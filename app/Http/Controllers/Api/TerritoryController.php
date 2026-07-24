<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Services\CacheService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class TerritoryController extends Controller
{
    /**
     * GET /api/territory
     * Returns the current rep's territory with summary stats.
     *
     * Stats (doctor count, pharmacy count, rep count) are cached
     * in Redis for 15 minutes to avoid 3 aggregate queries per request.
     */
    public function show(Request $request): JsonResponse
    {
        $user = $request->user()->load('territory');
        $territory = $user->territory;

        if (! $territory) {
            return response()->json(['message' => 'No territory assigned.'], 404);
        }

        // Cache the expensive aggregate counts
        $stats = CacheService::rememberTerritoryStats($territory->id, function () use ($territory) {
            return [
                'doctors'    => $territory->doctors()->active()->count(),
                'pharmacies' => $territory->pharmacies()->active()->count(),
                'reps'       => $territory->representatives()->where('is_active', true)->count(),
            ];
        });

        return response()->json([
            'id'             => $territory->id,
            'name'           => $territory->name,
            'code'           => $territory->code,
            'region'         => $territory->region,
            'description'    => $territory->description,
            'stats'          => $stats,
        ]);
    }
}
