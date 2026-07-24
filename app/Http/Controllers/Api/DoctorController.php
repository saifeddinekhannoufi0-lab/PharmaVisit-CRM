<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Doctor;
use App\Services\CacheService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class DoctorController extends Controller
{
    /**
     * GET /api/doctors
     * List doctors in the authenticated rep's territory.
     * Query params: ?search=, ?specialty=, ?priority=, ?city=, ?page=
     *
     * Results are cached in Redis for 10 minutes, scoped by territory + filters.
     */
    public function index(Request $request): JsonResponse
    {
        $territoryId = $request->user()->territory_id;

        // Build a filter fingerprint for the cache key
        $filters = $request->only(['search', 'specialty', 'priority', 'city', 'page', 'per_page']);

        $doctors = CacheService::rememberDoctors($territoryId, $filters, function () use ($request, $territoryId) {
            $query = Doctor::inTerritory($territoryId)
                ->active()
                ->with('territory:id,name,code');

            if ($search = $request->query('search')) {
                $query->where(function ($q) use ($search) {
                    $q->where('first_name', 'like', "%{$search}%")
                      ->orWhere('last_name', 'like', "%{$search}%")
                      ->orWhere('clinic_name', 'like', "%{$search}%")
                      ->orWhere('address', 'like', "%{$search}%");
                });
            }

            if ($specialty = $request->query('specialty')) {
                $query->where('specialty', $specialty);
            }

            if ($priority = $request->query('priority')) {
                $query->where('priority', $priority);
            }

            if ($city = $request->query('city')) {
                $query->where('city', $city);
            }

            $perPage = min((int) ($request->query('per_page', 25)), 100);

            $paginated = $query->orderBy('last_name')->paginate($perPage);

            // Format BEFORE caching so no closures are stored
            $items = $paginated->getCollection()->map(fn($d) => $this->formatDoctor($d));

            return [
                'data'         => $items->values()->all(),
                'current_page' => $paginated->currentPage(),
                'last_page'    => $paginated->lastPage(),
                'per_page'     => $paginated->perPage(),
                'total'        => $paginated->total(),
            ];
        });

        return response()->json($doctors);
    }

    /**
     * GET /api/doctors/{id}
     */
    public function show(Request $request, Doctor $doctor): JsonResponse
    {
        $this->authorizeTerritory($request, $doctor->territory_id);

        $doctor->load(['territory:id,name,code', 'visitLogs' => fn($q) => $q->latest()->limit(5)]);

        return response()->json($this->formatDoctor($doctor, detailed: true));
    }

    /**
     * POST /api/doctors
     */
    public function store(Request $request): JsonResponse
    {
        $data = $request->validate([
            'first_name'  => 'required|string|max:100',
            'last_name'   => 'required|string|max:100',
            'specialty'   => 'required|string|max:100',
            'clinic_name' => 'nullable|string|max:200',
            'address'     => 'required|string|max:255',
            'city'        => 'required|string|max:100',
            'postal_code' => 'nullable|string|max:10',
            'region'      => 'nullable|string|max:100',
            'phone'       => 'nullable|string|max:20',
            'email'       => 'nullable|email|max:150',
            'priority'    => 'nullable|in:high,medium,low',
            'notes'       => 'nullable|string',
        ]);

        $data['territory_id'] = $request->user()->territory_id;

        $doctor = Doctor::create($data);

        // Invalidate doctor list + territory stats caches
        CacheService::invalidateDoctors($data['territory_id']);

        return response()->json($this->formatDoctor($doctor), 201);
    }

    /**
     * PUT /api/doctors/{id}
     */
    public function update(Request $request, Doctor $doctor): JsonResponse
    {
        $this->authorizeTerritory($request, $doctor->territory_id);

        $data = $request->validate([
            'first_name'  => 'sometimes|string|max:100',
            'last_name'   => 'sometimes|string|max:100',
            'specialty'   => 'sometimes|string|max:100',
            'clinic_name' => 'nullable|string|max:200',
            'address'     => 'sometimes|string|max:255',
            'city'        => 'sometimes|string|max:100',
            'postal_code' => 'nullable|string|max:10',
            'region'      => 'nullable|string|max:100',
            'phone'       => 'nullable|string|max:20',
            'email'       => 'nullable|email|max:150',
            'priority'    => 'nullable|in:high,medium,low',
            'is_active'   => 'sometimes|boolean',
            'notes'       => 'nullable|string',
        ]);

        // If address changed, clear geocode so it gets re-geocoded next time
        if (isset($data['address']) || isset($data['city'])) {
            $data['lat']          = null;
            $data['lng']          = null;
            $data['geocoded_at']  = null;
        }

        $doctor->update($data);

        // Invalidate doctor list + territory stats caches
        CacheService::invalidateDoctors($doctor->territory_id);

        return response()->json($this->formatDoctor($doctor->fresh()));
    }

    /**
     * DELETE /api/doctors/{id}
     * Soft-delete — preserves visit history.
     */
    public function destroy(Request $request, Doctor $doctor): JsonResponse
    {
        $this->authorizeTerritory($request, $doctor->territory_id);
        $doctor->delete();

        // Invalidate doctor list + territory stats caches
        CacheService::invalidateDoctors($doctor->territory_id);

        return response()->json(['message' => 'Doctor deactivated.']);
    }

    // ─── Private Helpers ──────────────────────────────────────────────

    private function authorizeTerritory(Request $request, int $doctorTerritoryId): void
    {
        if ($request->user()->territory_id !== $doctorTerritoryId) {
            abort(403, 'This doctor does not belong to your territory.');
        }
    }

    private function formatDoctor(Doctor $doctor, bool $detailed = false): array
    {
        $base = [
            'id'          => $doctor->id,
            'full_name'   => $doctor->full_name,
            'first_name'  => $doctor->first_name,
            'last_name'   => $doctor->last_name,
            'specialty'   => $doctor->specialty,
            'clinic_name' => $doctor->clinic_name,
            'address'     => $doctor->address,
            'city'        => $doctor->city,
            'postal_code' => $doctor->postal_code,
            'region'      => $doctor->region,
            'lat'         => $doctor->lat,
            'lng'         => $doctor->lng,
            'is_geocoded' => $doctor->is_geocoded,
            'phone'       => $doctor->phone,
            'email'       => $doctor->email,
            'priority'    => $doctor->priority,
            'is_active'   => $doctor->is_active,
            'territory'   => $doctor->territory?->only(['id', 'name', 'code']),
        ];

        if ($detailed) {
            $base['notes']      = $doctor->notes;
            $base['visit_logs'] = $doctor->visitLogs?->map(fn($v) => [
                'id'         => $v->id,
                'visited_at' => $v->visited_at?->toISOString(),
                'outcome'    => $v->outcome,
                'notes'      => $v->notes,
            ]);
        }

        return $base;
    }
}
