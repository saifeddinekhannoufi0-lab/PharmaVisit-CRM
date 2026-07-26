<?php

namespace App\Services;

use Closure;
use Illuminate\Support\Facades\Cache;

/**
 * Centralized caching layer for PharmaVisit.
 *
 * Supports both tagged stores (Redis) and untagged stores (file, array).
 * Falls back gracefully to plain cache keys when tags are unsupported.
 *
 * Key structure:
 *   pharmavisit:doctors:{territory_id}:{filter_hash}
 *   pharmavisit:pharmacies:{territory_id}:{filter_hash}
 *   pharmavisit:territory:{territory_id}:stats
 *   pharmavisit:route:{stop_hash}
 */
class CacheService
{
    // ─── TTL Constants (seconds) ─────────────────────────────────────
    public const TTL_LIST    = 600;    // 10 minutes – doctor/pharmacy lists
    public const TTL_STATS   = 900;    // 15 minutes – territory aggregate stats
    public const TTL_ROUTE   = 86400;  // 24 hours   – optimized route results

    // ─── Key Prefixes ────────────────────────────────────────────────
    private const PREFIX = 'pharmavisit';

    // ─── Tag Support Detection ───────────────────────────────────────

    /**
     * Returns true if the current cache store supports tagging.
     */
    private static function supportsTags(): bool
    {
        try {
            Cache::tags(['_probe'])->get('_probe');
            return true;
        } catch (\BadMethodCallException $e) {
            return false;
        }
    }

    /**
     * Remember a value using tags if supported, otherwise use a plain key.
     */
    private static function remember(array $tags, string $key, int $ttl, Closure $callback): mixed
    {
        if (self::supportsTags()) {
            return Cache::tags($tags)->remember($key, $ttl, $callback);
        }

        return Cache::remember($key, $ttl, $callback);
    }

    /**
     * Flush a tagged group if supported, otherwise do nothing (plain cache expires naturally).
     */
    private static function flushTags(array $tags): void
    {
        if (self::supportsTags()) {
            Cache::tags($tags)->flush();
        }
    }

    // ─── Doctor Caching ──────────────────────────────────────────────

    /**
     * Cache a paginated doctor list scoped to territory + query filters.
     */
    public static function rememberDoctors(int $territoryId, array $filters, Closure $callback): mixed
    {
        $key = self::doctorListKey($territoryId, $filters);

        return self::remember(self::doctorTags($territoryId), $key, self::TTL_LIST, $callback);
    }

    /**
     * Cache a single doctor detail response.
     */
    public static function rememberDoctor(int $territoryId, int $doctorId, Closure $callback): mixed
    {
        $key = self::PREFIX . ":doctor:{$doctorId}";

        return self::remember(self::doctorTags($territoryId), $key, self::TTL_LIST, $callback);
    }

    // ─── Pharmacy Caching ────────────────────────────────────────────

    /**
     * Cache a paginated pharmacy list scoped to territory + query filters.
     */
    public static function rememberPharmacies(int $territoryId, array $filters, Closure $callback): mixed
    {
        $key = self::pharmacyListKey($territoryId, $filters);

        return self::remember(self::pharmacyTags($territoryId), $key, self::TTL_LIST, $callback);
    }

    // ─── Territory Stats Caching ─────────────────────────────────────

    /**
     * Cache territory aggregate stats (doctor count, pharmacy count, rep count).
     */
    public static function rememberTerritoryStats(int $territoryId, Closure $callback): mixed
    {
        $key = self::PREFIX . ":territory:{$territoryId}:stats";

        return self::remember(self::territoryStatsTags($territoryId), $key, self::TTL_STATS, $callback);
    }

    // ─── Route Caching ───────────────────────────────────────────────

    /**
     * Cache an optimized route result keyed by the sorted set of stop IDs + start location.
     */
    public static function rememberOptimizedRoute(array $doctorIds, array $startLocation, Closure $callback): mixed
    {
        $key = self::routeKey($doctorIds, $startLocation);

        return self::remember(['routes'], $key, self::TTL_ROUTE, $callback);
    }

    // ─── Invalidation ────────────────────────────────────────────────

    /**
     * Flush ALL caches for a territory (doctors, pharmacies, stats).
     * Call this after any create/update/delete on doctors or pharmacies.
     */
    public static function invalidateTerritory(int $territoryId): void
    {
        self::flushTags(["territory:{$territoryId}"]);
    }

    /**
     * Flush only doctor-related caches for a territory.
     */
    public static function invalidateDoctors(int $territoryId): void
    {
        self::flushTags(self::doctorTags($territoryId));
        self::flushTags(self::territoryStatsTags($territoryId));
    }

    /**
     * Flush only pharmacy-related caches for a territory.
     */
    public static function invalidatePharmacies(int $territoryId): void
    {
        self::flushTags(self::pharmacyTags($territoryId));
        self::flushTags(self::territoryStatsTags($territoryId));
    }

    /**
     * Flush ALL cached route optimizations.
     */
    public static function invalidateAllRoutes(): void
    {
        self::flushTags(['routes']);
    }

    /**
     * Flush everything the app has cached.
     */
    public static function flushAll(): void
    {
        if (self::supportsTags()) {
            Cache::tags(['pharmavisit'])->flush();
            Cache::tags(['routes'])->flush();
        } else {
            Cache::flush();
        }
    }

    // ─── Key Builders ────────────────────────────────────────────────

    private static function doctorListKey(int $territoryId, array $filters): string
    {
        $hash = md5(serialize(array_filter($filters)));
        return self::PREFIX . ":doctors:{$territoryId}:{$hash}";
    }

    private static function pharmacyListKey(int $territoryId, array $filters): string
    {
        $hash = md5(serialize(array_filter($filters)));
        return self::PREFIX . ":pharmacies:{$territoryId}:{$hash}";
    }

    private static function routeKey(array $doctorIds, array $startLocation): string
    {
        sort($doctorIds);
        $payload = json_encode([
            'ids'   => $doctorIds,
            'start' => [
                'lat' => round($startLocation['lat'] ?? 0, 5),
                'lng' => round($startLocation['lng'] ?? 0, 5),
            ],
        ]);
        return self::PREFIX . ':route:' . md5($payload);
    }

    // ─── Tag Helpers ─────────────────────────────────────────────────

    private static function doctorTags(int $territoryId): array
    {
        return ['pharmavisit', "territory:{$territoryId}", 'doctors'];
    }

    private static function pharmacyTags(int $territoryId): array
    {
        return ['pharmavisit', "territory:{$territoryId}", 'pharmacies'];
    }

    private static function territoryStatsTags(int $territoryId): array
    {
        return ['pharmavisit', "territory:{$territoryId}", 'stats'];
    }
}
