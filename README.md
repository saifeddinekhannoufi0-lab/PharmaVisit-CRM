<div align="center">

<h1>⚕️ PharmaVisit CRM</h1>
<p><strong>Field Service Routing & Management for Pharma Sales Reps</strong></p>

<p>
  <img src="https://img.shields.io/badge/Laravel-FF2D20?style=for-the-badge&logo=laravel&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
</p>

<p>PharmaVisit transforms field sales management into a seamless, optimized experience — combining intelligent route planning, high-speed data caching, interactive cartography, and a premium UI to maximize reps' time on the road.</p>

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧑‍💼 **Field Rep Dashboard** | Intuitive interface for representatives to manage territories, view stats, and track visits |
| 🗺️ **Interactive Maps** | Visual mapping of doctors, pharmacies, and optimized daily routes using Leaflet.js |
| 🚀 **Route Optimizer Engine** | Dedicated Python/FastAPI microservice leveraging Google OR-Tools to calculate highly efficient TSP routes |
| ⚡ **Redis Performance Buffer** | Caches API responses and routes, drastically reducing MySQL bottlenecks and API latency |
| 🤖 **Data Acquisition Pipeline** | Built-in Scrapy and Pandas pipeline to extract, clean, and import medical registry data |
| 🎨 **Premium UI & Branding** | Dark-mode design with PHI teal palette, custom SVG iconography, and CSS micro-animations |
| 🔌 **RESTful API** | Robust APIs built with Laravel Sanctum to manage Territories, Doctors, Pharmacies, Route Stops, and Visit Logs |

---

## 🏗️ Tech Stack

### Frontend
- **Blade** + **Vanilla JS/CSS** — modern templating and sleek, dependency-free styling
- **Leaflet.js** — lightweight, interactive cartography and mapping
- **Custom SVGs** — scalable, inline vector icons replacing heavy font libraries

### Core Backend (Orchestrator)
- **Laravel (PHP 8+)** — core application logic and RESTful API framework
- **MySQL** — secure, relational database for entities and user data
- **Redis** — high-performance in-memory caching layer for queries and optimization results
- **Sanctum** — lightweight authentication system for APIs

### Microservices & Data Pipelines
- **Python + FastAPI** — Route Optimizer microservice (lightning-fast, async APIs)
- **Google OR-Tools** — advanced routing and Travelling Salesperson Problem (TSP) solver
- **Mapbox & OpenStreetMap (Nominatim)** — geocoding and distance matrix calculation
- **Scrapy & Pandas** — robust data scraping, parsing, and cleaning

---

## 🚀 Getting Started

### Prerequisites
- PHP ≥ 8.1 and Composer
- Python ≥ 3.10
- Node.js & npm
- MySQL server running locally
- Redis server running locally

### 1. Clone the repository
```bash
git clone https://github.com/saifeddinekhannoufi0-lab/PharmaVisit-CRM.git
cd PharmaVisit-CRM
```

### 2. Set up the Laravel Core Application
```bash
composer install
cp .env.example .env
# Edit .env with your MySQL and Redis credentials
php artisan key:generate
php artisan migrate --seed
```

### 3. Set up the Route Optimizer Microservice
Open a new terminal window:
```bash
cd route-optimizer
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --port 8001
```

### 4. Running the Development Server
```bash
npm install
npm run dev
php artisan serve
```
The app will be running at `http://localhost:8000` and the Python routing microservice at `http://localhost:8001`.

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
APP_NAME=PharmaVisit
APP_ENV=local
APP_KEY=base64:...
APP_DEBUG=true
APP_URL=http://localhost:8000

# MySQL
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=pharmavisit
DB_USERNAME=root
DB_PASSWORD=your_password

# Redis Caching Layer
CACHE_DRIVER=redis
REDIS_CLIENT=predis
REDIS_HOST=127.0.0.1
REDIS_PASSWORD=null
REDIS_PORT=6379

# Microservices
ROUTE_OPTIMIZER_URL=http://localhost:8001
MAPBOX_API_KEY=pk.eyJ1...
```

---

## 📁 Project Structure

```text
PharmaVisit-CRM/
├── app/
│   ├── Http/Controllers/     # API endpoints and Web controllers
│   ├── Models/               # Eloquent Models (Doctor, Pharmacy, Route, VisitLog)
│   └── Services/
│       ├── CacheService.php  # Redis serialization and TTL management
│       └── RouteOptimizer.php# Bridge to the Python FastAPI microservice
├── route-optimizer/
│   ├── main.py               # FastAPI entry point
│   ├── schemas.py            # Pydantic validation models
│   └── services/
│       ├── router.py         # Google OR-Tools TSP logic
│       └── geocoder.py       # Mapbox/OSRM distance matrix fetching
├── data-pipeline/
│   ├── spiders/              # Scrapy spiders for medical registries
│   ├── import_data.py        # Pandas cleaning scripts
│   └── scrapy.cfg
├── public/
│   ├── css/pharmavisit.css   # Core design system and PHI Teal branding
│   └── js/pharmavisit.js     # Frontend routing logic and Leaflet implementation
└── resources/
    └── views/
        └── app.blade.php     # Main entry point and layout shell
```

---

## 🧠 System Architecture

**1. The Redis Performance Buffer**
To prevent MySQL bottlenecking, PharmaVisit caches all territory data natively in Redis. When a rep opens their dashboard, the 25-doctor paginated list and territory stats load instantly. When data is modified (e.g., adding a new doctor), `CacheService` triggers targeted tag invalidations ensuring data is always fresh while minimizing database strain.

**2. Asynchronous Route Optimization**
Calculating the "Travelling Salesman Problem" is computationally heavy. Instead of blocking the PHP thread, Laravel dispatches the list of selected geocoordinates to the Python `route-optimizer` microservice. Python leverages **Google OR-Tools** alongside the **Mapbox Matrix API** to compute the mathematically optimal route in milliseconds.

The result is then returned to Laravel, cached in Redis for 24 hours, and rendered on the frontend using Leaflet.js — ensuring that if another rep calculates a similar route, no external API quotas are consumed.

---

## 📜 License
This project is licensed under the MIT License — see the LICENSE file for details.

## 👨‍💻 Author

**Saifeddine Khannoufi**  
GitHub: [@saifeddinekhannoufi0-lab](https://github.com/saifeddinekhannoufi0-lab)  
*Built with ❤️ for optimal healthcare field management.*
