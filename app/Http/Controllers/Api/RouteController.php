<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Doctor;
use App\Models\Route;
use App\Models\RouteStop;
use App\Services\CacheService;
use App\Services\RouteOptimizerService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class RouteController extends Controller
{
    public function __construct(private RouteOptimizerService $optimizer) {}

    /**
     * POST /api/routes/optimize
     *
     * Body:
     * {
     *   "name": "Monday Round",           // optional
     *   "route_date": "2026-07-24",       // optional, defaults to today
     *   "doctor_ids": [1, 3, 5, 7],       // required, ≥ 1
     *   "start_lat": 33.9716,             // optional start location
     *   "start_lng": -6.8498,
     *   "start_name": "Rabat Office"
     * }
     *
     * The optimized route result is cached in Redis for 24 hours.
     * If the same set of doctor IDs + start location was already computed,
     * the cached result is used instead of calling the Python microservice,
     * saving Mapbox/OR-Tools API costs.
     */
    public function optimize(Request $request): JsonResponse
    {
        $data = $request->validate([
            'doctor_ids'   => 'required|array|min:1',
            'doctor_ids.*' => 'integer|exists:doctors,id',
            'name'         => 'nullable|string|max:200',
            'route_date'   => 'nullable|date',
            'start_lat'    => 'nullable|numeric',
            'start_lng'    => 'nullable|numeric',
            'start_name'   => 'nullable|string|max:200',
        ]);

        $rep         = $request->user();
        $territoryId = $rep->territory_id;

        // Load doctors and verify they all belong to this rep's territory
        $doctors = Doctor::whereIn('id', $data['doctor_ids'])
            ->where('territory_id', $territoryId)
            ->where('is_active', true)
            ->get();

        $missingIds = collect($data['doctor_ids'])->diff($doctors->pluck('id'));
        if ($missingIds->isNotEmpty()) {
            return response()->json([
                'status'  => 'error',
                'message' => 'Some doctor IDs do not belong to your territory or are inactive.',
                'invalid' => $missingIds->values(),
            ], 422);
        }

        // Build start location (default to territory's rough center if not provided)
        $startLocation = [
            'lat'  => (float)($data['start_lat']  ?? $doctors->avg('lat') ?? 33.9716),
            'lng'  => (float)($data['start_lng']  ?? $doctors->avg('lng') ?? -6.8498),
            'name' => $data['start_name'] ?? 'Starting Point',
        ];

        // ─── Redis Cache: reuse previously computed route for identical stops ───
        try {
            $result = CacheService::rememberOptimizedRoute(
                $data['doctor_ids'],
                $startLocation,
                function () use ($doctors, $startLocation) {
                    return $this->optimizer->optimizeForDoctors($doctors->all(), $startLocation);
                }
            );
        } catch (\RuntimeException $e) {
            return response()->json([
                'status' => 'error',
                'reason' => $e->getMessage(),
            ], 503);
        }

        // Persist the Route and RouteStops in a transaction
        $route = DB::transaction(function () use ($rep, $data, $result, $startLocation) {
            $route = Route::create([
                'user_id'          => $rep->id,
                'name'             => $data['name'] ?? 'Route du ' . now()->format('d/m/Y'),
                'route_date'       => $data['route_date'] ?? today()->toDateString(),
                'total_distance_m' => $result['total_distance_m'] ?? null,
                'total_duration_s' => $result['total_duration_s'] ?? null,
                'status'           => 'active',
                'geometry'         => $result['geometry'] ?? null,
            ]);

            foreach ($result['ordered_stops'] as $stop) {
                RouteStop::create([
                    'route_id'   => $route->id,
                    'stop_order' => $stop['stop_number'],
                    'doctor_id'  => $stop['id'],
                    'status'     => 'pending',
                ]);
            }

            return $route;
        });

        // Update geocode cache for any doctors that got geocoded by the service
        foreach ($result['ordered_stops'] as $stop) {
            Doctor::where('id', $stop['id'])
                ->whereNull('lat')
                ->update([
                    'lat'         => $stop['lat'],
                    'lng'         => $stop['lng'],
                    'geocoded_at' => now(),
                ]);
        }

        return response()->json([
            'status'         => $result['status'],
            'route_id'       => $route->id,
            'start_location' => $result['start_location'] ?? $startLocation,
            'ordered_stops'  => $result['ordered_stops'],
            'total_distance_m' => $result['total_distance_m'],
            'total_duration_s' => $result['total_duration_s'],
            'geometry'       => $result['geometry'],
            'notes'          => $result['notes'] ?? null,
        ]);
    }

    /**
     * GET /api/routes
     * List routes for the current rep.
     */
    public function index(Request $request): JsonResponse
    {
        $routes = Route::where('user_id', $request->user()->id)
            ->with('stops.doctor:id,first_name,last_name,specialty,city')
            ->orderByDesc('route_date')
            ->paginate(20);

        return response()->json($routes);
    }

    /**
     * GET /api/routes/{route}
     */
    public function show(Request $request, Route $route): JsonResponse
    {
        if ($route->user_id !== $request->user()->id) {
            abort(403);
        }

        $route->load('stops.doctor');

        return response()->json($route);
    }

    /**
     * PATCH /api/routes/{route}/stops/{stop}/status
     * Mark a stop as visited or skipped.
     */
    public function updateStop(Request $request, Route $route, RouteStop $stop): JsonResponse
    {
        if ($route->user_id !== $request->user()->id || $stop->route_id !== $route->id) {
            abort(403);
        }

        $data = $request->validate([
            'status' => 'required|in:pending,visited,skipped',
        ]);

        $stop->update($data);

        return response()->json(['status' => 'ok', 'stop' => $stop->fresh()]);
    }
}
