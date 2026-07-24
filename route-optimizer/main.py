"""
PharmaVisit Route Optimizer Microservice
=========================================
FastAPI service exposing:
  GET  /health              — liveness + dependency check
  POST /geocode             — single-address geocoding (Nominatim, rate-limited)
  POST /optimize            — full pipeline: geocode → matrix → OR-Tools → geometry

Consumed by the Laravel CRM backend (not directly by the browser).
"""
from __future__ import annotations

import logging
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from schemas import (
    GeocodeRequest,
    GeocodeResponse,
    HealthResponse,
    OptimizeRequest,
    OptimizeResponse,
    OrderedStop,
)
from services.geocoder import NominatimGeocoder
from services.optimizer import (
    OR_TOOLS_AVAILABLE,
    build_haversine_matrix,
    solve_tsp,
)
from services.router import get_duration_matrix, get_route_geometry, health_check

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PharmaVisit Route Optimizer",
    version="1.0.0",
    description="Geocoding + TSP optimization microservice for PharmaVisit CRM",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# Single shared geocoder instance (holds the rate-limit state + cache)
geocoder = NominatimGeocoder()


# ─── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    osrm_ok = await health_check()
    # Quick Nominatim ping
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(
                f"{os.getenv('NOMINATIM_BASE_URL', 'https://nominatim.openstreetmap.org')}/status",
                headers={"User-Agent": os.getenv("NOMINATIM_USER_AGENT", "PharmaVisitCRM/1.0")},
            )
        nom_ok = r.status_code == 200
    except Exception:
        nom_ok = False

    return HealthResponse(
        status="ok",
        osrm="ok" if osrm_ok else "unreachable",
        nominatim="ok" if nom_ok else "unreachable",
        or_tools="ok" if OR_TOOLS_AVAILABLE else "not_installed (using fallback)",
    )


# ─── Geocoding ─────────────────────────────────────────────────────────────────

@app.post("/geocode", response_model=GeocodeResponse, tags=["Geocoding"])
async def geocode_address(req: GeocodeRequest):
    """
    Geocode a single address via Nominatim.
    Results are in-memory cached; API calls are rate-limited to ≤ 1/sec.
    """
    result = await geocoder.geocode(req.query)
    if not result:
        return GeocodeResponse(status="not_found", reason="Nominatim returned no results")
    return GeocodeResponse(status="ok", **result)


@app.get("/geocoder/stats", tags=["System"])
async def geocoder_stats():
    """Cache hit/miss ratio — useful for proving Nominatim ToS compliance."""
    return geocoder.stats()


# ─── Route Optimization ────────────────────────────────────────────────────────

@app.post("/optimize", response_model=OptimizeResponse, tags=["Routing"])
async def optimize_route(req: OptimizeRequest):
    """
    Full pipeline:
      1. Geocode any stops with missing lat/lng (sequentially, rate-limited)
      2. Build OSRM driving-time matrix (falls back to Haversine on timeout)
      3. Solve TSP with OR-Tools (falls back to nearest-neighbor)
      4. Fetch driving polyline from OSRM for the optimized order
      5. Return ordered stops + GeoJSON geometry + totals
    """
    if not req.stops:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No stops provided")

    # ── 1. Geocode any stops missing coordinates ────────────────────────────
    stops = list(req.stops)
    geocode_failures: list[str] = []

    for stop in stops:
        if stop.lat is None or stop.lng is None:
            query = f"{stop.address}, {stop.city}, Morocco"
            result = await geocoder.geocode(query)   # rate-limited internally
            if result:
                stop.lat = result["lat"]
                stop.lng = result["lng"]
            else:
                geocode_failures.append(stop.name)
                logger.warning("[optimize] Could not geocode: %s — skipping", stop.name)

    # Filter out ungeocodeable stops
    geocoded_stops = [s for s in stops if s.lat is not None and s.lng is not None]
    if not geocoded_stops:
        return OptimizeResponse(
            status="error",
            reason="All stops failed geocoding",
            notes=f"Failed: {', '.join(geocode_failures)}",
        )

    # ── 2. Build coordinate list: [start] + [stops…] ──────────────────────
    all_coords: list[tuple[float, float]] = [
        (req.start.lat, req.start.lng),
        *[(s.lat, s.lng) for s in geocoded_stops],
    ]
    n_total = len(all_coords)

    # ── 3. Build duration matrix ───────────────────────────────────────────
    duration_matrix, distance_matrix = await get_duration_matrix(all_coords)
    used_haversine = False

    if duration_matrix is None:
        logger.info("[optimize] OSRM unavailable — using Haversine matrix")
        duration_matrix = build_haversine_matrix(all_coords)
        used_haversine = True

    # ── 4. Solve TSP (start is always index 0) ────────────────────────────
    order = solve_tsp(duration_matrix, start_index=0)

    # Build ordered stops (skip index 0 = start location)
    ordered_stop_nodes = [i for i in order if i != 0]

    # Compute per-leg durations
    total_dur = 0
    total_dist = 0
    ordered_stops_out: list[OrderedStop] = []

    prev_node = 0
    for step, node_idx in enumerate(ordered_stop_nodes, start=1):
        stop = geocoded_stops[node_idx - 1]   # -1 because index 0 = start
        leg_dur = duration_matrix[prev_node][node_idx]
        leg_dist = (distance_matrix[prev_node][node_idx]
                    if distance_matrix else int(leg_dur * 14))
        total_dur += leg_dur
        total_dist += leg_dist

        ordered_stops_out.append(OrderedStop(
            id=stop.id,
            stop_number=step,
            name=stop.name,
            specialty=stop.specialty,
            priority=stop.priority,
            lat=stop.lat,
            lng=stop.lng,
            address=stop.address,
            city=stop.city,
            leg_duration_s=leg_dur,
            leg_distance_m=leg_dist,
            cumulative_duration_s=total_dur,
        ))
        prev_node = node_idx

    # ── 5. Fetch driving polyline for optimized order ─────────────────────
    waypoint_coords = [all_coords[0]] + [all_coords[i] for i in ordered_stop_nodes]
    geometry, osrm_dur, osrm_dist = await get_route_geometry(waypoint_coords)

    # Use OSRM totals if available (more accurate than matrix diagonals)
    if osrm_dur is not None:
        total_dur = osrm_dur
    if osrm_dist is not None:
        total_dist = osrm_dist

    # ── 6. Compose response ───────────────────────────────────────────────
    notes_parts = []
    if geocode_failures:
        notes_parts.append(f"Skipped (geocode failed): {', '.join(geocode_failures)}")
    if used_haversine:
        notes_parts.append("OSRM unavailable — times are estimates (Haversine)")

    return OptimizeResponse(
        status="partial" if geocode_failures else "ok",
        start_location=req.start,
        ordered_stops=ordered_stops_out,
        total_distance_m=total_dist,
        total_duration_s=total_dur,
        geometry=geometry,
        notes="; ".join(notes_parts) or None,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8001)), reload=True)
