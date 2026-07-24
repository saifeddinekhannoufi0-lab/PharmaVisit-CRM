# PharmaVisit CRM

PharmaVisit is a comprehensive Customer Relationship Management (CRM) and Field Representative Dashboard designed specifically for managing and optimizing visits to healthcare professionals (Doctors and Pharmacies).

## Key Features

- **Field Rep Dashboard**: An intuitive interface for representatives to manage their assigned territories, view statistics, and track visits.
- **Route Optimization Microservice**: A dedicated Python/FastAPI microservice leveraging OR-Tools and Mapbox to calculate the most efficient driving routes for field reps, minimizing travel time and distance.
- **Redis Performance Buffer**: High-performance caching layer using Redis to significantly reduce MySQL bottlenecks. It caches doctor/pharmacy lists, territory statistics, and optimized route results to avoid redundant, expensive API calls and database queries.
- **Automated Data Pipeline**: Built-in data extraction pipeline (using Scrapy) to scrape, clean, and import medical registry data into the platform.
- **Interactive Maps**: Visual mapping of doctors, pharmacies, and optimized daily routes using Leaflet.js.
- **RESTful API Architecture**: Robust APIs to manage Territories, Doctors, Pharmacies, Route Stops, and Visit Logs.

## Technology Stack

- **Backend (Main Application)**: Laravel (PHP 8+), MySQL, Redis
- **Backend (Route Optimizer)**: Python, FastAPI, OR-Tools, Mapbox
- **Frontend**: Blade, JavaScript, Vanilla CSS, Leaflet.js
- **Data Scraping**: Python, Scrapy, Pandas
- **Caching & Sessions**: Redis

## The Redis Implementation (Performance Buffer)

- **What it is:** An incredibly fast, in-memory caching database.
- **Which problems it solves:**
  - **Fixes Laravel & MySQL bottlenecks:** Instead of Laravel asking MySQL for the exact same list of doctors every time a user logs in, it asks once and saves the result in Redis. The next time, Redis delivers the data instantly, taking the heavy workload off MySQL.
  - **Saves API Costs:** If you calculate the optimized route between "Doctor A" and "Pharmacy B" on Monday, Redis memorizes that route. If another commercial rep needs the exact same route on Tuesday, Laravel pulls it from Redis instead of paying Mapbox or OR-Tools to calculate it all over again. (24-hour TTL for routes, auto-invalidation on data mutation).

## Project Structure

- `/app` - Laravel application core (Controllers, Models, Services)
- `/route-optimizer` - Python microservice for TSP route optimization
- `/data-pipeline` - Python web scraping and data preparation scripts
- `/public` - Compiled frontend assets
- `/routes` - Web and API route definitions

## Setup and Installation

### 1. Laravel Application
```bash
composer install
cp .env.example .env
php artisan key:generate
php artisan migrate --seed
```

### 2. Route Optimizer Microservice
Navigate to `/route-optimizer`:
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --port 8001
```

### 3. Data Pipeline
Navigate to `/data-pipeline`:
```bash
pip install -r requirements.txt
scrapy crawl medical_registry
```

### 4. Running the Development Server
```bash
npm install
npm run dev
php artisan serve
```

---
*Developed for optimal healthcare CRM management.*
