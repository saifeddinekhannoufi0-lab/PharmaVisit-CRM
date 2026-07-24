"""
OSRM client — distance matrices and driving route geometry.

Uses the public OSRM demo server by default (no API key needed).
Set OSRM_BASE_URL in .env to point at a self-hosted instance.

Note: OSRM coordinates are [lng, lat] (GeoJSON order), the opposite of Leaflet.
      This module always accepts (lat, lng) tuples and converts internally.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "http://router.project-osrm.org")


def _coords_str(coords: list[tuple[float, float]]) -> str:
    """Convert (lat,lng) list to OSRM's 'lng,lat;lng,lat' format."""
    return ";".join(f"{lng},{lat}" for lat, lng in coords)


async def get_duration_matrix(
    coords: list[tuple[float, float]],
) -> tuple[list[list[int]] | None, list[list[int]] | None]:
    """
    Returns (durations_matrix_s, distances_matrix_m) or (None, None) on error.
    """
    if len(coords) < 2:
        return None, None

    url = f"{OSRM_BASE_URL}/table/v1/driving/{_coords_str(coords)}"
    params = {"annotations": "duration,distance"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != "Ok":
            logger.error("[osrm] table API error: %s", data.get("code"))
            return None, None

        durations = [[int(v or 0) for v in row] for row in data["durations"]]
        distances = [[int(v or 0) for v in row] for row in data.get("distances", [[]])]

        logger.info("[osrm] matrix %dx%d OK", len(durations), len(durations))
        return durations, distances or None

    except httpx.TimeoutException:
        logger.warning("[osrm] Table request timed out — will fall back to Haversine")
        return None, None
    except Exception as exc:
        logger.error("[osrm] Table request failed: %s", exc)
        return None, None


async def get_route_geometry(
    coords: list[tuple[float, float]],
) -> tuple[dict | None, int | None, int | None]:
    """
    Returns (geojson_linestring, total_duration_s, total_distance_m) or (None, None, None).
    """
    if len(coords) < 2:
        return None, None, None

    url = f"{OSRM_BASE_URL}/route/v1/driving/{_coords_str(coords)}"
    params = {"overview": "full", "geometries": "geojson", "steps": "false"}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            logger.error("[osrm] route API error: %s", data.get("code"))
            return None, None, None

        route = data["routes"][0]
        geometry = route["geometry"]  # GeoJSON LineString
        duration = int(route.get("duration", 0))
        distance = int(route.get("distance", 0))

        logger.info("[osrm] route OK — %.1f km, %d min", distance / 1000, duration // 60)
        return geometry, duration, distance

    except httpx.TimeoutException:
        logger.warning("[osrm] Route request timed out — geometry will be null")
        return None, None, None
    except Exception as exc:
        logger.error("[osrm] Route request failed: %s", exc)
        return None, None, None


async def health_check() -> bool:
    """Ping OSRM with a trivial request to verify it's reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Nearest-road snap for Rabat city center
            resp = await client.get(f"{OSRM_BASE_URL}/nearest/v1/driving/-6.8498,33.9716")
        return resp.status_code == 200 and resp.json().get("code") == "Ok"
    except Exception:
        return False
