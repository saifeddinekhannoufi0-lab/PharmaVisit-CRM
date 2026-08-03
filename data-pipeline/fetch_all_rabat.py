"""
Overpass API scraper for Rabat region healthcare data.
Queries OSM for all medical/healthcare amenities in Rabat + Salé + Témara.
"""
import urllib.request
import urllib.parse
import json
import csv
import time
import sys
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "output" / "raw_doctors.csv"

FIELDNAMES = ["first_name", "last_name", "specialty", "address", "city",
              "postal_code", "region", "phone", "source", "lat", "lng"]

# ── Overpass query: all healthcare in Rabat-Salé-Témara bounding box ─────────
# Bounding box covers Rabat, Salé, Témara, and suburbs
# south,west,north,east = 33.85,-7.00,34.10,-6.70
OVERPASS_QUERY = """
[out:json][timeout:120];
(
  // Rabat area by bounding box (wider: Rabat + Salé + Témara)
  node["amenity"="doctors"](33.85,-7.00,34.10,-6.70);
  way["amenity"="doctors"](33.85,-7.00,34.10,-6.70);
  node["amenity"="clinic"](33.85,-7.00,34.10,-6.70);
  way["amenity"="clinic"](33.85,-7.00,34.10,-6.70);
  node["amenity"="hospital"](33.85,-7.00,34.10,-6.70);
  way["amenity"="hospital"](33.85,-7.00,34.10,-6.70);
  node["amenity"="dentist"](33.85,-7.00,34.10,-6.70);
  way["amenity"="dentist"](33.85,-7.00,34.10,-6.70);
  node["amenity"="pharmacy"](33.85,-7.00,34.10,-6.70);
  way["amenity"="pharmacy"](33.85,-7.00,34.10,-6.70);
  node["healthcare"](33.85,-7.00,34.10,-6.70);
  way["healthcare"](33.85,-7.00,34.10,-6.70);
  // Also search by named area
  area["name"="Rabat"]->.rabat;
  node["amenity"="doctors"](area.rabat);
  way["amenity"="doctors"](area.rabat);
  node["amenity"="clinic"](area.rabat);
  way["amenity"="clinic"](area.rabat);
  node["amenity"="pharmacy"](area.rabat);
  way["amenity"="pharmacy"](area.rabat);
  node["healthcare"](area.rabat);
  way["healthcare"](area.rabat);
);
out center;
"""

# ── Additional Nominatim queries for neighborhood-level coverage ──────────────
NOMINATIM_QUERIES = [
    # By specialty
    "doctor Rabat", "médecin Rabat", "docteur Rabat",
    "clinic Rabat", "clinique Rabat",
    "dentist Rabat", "dentiste Rabat",
    "cardiologue Rabat", "pédiatre Rabat",
    "ophtalmologue Rabat", "gynécologue Rabat",
    "dermatologue Rabat", "chirurgien Rabat",
    "radiologue Rabat", "ORL Rabat",
    "pneumologue Rabat", "gastro Rabat",
    "néphrologue Rabat", "urologue Rabat",
    "rhumatologue Rabat", "endocrinologue Rabat",
    "psychiatre Rabat", "neurologue Rabat",
    # By neighborhood
    "doctor Agdal Rabat", "médecin Agdal Rabat",
    "doctor Hassan Rabat", "médecin Hassan Rabat",
    "doctor Hay Riad Rabat", "médecin Hay Riad Rabat",
    "doctor Souissi Rabat", "médecin Souissi Rabat",
    "doctor Océan Rabat", "médecin Océan Rabat",
    "doctor Yacoub El Mansour Rabat",
    "doctor Akkari Rabat", "médecin Akkari Rabat",
    "doctor Diour Jamaa Rabat",
    "doctor Takaddoum Rabat",
    "cabinet médical Rabat", "centre médical Rabat",
    "polyclinique Rabat", "laboratoire analyse Rabat",
    # Salé
    "doctor Salé", "médecin Salé", "clinique Salé",
    "dentiste Salé", "pharmacy Salé",
    # Témara
    "doctor Témara", "médecin Témara", "clinique Témara",
    # Pharmacies
    "pharmacy Rabat", "pharmacie Rabat",
    "pharmacie Agdal Rabat", "pharmacie Hassan Rabat",
    "pharmacie Hay Riad Rabat", "pharmacie Souissi Rabat",
    "pharmacie Océan Rabat",
    "pharmacy Salé", "pharmacie Salé",
    "pharmacy Témara", "pharmacie Témara",
]


def guess_specialty(tags, name_lower):
    """Determine specialty from OSM tags and name."""
    amenity = tags.get("amenity", "")
    healthcare = tags.get("healthcare", "")
    hc_spec = tags.get("healthcare:speciality", "").lower()

    if amenity == "pharmacy" or healthcare == "pharmacy":
        return "Pharmacie"
    if amenity == "dentist" or "dent" in name_lower:
        return "Dentiste"
    if amenity == "hospital" or healthcare == "hospital":
        return "Hôpital"
    if amenity == "clinic" or healthcare == "clinic" or "clinique" in name_lower:
        return "Clinique"

    # Check healthcare:speciality tag
    spec_map = {
        "cardio": "Cardiologie", "ophtalmo": "Ophtalmologie",
        "pédiat": "Pédiatrie", "pediatr": "Pédiatrie",
        "gynéco": "Gynécologie", "gyneco": "Gynécologie",
        "derma": "Dermatologie", "neuro": "Neurologie",
        "chir": "Chirurgie", "radio": "Radiologie",
        "orl": "ORL", "pneumo": "Pneumologie",
        "gastro": "Gastro-entérologie", "uro": "Urologie",
        "rhumato": "Rhumatologie", "endocrino": "Endocrinologie",
        "psychiatr": "Psychiatrie", "néphro": "Néphrologie",
    }

    check_str = hc_spec + " " + name_lower
    for key, val in spec_map.items():
        if key in check_str:
            return val

    if healthcare == "laboratory" or "labo" in name_lower:
        return "Laboratoire"

    return "Médecine Générale"


def parse_name(name_str):
    """Split an OSM name into first_name and last_name."""
    if not name_str:
        return "Dr", "Unknown"

    # Common prefixes
    prefixes = ["Dr.", "Dr", "Cabinet", "Docteur", "Clinique", "Centre",
                "Polyclinique", "Pharmacie", "Laboratoire"]

    parts = name_str.strip().split(" ", 1)
    first = parts[0] if parts else "Dr"
    last = parts[1] if len(parts) > 1 else name_str

    return first, last


def guess_city(lat, lng, tags):
    """Guess city from coordinates."""
    city = tags.get("addr:city", "")
    if city:
        return city

    # Based on approximate coordinates
    if lat and lng:
        lat_f, lng_f = float(lat), float(lng)
        if lng_f < -6.88:  # West side
            if lat_f > 34.02:
                return "Salé"
            return "Rabat"
        if lat_f > 34.05:
            return "Salé"
        if lat_f < 33.92:
            return "Témara"
    return "Rabat"


def fetch_overpass():
    """Fetch healthcare data from Overpass API."""
    print("[overpass] Querying Overpass API for Rabat region...")

    data = urllib.parse.urlencode({'data': OVERPASS_QUERY}).encode('utf-8')
    req = urllib.request.Request(
        'https://overpass-api.de/api/interpreter',
        data=data,
        headers={'User-Agent': 'PharmaVisitCRM/2.0 DataPipeline'}
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res = json.loads(response.read().decode('utf-8'))
            elements = res.get('elements', [])
            print(f"[overpass] Got {len(elements)} raw elements")
            return elements
    except Exception as e:
        print(f"[overpass] Error: {e}")
        return []


def fetch_nominatim():
    """Fetch additional data from Nominatim with expanded queries."""
    all_results = []
    seen_places = set()
    headers = {'User-Agent': 'PharmaVisitCRM/2.0 DataPipeline'}

    for i, query in enumerate(NOMINATIM_QUERIES):
        pct = int((i + 1) / len(NOMINATIM_QUERIES) * 100)
        print(f"[nominatim] ({pct}%) Fetching '{query}'...")

        url = (
            f"https://nominatim.openstreetmap.org/search"
            f"?q={urllib.parse.quote(query)}"
            f"&format=json&limit=50&addressdetails=1"
            f"&viewbox=-7.00,34.10,-6.70,33.85&bounded=1"
        )

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                for item in data:
                    place_id = item.get("place_id")
                    if place_id in seen_places:
                        continue
                    seen_places.add(place_id)
                    all_results.append(item)
        except Exception as e:
            print(f"[nominatim] Error on '{query}': {e}")

        # Rate limit: 1 req/sec for Nominatim
        time.sleep(1.1)

    print(f"[nominatim] Got {len(all_results)} unique results")
    return all_results


def process_overpass_elements(elements):
    """Convert Overpass elements to doctor records."""
    records = []
    seen_keys = set()

    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", "")

        if not name:
            name = tags.get("name:fr", tags.get("name:ar", ""))
        if not name:
            continue  # Skip unnamed nodes

        # Get coordinates
        lat = el.get("lat") or (el.get("center", {}).get("lat") if el.get("center") else None)
        lng = el.get("lon") or (el.get("center", {}).get("lon") if el.get("center") else None)

        if not lat or not lng:
            continue

        # Skip if outside Morocco (safety check)
        if float(lat) > 35.5 or float(lng) > 0:
            continue

        # Dedup key
        dedup_key = f"{name.lower().strip()}_{float(lat):.4f}_{float(lng):.4f}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        first_name, last_name = parse_name(name)
        specialty = guess_specialty(tags, name.lower())
        city = guess_city(lat, lng, tags)

        address = tags.get("addr:street", "")
        if tags.get("addr:housenumber"):
            address = f"{tags['addr:housenumber']} {address}".strip()
        if not address:
            address = name  # Use name as fallback address

        phone = tags.get("phone", tags.get("contact:phone", ""))
        postal = tags.get("addr:postcode", "")

        records.append({
            "first_name": first_name,
            "last_name": last_name,
            "specialty": specialty,
            "address": address,
            "city": city,
            "postal_code": postal,
            "region": "Rabat-Salé-Kénitra",
            "phone": phone,
            "source": "overpass",
            "lat": f"{float(lat):.7f}",
            "lng": f"{float(lng):.7f}",
        })

    return records


def process_nominatim_results(results):
    """Convert Nominatim results to doctor records."""
    records = []
    seen_keys = set()

    for item in results:
        addr = item.get("address", {})
        lat = item.get("lat")
        lng = item.get("lon")

        if not lat or not lng:
            continue

        # Skip outside Morocco
        if float(lat) > 35.5 or float(lng) > 0:
            continue

        name_str = item.get("name", "") or item.get("display_name", "").split(",")[0]
        if not name_str:
            continue

        dedup_key = f"{name_str.lower().strip()}_{float(lat):.4f}_{float(lng):.4f}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        first_name, last_name = parse_name(name_str)
        specialty = guess_specialty({}, name_str.lower())

        osm_type = item.get("type", "")
        if osm_type == "pharmacy" or "pharma" in name_str.lower():
            specialty = "Pharmacie"
        elif osm_type == "dentist" or "dent" in name_str.lower():
            specialty = "Dentiste"
        elif osm_type == "hospital":
            specialty = "Hôpital"
        elif "clinique" in name_str.lower() or "clinic" in name_str.lower():
            specialty = "Clinique"

        city = addr.get("city", addr.get("town", "Rabat"))
        if "Rabat" not in str(city) and "Salé" not in str(city) and "Témara" not in str(city):
            city = "Rabat"

        address = addr.get("road", item.get("display_name", "").split(",")[0])
        postal_code = addr.get("postcode", "")
        phone = ""

        records.append({
            "first_name": first_name,
            "last_name": last_name,
            "specialty": specialty,
            "address": address,
            "city": city,
            "postal_code": postal_code,
            "region": "Rabat-Salé-Kénitra",
            "phone": phone,
            "source": "nominatim",
            "lat": f"{float(lat):.7f}",
            "lng": f"{float(lng):.7f}",
        })

    return records


def merge_and_dedup(overpass_records, nominatim_records):
    """Merge and deduplicate records from both sources."""
    seen = set()
    merged = []

    # Overpass data is higher quality (has tags), so prioritize it
    for r in overpass_records + nominatim_records:
        key = f"{r['last_name'].lower().strip()}_{float(r['lat']):.3f}_{float(r['lng']):.3f}"
        if key not in seen:
            seen.add(key)
            merged.append(r)

    return merged


def main():
    print("=" * 60)
    print("PharmaVisit Data Scraper — Rabat Region")
    print("=" * 60)

    # ── Step 1: Overpass API (OSM database) ──────────────────────────────
    overpass_elements = fetch_overpass()
    overpass_records = process_overpass_elements(overpass_elements)
    print(f"[overpass] Processed {len(overpass_records)} valid records")

    # Show breakdown by type
    types = {}
    for r in overpass_records:
        types[r["specialty"]] = types.get(r["specialty"], 0) + 1
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    # ── Step 2: Nominatim (expanded queries) ─────────────────────────────
    nominatim_results = fetch_nominatim()
    nominatim_records = process_nominatim_results(nominatim_results)
    print(f"[nominatim] Processed {len(nominatim_records)} valid records")

    # ── Step 3: Merge & dedup ────────────────────────────────────────────
    all_records = merge_and_dedup(overpass_records, nominatim_records)
    print(f"\n[TOTAL] {len(all_records)} unique records after merge")

    # Final breakdown
    types = {}
    for r in all_records:
        types[r["specialty"]] = types.get(r["specialty"], 0) + 1
    print("\nFinal breakdown:")
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    # ── Step 4: Write CSV ────────────────────────────────────────────────
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for rec in all_records:
            writer.writerow(rec)

    print(f"\n[OK] Wrote {len(all_records)} records to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
