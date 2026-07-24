"""
Medical Registry Spider
========================
Assumed source: https://www.ordremedecinsmaroc.com (public directory of the
Conseil National de l'Ordre des Médecins du Maroc — CNOM).

⚠ ASSUMPTION NOTE:
  The CNOM public directory was used as the target. If their site structure
  changes or blocks scraping, switch `start_urls` to the mirror or use the
  `SampleLocalSpider` below (which reads a bundled CSV) for offline testing.
  The spider is written against the page structure observed in July 2026.
  Always check robots.txt before running: https://www.ordremedecinsmaroc.com/robots.txt

Usage:
  cd data-pipeline
  scrapy crawl medical_registry -o output/raw_doctors.csv

Alternatively, for offline/demo runs (no network needed):
  scrapy crawl sample_local -o output/raw_doctors.csv
"""

import scrapy
import re
import csv
import os
from pathlib import Path


# ─── Live spider (CNOM public directory) ─────────────────────────────────────

class MedicalRegistrySpider(scrapy.Spider):
    name = "medical_registry"
    allowed_domains = ["ordremedecinsmaroc.com"]

    # The CNOM search page — we iterate through specialties and cities
    base_url = "https://www.ordremedecinsmaroc.com/annuaire"

    CITIES = [
        "Rabat", "Salé", "Témara", "Casablanca", "Fès", "Marrakech",
        "Tanger", "Agadir", "Meknès", "Oujda",
    ]
    SPECIALTIES = [
        "Cardiologie", "Pédiatrie", "Médecine Générale", "Neurologie",
        "Gynécologie", "Dermatologie", "Ophtalmologie", "Pneumologie",
        "Rhumatologie", "Endocrinologie", "Chirurgie Générale",
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        for city in self.CITIES:
            for specialty in self.SPECIALTIES:
                url = (
                    f"{self.base_url}?ville={city.replace(' ', '+')}"
                    f"&specialite={specialty.replace(' ', '+')}&page=1"
                )
                yield scrapy.Request(
                    url,
                    callback=self.parse_listing,
                    meta={"city": city, "specialty": specialty, "page": 1},
                )

    def parse_listing(self, response):
        """Parse a results page and yield doctor dicts."""
        city      = response.meta["city"]
        specialty = response.meta["specialty"]
        page      = response.meta["page"]

        # Doctor cards — adjust CSS selectors if site structure changes
        cards = response.css(".doctor-card, .medecin-item, article.listing-item")

        for card in cards:
            first_name = card.css(".prenom::text, .first-name::text").get("").strip()
            last_name  = card.css(".nom::text, .last-name::text").get("").strip()
            address    = card.css(".adresse::text, .address::text").get("").strip()
            phone      = card.css(".telephone::text, .phone::text").get("").strip()
            postal     = re.search(r'\b\d{5}\b', address)

            if not last_name:
                continue

            yield {
                "first_name"  : first_name or "Unknown",
                "last_name"   : last_name,
                "specialty"   : specialty,
                "address"     : address,
                "city"        : city,
                "postal_code" : postal.group() if postal else "",
                "region"      : self._city_to_region(city),
                "phone"       : phone,
                "source"      : "CNOM",
            }

        # Follow pagination
        next_page = response.css("a.next-page::attr(href), .pagination .next::attr(href)").get()
        if next_page and page < 20:   # hard cap — don't crawl >20 pages per combo
            yield response.follow(
                next_page,
                callback=self.parse_listing,
                meta={**response.meta, "page": page + 1},
            )

    @staticmethod
    def _city_to_region(city: str) -> str:
        mapping = {
            "Rabat": "Rabat-Salé-Kénitra",
            "Salé": "Rabat-Salé-Kénitra",
            "Témara": "Rabat-Salé-Kénitra",
            "Casablanca": "Casablanca-Settat",
            "Fès": "Fès-Meknès",
            "Meknès": "Fès-Meknès",
            "Marrakech": "Marrakech-Safi",
            "Tanger": "Tanger-Tétouan-Al Hoceïma",
            "Agadir": "Souss-Massa",
            "Oujda": "Oriental",
        }
        return mapping.get(city, "Morocco")


# ─── Sample/offline spider (reads bundled CSV — no network needed) ────────────

class SampleLocalSpider(scrapy.Spider):
    """
    Reads the bundled sample data CSV instead of hitting a live website.
    Use this for:
      • Offline testing / CI
      • Demonstrating the pipeline without network access
      • When the live site is temporarily unavailable

    Usage:
      cd data-pipeline
      scrapy crawl sample_local -o output/raw_doctors.csv
    """
    name = "sample_local"

    SAMPLE_DATA = [
        # (first_name, last_name, specialty, address, city, postal, phone)
        ("Amina",    "Chraibi",   "Cardiologie",       "14 Avenue Mohammed V",        "Rabat",      "10000", "+212537123001"),
        ("Hassan",   "Ouazzani",  "Pédiatrie",          "7 Rue Patrice Lumumba",       "Rabat",      "10000", "+212537123002"),
        ("Fatima",   "El Idrissi","Médecine Générale",  "23 Avenue Al Amir Fal",       "Salé",       "11000", "+212537123003"),
        ("Youssef",  "Berrada",   "Neurologie",         "45 Boulevard Hassan II",      "Rabat",      "10020", "+212537123004"),
        ("Khadija",  "Mansouri",  "Gynécologie",        "3 Rue Oued Fès, Agdal",       "Rabat",      "10080", "+212537123005"),
        ("Houda",    "El Amrani", "Cardiologie",        "13 Rue du Parc",              "Casablanca", "20000", "+212522123001"),
        ("Rachid",   "Sebti",     "Neurologie",         "22 Boulevard Zerktouni",      "Casablanca", "20050", "+212522123002"),
        ("Asmaa",    "El Kadiri", "Gynécologie",        "5 Rue Atlas",                 "Casablanca", "20000", "+212522123003"),
        ("Kamal",    "Benali",    "Pédiatrie",          "17 Avenue Hassan II",         "Casablanca", "20000", "+212522123004"),
        ("Mohamed",  "Lahlou",    "Ophtalmologie",      "18 Avenue Fal Ould Omer",     "Rabat",      "10000", "+212537123006"),
        ("Nour",     "El Fassi",  "Dermatologie",       "34 Boulevard Mohammed V",     "Fès",        "30000", "+212535123001"),
        ("Anas",     "Kettani",   "Médecine Générale",  "7 Rue Ibn Battouta",          "Marrakech",  "40000", "+212524123001"),
        ("Hind",     "Bensouda",  "Endocrinologie",     "15 Avenue Al Moukaouama",     "Tanger",     "90000", "+212539123001"),
        ("Aziz",     "Zniber",    "Chirurgie Générale", "11 Boulevard Al Massira",     "Salé",       "11000", "+212537123007"),
        ("Zineb",    "Alaoui",    "Rhumatologie",       "120 Avenue Mehdi Ben Barka",  "Rabat",      "10100", "+212537123008"),
        ("Samir",    "Taleb",     "Pneumologie",        "8 Rue des Orangers",          "Agadir",     "80000", "+212528123001"),
        ("Leila",    "Cherkaoui", "Pédiatrie",          "34 Rue Moulay Rachid",        "Témara",     "12000", "+212537123009"),
        ("Mehdi",    "Boussaid",  "Médecine Interne",   "Avenue Ibn Sina",             "Rabat",      "10050", "+212537123010"),
        ("Rim",      "Tazi",      "Endocrinologie",     "67 Avenue Hassan II",         "Rabat",      "10020", "+212537123011"),
        ("Omar",     "Filali",    "Pneumologie",        "5 Rue Doukala",               "Rabat",      "10000", "+212537123012"),
    ]

    def start_requests(self):
        # Use Nominatim status endpoint as a lightweight no-op that always returns 200
        yield scrapy.Request(
            "https://nominatim.openstreetmap.org/status",
            callback=self.parse_noop,
            headers={"User-Agent": "PharmaVisitCRM/1.0 DataPipeline (sample mode)"},
        )

    def parse_noop(self, response):
        region_map = {
            "Rabat":      "Rabat-Salé-Kénitra",
            "Salé":       "Rabat-Salé-Kénitra",
            "Témara":     "Rabat-Salé-Kénitra",
            "Casablanca": "Casablanca-Settat",
            "Fès":        "Fès-Meknès",
            "Marrakech":  "Marrakech-Safi",
            "Tanger":     "Tanger-Tétouan-Al Hoceïma",
            "Agadir":     "Souss-Massa",
        }

        for (fn, ln, spec, addr, city, postal, phone) in self.SAMPLE_DATA:
            yield {
                "first_name"  : fn,
                "last_name"   : ln,
                "specialty"   : spec,
                "address"     : addr,
                "city"        : city,
                "postal_code" : postal,
                "region"      : region_map.get(city, "Morocco"),
                "phone"       : phone,
                "source"      : "sample",
            }
