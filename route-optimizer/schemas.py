from __future__ import annotations
from pydantic import BaseModel


# ─── Geocoding ────────────────────────────────────────────────────────────────

class GeocodeRequest(BaseModel):
    query: str


class GeocodeResponse(BaseModel):
    status: str   # "ok" | "not_found" | "error"
    lat: float | None = None
    lng: float | None = None
    display_name: str | None = None
    confidence: float | None = None
    candidates: int = 0
    reason: str | None = None


# ─── Optimization inputs ──────────────────────────────────────────────────────

class StopInput(BaseModel):
    id: int
    name: str
    address: str
    city: str
    lat: float | None = None
    lng: float | None = None
    priority: str = "medium"
    specialty: str | None = None


class StartLocation(BaseModel):
    lat: float
    lng: float
    name: str = "Starting Point"


class OptimizeRequest(BaseModel):
    stops: list[StopInput]
    start: StartLocation


# ─── Optimization outputs ─────────────────────────────────────────────────────

class OrderedStop(BaseModel):
    id: int
    stop_number: int
    name: str
    specialty: str | None = None
    priority: str
    lat: float
    lng: float
    address: str
    city: str
    leg_duration_s: int | None = None
    leg_distance_m: int | None = None
    cumulative_duration_s: int | None = None


class OptimizeResponse(BaseModel):
    status: str   # "ok" | "partial" | "error"
    start_location: StartLocation | None = None
    ordered_stops: list[OrderedStop] = []
    total_distance_m: int | None = None
    total_duration_s: int | None = None
    geometry: dict | None = None   # GeoJSON LineString — null if OSRM unavailable
    notes: str | None = None
    reason: str | None = None


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    osrm: str
    nominatim: str
    or_tools: str
