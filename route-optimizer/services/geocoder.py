"""
Nominatim geocoding client.

Hard requirements enforced HERE in code (not just the agent prompt):
  - Max 1 concurrent request via asyncio.Semaphore
  - Enforced 1-second floor between calls via timestamp check + asyncio.sleep
  - Custom User-Agent on every request (required by Nominatim ToS)
  - In-memory cache keyed on normalized query string
  - Observable: logs cache hits vs. API calls to stdout
"""
from __future__ import annotations

import asyncio
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)


class NominatimGeocoder:
    def __init__(self) -> None:
        self._base_url: str = os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org")
        self._user_agent: str = os.getenv("NOMINATIM_USER_AGENT", "PharmaVisitCRM/1.0")
        self._semaphore = asyncio.Semaphore(1)  # HARD LIMIT: 1 concurrent request
        self._last_call_at: float = 0.0
        self._cache: dict[str, dict] = {}
        self._cache_hits: int = 0
        self._api_calls: int = 0

    # ── Public interface ───────────────────────────────────────────────────────

    async def geocode(self, query: str) -> dict | None:
        """
        Geocode a query string.
        Returns {lat, lng, display_name, confidence, candidates} or None.
        """
        key = query.lower().strip()

        if key in self._cache:
            self._cache_hits += 1
            logger.info("[geocoder] CACHE HIT  (%d hits / %d calls): %s", self._cache_hits, self._api_calls, query)
            return self._cache[key]

        async with self._semaphore:
            # Double-check cache in case another coroutine filled it while we waited
            if key in self._cache:
                self._cache_hits += 1
                return self._cache[key]

            # Enforce ≥ 1 second between API calls
            elapsed = time.monotonic() - self._last_call_at
            if elapsed < 1.0:
                wait = 1.0 - elapsed
                logger.debug("[geocoder] rate-limit sleep %.2fs", wait)
                await asyncio.sleep(wait)

            result = await self._call_nominatim(query)
            self._last_call_at = time.monotonic()
            self._api_calls += 1

            logger.info(
                "[geocoder] API CALL   (%d hits / %d calls): %s → %s",
                self._cache_hits,
                self._api_calls,
                query,
                f"{result['lat']:.5f},{result['lng']:.5f}" if result else "NOT FOUND",
            )

            if result:
                self._cache[key] = result

            return result

    async def reverse_geocode(self, lat: float, lng: float) -> dict | None:
        """Reverse geocode a lat/lng pair."""
        return await self.geocode(f"reverse:{lat:.6f},{lng:.6f}")

    def stats(self) -> dict:
        return {
            "cache_hits": self._cache_hits,
            "api_calls": self._api_calls,
            "cache_size": len(self._cache),
        }

    # ── Private ────────────────────────────────────────────────────────────────

    async def _call_nominatim(self, query: str) -> dict | None:
        params = {"q": query, "format": "json", "limit": 3, "addressdetails": 1}
        headers = {"User-Agent": self._user_agent}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/search", params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            if not data:
                return None

            best = data[0]
            return {
                "lat": float(best["lat"]),
                "lng": float(best["lon"]),
                "display_name": best.get("display_name", ""),
                "confidence": float(best.get("importance", 0.5)),
                "candidates": len(data),
            }
        except httpx.TimeoutException:
            logger.warning("[geocoder] Nominatim timeout for: %s", query)
            return None
        except Exception as exc:
            logger.error("[geocoder] Nominatim error: %s", exc)
            return None
