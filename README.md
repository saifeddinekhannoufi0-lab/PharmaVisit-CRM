<div align="center">

<h1>⚕️ PharmaVisit CRM</h1>
<p><strong>Field Service Routing & Management for Pharma Sales Reps</strong></p>

<p>
  <img src="https://img.shields.io/badge/Laravel-FF2D20?style=for-the-badge&logo=laravel&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white" />
</p>

<p>PharmaVisit is a comprehensive Customer Relationship Management (CRM) and Field Representative Dashboard designed specifically for managing and optimizing visits to healthcare professionals (Doctors and Pharmacies).</p>

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧑‍💼 **Field Rep Dashboard** | Intuitive interface for representatives to manage territories, view stats, and track visits |
| 🗺️ **Interactive Maps** | Visual mapping of doctors, pharmacies, and optimized daily routes using Leaflet.js |
| 🚀 **Route Optimizer** | Dedicated Python/FastAPI microservice leveraging OR-Tools to calculate efficient routes |
| ⚡ **Redis Performance Buffer** | Caches data and routes, reducing MySQL bottlenecks and expensive API calls |
| 🤖 **Automated Data Pipeline** | Built-in Scrapy data extraction pipeline to scrape and import medical registry data |
| 🎨 **Premium UI Integration** | Dark-mode design with PHI teal palette, custom SVGs, and CSS micro-animations |
| 🔌 **RESTful API** | Robust APIs to manage Territories, Doctors, Pharmacies, Route Stops, and Visit Logs |

---

## 🏗️ Tech Stack

### Frontend
- **Blade** + **Vanilla JS/CSS** — modern templating and styling
- **Leaflet.js** — interactive maps
- **Custom SVGs** — scalable vector icons

### Backend
- **Laravel (PHP 8+)** — core application logic and REST API
- **MySQL** — relational database
- **Redis** — high-performance caching layer

### Microservices & Data
- **Python + FastAPI** — Route Optimizer microservice
- **OR-Tools & Mapbox** — TSP solving and geocoding
- **Scrapy & Pandas** — data scraping and preparation

---

## 🚀 Getting Started

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
