<div align="center">
  <img src="public/img/readme_logo.png" alt="PharmaVisit CRM Logo" width="180" />
  <h1>PharmaVisit CRM</h1>
  <p><strong>Intelligent Field CRM for Pharmaceutical Sales Representatives</strong></p>
  <p><em>Route optimization · Live GPS tracking · Real medical data · Morocco region</em></p>

  <p>
    <img src="https://img.shields.io/badge/Laravel-11-FF2D20?style=for-the-badge&logo=laravel&logoColor=white" />
    <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" />
    <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
    <img src="https://img.shields.io/badge/MySQL-8-4479A1?style=for-the-badge&logo=mysql&logoColor=white" />
    <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" />
    <img src="https://img.shields.io/badge/OpenStreetMap-7EBC6F?style=for-the-badge&logo=openstreetmap&logoColor=white" />
  </p>
</div>

---

## Overview

**PharmaVisit CRM** is a full-stack field management system built for pharmaceutical sales representatives operating in the **Rabat-Sale-Kenitra region of Morocco**. It solves a real operational problem: how to efficiently plan and optimize a day of medical visits starting directly from the rep's current GPS location.

- A **real-time interactive map** with 600+ geocoded healthcare providers
- **Automatic GPS-based route optimization** using Google OR-Tools (TSP solver)
- **Real medical data** scraped from OpenStreetMap via Overpass API and Nominatim
- A **territory-scoped REST API** built with Laravel 11 and Redis caching
- A **Python microservice** for route computation backed by OSRM real-road routing

---

## Features

| Feature | Description |
|---------|-------------|
| Interactive Map | Dark-mode Leaflet.js map with 600+ clustered markers (Rabat, Sale, Temara) |
| Live GPS Tracking | watchPosition() — marker updates automatically as you move |
| Route Optimization | OR-Tools TSP solver — shortest path from your location through selected stops |
| Smart Search | Search by name, specialty, or city across all 600+ records |
| Multi-type Support | Doctors, pharmacies, clinics, hospitals, dentists — all on one map |
| Visit Logging | Record outcomes and notes for each completed visit |
| Territory Isolation | Each rep sees only their assigned territory's data |
| Redis Caching | API responses cached 10 minutes per territory + filter set |
| Premium Dark UI | Glassmorphism design with animated GPS marker and route overlay |

---

## Architecture

```
Browser SPA (Leaflet.js + Vanilla JS + CSS)
    |  REST JSON
Laravel 11 :8000  <-->  MySQL 8  +  Redis
    |  HTTP
FastAPI Microservice :8001
    ├── OR-Tools TSP Solver
    ├── OSRM real-road matrix
    ├── Haversine fallback
    └── Nominatim geocoder

Data Pipeline (Python)
    fetch_all_rabat.py  →  clean_data.py  →  import_data.py
    (Overpass + Nominatim)    (filter)         (MySQL)
```

---

## Data Sources

All data is collected from **free, open, public sources** — no API key required.

### Overpass API (OpenStreetMap)
**URL:** `https://overpass-api.de/api/interpreter`

Queries all healthcare OSM nodes in the Rabat-Sale-Temara bounding box `(33.85,-7.00,34.10,-6.70)` — doctors, pharmacies, clinics, hospitals, dentists, and all `healthcare=*` tagged nodes.

Result: **681 raw elements → 616 valid records**

### Nominatim (OSM Geocoding)
**URL:** `https://nominatim.openstreetmap.org/search`

90+ text queries at >= 1 second intervals covering:
- Specialties: `cardiologue Rabat`, `dentiste Sale`, `pharmacie Temara` ...
- Neighborhoods: `medecin Agdal Rabat`, `doctor Hay Riad` ...

Result: **225 unique → 150 valid records**

### Data Cleaning Pipeline

| Stage | Action | Records removed |
|-------|--------|----------------|
| Geo-filter | Remove lat > 35.5 or lng > 0 (Malta/Europe) | 0 |
| Entity-filter | Remove streets, labs, non-medical entities | 21 |
| Deduplication | Dedupe by name + coordinates | 1 |
| **Final** | **604 clean records imported** | |

---

## Route Optimization Algorithm

Solves the **Open Travelling Salesman Problem** — shortest path visiting N stops from GPS start, no return required.

### 1. Travel Time Matrix

**OSRM** (primary) — real road network:
```
GET /table/v1/driving/{coords}?annotations=duration,distance
```

**Haversine** (fallback) — straight-line distance:
```
d = 2R · atan2(sqrt(a), sqrt(1-a))
where a = sin(Δlat/2)² + cos(lat1)·cos(lat2)·sin(Δlng/2)²
Duration proxy = distance_m / 14   (~50 km/h urban)
```

### 2. TSP Solver — Google OR-Tools

```python
# Open TSP via dummy end depot (zero-cost arcs from all nodes)
params.first_solution_strategy = PATH_CHEAPEST_ARC
params.local_search_metaheuristic = GUIDED_LOCAL_SEARCH
params.time_limit.seconds = 5
```

**Fallback: Nearest-Neighbor O(N²)** — when OR-Tools unavailable or times out.

### 3. Route Geometry

Ordered stops sent to OSRM Route API → returns GeoJSON LineString drawn on the Leaflet map.

---

## Tech Stack

| Layer | Technology | Role |
|-------|------------|------|
| Backend | Laravel 11 (PHP 8.3) | REST API, auth, Eloquent ORM |
| Auth | Laravel Sanctum | Bearer token authentication |
| Database | MySQL 8 | Primary data store (166 doctors, 492 pharmacies) |
| Cache | Redis 7 | 10-min API response cache |
| Optimizer | FastAPI (Python 3.12) | Route optimization microservice |
| TSP Solver | Google OR-Tools | Near-optimal TSP solution |
| Routing | OSRM | Real-road distance matrices |
| Geocoding | Nominatim | Address-to-coordinate conversion |
| Map | Leaflet.js + markercluster | Interactive map with clustering |
| Tiles | OpenStreetMap / CartoDB Dark | Dark mode base map |
| GPS | navigator.geolocation | Browser native live tracking |
| Frontend | Vanilla JS + CSS Variables | SPA without frameworks |

---

## Setup

### Prerequisites
- PHP 8.3 + Composer
- Python 3.12 + pip
- MySQL 8
- Redis

### Install

```bash
git clone https://github.com/saifeddinekhannoufi0-lab/PharmaVisit-CRM.git
cd PharmaVisit-CRM

# Laravel
composer install
cp .env.example .env
# Edit .env with your DB credentials
php artisan key:generate
php artisan migrate
php artisan db:seed

# Python microservice
cd route-optimizer
pip install -r requirements.txt
cd ..
```

### Run

```bash
# Windows (one command):
start.bat

# Or manually:
php artisan serve                              # API  → :8000
cd route-optimizer && uvicorn main:app --port 8001  # Optimizer → :8001
redis-server                                        # Cache
```

### Login

| Name | Email | Password | Territory |
|------|-------|----------|-----------|
| Sarah Bennani | sarah@pharmavisit.ma | password | Grand Rabat |
| Karim Tazi | karim@pharmavisit.ma | password | Grand Rabat |
| Nadia El Fassi | nadia@pharmavisit.ma | password | Casablanca Nord |

---

## Refresh Data (optional)

```bash
cd data-pipeline
python fetch_all_rabat.py   # scrape Overpass API + Nominatim
python clean_data.py        # filter and deduplicate
python import_data.py       # idempotent MySQL import
```

---

## API Reference

All routes require `Authorization: Bearer {token}`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/login | Authenticate, receive token |
| GET | /api/territory | Your territory + stats |
| GET | /api/doctors | Paginated, filterable doctor list |
| GET | /api/doctors/{id} | Detail + last 5 visits |
| POST | /api/doctors | Create doctor |
| PUT | /api/doctors/{id} | Update doctor |
| DELETE | /api/doctors/{id} | Soft-delete doctor |
| GET | /api/pharmacies | Paginated pharmacy list |
| POST | /api/routes/optimize | Compute optimized route |
| POST | /api/visits | Log a completed visit |

---

## Data Statistics

| Metric | Value |
|--------|-------|
| Doctors in database | 166 |
| Pharmacies in database | 492 |
| Data source | OpenStreetMap (Overpass + Nominatim) |
| Coverage | Rabat · Sale · Temara |
| Coordinates range | 33.94–34.02°N · -6.90–-6.82°W |
| Specialties | 14 types |

---

## License & Attribution

Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors — **ODbL license**
Map tiles © [CARTO](https://carto.com/attributions)

---

<div align="center">
  <sub>Built for the Moroccan pharmaceutical field by Saifeddine Khannoufi</sub>
</div>
