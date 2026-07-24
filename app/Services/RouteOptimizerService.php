<?php

namespace App\Services;

use App\Models\Doctor;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class RouteOptimizerService
{
    private string $baseUrl;

    public function __construct()
    {
        $this->baseUrl = rtrim(config('services.optimizer.url', 'http://127.0.0.1:8001'), '/');
    }

    /**
     * Run the full geocode → TSP → polyline pipeline for a list of doctors.
     *
     * @param  \App\Models\Doctor[]  $doctors
     * @param  array{lat: float, lng: float, name: string}  $startLocation
     * @return array  The decoded JSON response from the microservice.
     * @throws \RuntimeException  if the microservice is unreachable or returns an error.
     */
    public function optimizeForDoctors(array $doctors, array $startLocation): array
    {
        $stops = collect($doctors)->map(fn(Doctor $d) => [
            'id'        => $d->id,
            'name'      => $d->full_name,
            'address'   => $d->address,
            'city'      => $d->city,
            'lat'       => $d->lat,
            'lng'       => $d->lng,
            'priority'  => $d->priority,
            'specialty' => $d->specialty,
        ])->values()->all();

        $payload = [
            'stops' => $stops,
            'start' => $startLocation,
        ];

        try {
            $response = Http::timeout(30)
                ->post("{$this->baseUrl}/optimize", $payload);

            if ($response->failed()) {
                Log::error('RouteOptimizer: microservice returned error', [
                    'status' => $response->status(),
                    'body'   => $response->body(),
                ]);
                throw new \RuntimeException("Route optimizer service error: HTTP {$response->status()}");
            }

            $data = $response->json();

            if (($data['status'] ?? '') === 'error') {
                throw new \RuntimeException($data['reason'] ?? 'Unknown optimizer error');
            }

            return $data;

        } catch (\Illuminate\Http\Client\ConnectionException $e) {
            throw new \RuntimeException(
                'Route optimizer service is unreachable. Make sure the Python microservice is running on port 8001.',
                previous: $e
            );
        }
    }

    /**
     * Geocode a single address via the microservice (which caches + rate-limits).
     */
    public function geocodeAddress(string $query): ?array
    {
        try {
            $response = Http::timeout(15)
                ->post("{$this->baseUrl}/geocode", ['query' => $query]);

            if ($response->failed()) {
                return null;
            }

            $data = $response->json();
            return $data['status'] === 'ok' ? $data : null;

        } catch (\Exception $e) {
            Log::warning("Geocode failed for '{$query}': " . $e->getMessage());
            return null;
        }
    }

    /**
     * Check if the microservice is up.
     */
    public function isHealthy(): bool
    {
        try {
            $r = Http::timeout(5)->get("{$this->baseUrl}/health");
            return $r->successful();
        } catch (\Exception) {
            return false;
        }
    }
}
