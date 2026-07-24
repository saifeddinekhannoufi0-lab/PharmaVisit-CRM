<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Pharmacy;
use App\Services\CacheService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class PharmacyController extends Controller
{
    /**
     * GET /api/pharmacies
     *
     * Results are cached in Redis for 10 minutes, scoped by territory + filters.
     */
    public function index(Request $request): JsonResponse
    {
        $territoryId = $request->user()->territory_id;

        $filters = $request->only(['search', 'city', 'page']);

        $pharmacies = CacheService::rememberPharmacies($territoryId, $filters, function () use ($request, $territoryId) {
            $query = Pharmacy::inTerritory($territoryId)
                ->active()
                ->with('territory:id,name,code');

            if ($search = $request->query('search')) {
                $query->where(function ($q) use ($search) {
                    $q->where('name', 'like', "%{$search}%")
                      ->orWhere('address', 'like', "%{$search}%")
                      ->orWhere('manager_name', 'like', "%{$search}%");
                });
            }

            if ($city = $request->query('city')) {
                $query->where('city', $city);
            }

            return $query->orderBy('name')
                         ->paginate(25)
                         ->through(fn($p) => $this->formatPharmacy($p));
        });

        return response()->json($pharmacies);
    }

    /**
     * GET /api/pharmacies/{id}
     */
    public function show(Request $request, Pharmacy $pharmacy): JsonResponse
    {
        $this->authorizeTerritory($request, $pharmacy->territory_id);
        $pharmacy->load(['territory:id,name,code', 'visitLogs' => fn($q) => $q->latest()->limit(5)]);

        return response()->json($this->formatPharmacy($pharmacy, detailed: true));
    }

    /**
     * POST /api/pharmacies
     */
    public function store(Request $request): JsonResponse
    {
        $data = $request->validate([
            'name'         => 'required|string|max:200',
            'address'      => 'required|string|max:255',
            'city'         => 'required|string|max:100',
            'postal_code'  => 'nullable|string|max:10',
            'region'       => 'nullable|string|max:100',
            'phone'        => 'nullable|string|max:20',
            'manager_name' => 'nullable|string|max:150',
            'notes'        => 'nullable|string',
        ]);

        $data['territory_id'] = $request->user()->territory_id;

        $pharmacy = Pharmacy::create($data);

        // Invalidate pharmacy list + territory stats caches
        CacheService::invalidatePharmacies($data['territory_id']);

        return response()->json($this->formatPharmacy($pharmacy), 201);
    }

    /**
     * PUT /api/pharmacies/{id}
     */
    public function update(Request $request, Pharmacy $pharmacy): JsonResponse
    {
        $this->authorizeTerritory($request, $pharmacy->territory_id);

        $data = $request->validate([
            'name'         => 'sometimes|string|max:200',
            'address'      => 'sometimes|string|max:255',
            'city'         => 'sometimes|string|max:100',
            'postal_code'  => 'nullable|string|max:10',
            'region'       => 'nullable|string|max:100',
            'phone'        => 'nullable|string|max:20',
            'manager_name' => 'nullable|string|max:150',
            'is_active'    => 'sometimes|boolean',
            'notes'        => 'nullable|string',
        ]);

        if (isset($data['address']) || isset($data['city'])) {
            $data['lat']         = null;
            $data['lng']         = null;
            $data['geocoded_at'] = null;
        }

        $pharmacy->update($data);

        // Invalidate pharmacy list + territory stats caches
        CacheService::invalidatePharmacies($pharmacy->territory_id);

        return response()->json($this->formatPharmacy($pharmacy->fresh()));
    }

    /**
     * DELETE /api/pharmacies/{id}
     */
    public function destroy(Request $request, Pharmacy $pharmacy): JsonResponse
    {
        $this->authorizeTerritory($request, $pharmacy->territory_id);
        $pharmacy->delete();

        // Invalidate pharmacy list + territory stats caches
        CacheService::invalidatePharmacies($pharmacy->territory_id);

        return response()->json(['message' => 'Pharmacy deactivated.']);
    }

    // ─── Helpers ──────────────────────────────────────────────────────

    private function authorizeTerritory(Request $request, int $territoryId): void
    {
        if ($request->user()->territory_id !== $territoryId) {
            abort(403, 'This pharmacy does not belong to your territory.');
        }
    }

    private function formatPharmacy(Pharmacy $pharmacy, bool $detailed = false): array
    {
        $base = [
            'id'           => $pharmacy->id,
            'name'         => $pharmacy->name,
            'address'      => $pharmacy->address,
            'city'         => $pharmacy->city,
            'postal_code'  => $pharmacy->postal_code,
            'region'       => $pharmacy->region,
            'lat'          => $pharmacy->lat,
            'lng'          => $pharmacy->lng,
            'is_geocoded'  => $pharmacy->is_geocoded,
            'phone'        => $pharmacy->phone,
            'manager_name' => $pharmacy->manager_name,
            'is_active'    => $pharmacy->is_active,
            'territory'    => $pharmacy->territory?->only(['id', 'name', 'code']),
        ];

        if ($detailed) {
            $base['notes']      = $pharmacy->notes;
            $base['visit_logs'] = $pharmacy->visitLogs?->map(fn($v) => [
                'id'         => $v->id,
                'visited_at' => $v->visited_at?->toISOString(),
                'outcome'    => $v->outcome,
                'notes'      => $v->notes,
            ]);
        }

        return $base;
    }
}
