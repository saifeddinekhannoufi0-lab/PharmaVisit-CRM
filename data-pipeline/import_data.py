"""
MySQL Import Script
=====================
Reads clean_doctors.csv and upserts records into the pharmavisit database.

Routing rules:
  • specialty == 'Pharmacie'    → pharmacies table
  • specialty == 'Laboratoire'  → skipped (labs are not targets)
  • everything else             → doctors table

KEY DESIGN DECISIONS:
  • Uses INSERT ... ON DUPLICATE KEY UPDATE so re-running is idempotent.
  • NEVER overwrites: notes, lat, lng, geocoded_at, priority, is_active.
    These are rep-curated fields — the pipeline must not clobber them.
  • New doctors are inserted with is_active=1, priority='medium'.
  • territory_id is assigned via the CITY→TERRITORY mapping below.

Run:
  cd data-pipeline
  python import_data.py

Environment variables (or edit the DB_* constants below):
  DB_HOST, DB_PORT, DB_DATABASE, DB_USERNAME, DB_PASSWORD
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import mysql.connector
import pandas as pd
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")  # reads Laravel's .env

# ─── Database connection ──────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "127.0.0.1"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "database": os.getenv("DB_DATABASE", "pharmavisit"),
    "user":     os.getenv("DB_USERNAME", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "charset":  "utf8mb4",
}

INPUT_FILE = Path(__file__).parent / "output" / "clean_doctors.csv"

# ─── Specialties that go to pharmacies table (not doctors) ───────────────────
PHARMACY_SPECIALTIES = {"Pharmacie"}
SKIP_SPECIALTIES     = {"Laboratoire"}   # not relevant for field visits

# ─── City → Territory mapping ─────────────────────────────────────────────────
CITY_TO_TERRITORY = {
    "Rabat":      1,   # Grand Rabat (MAR-RAB)
    "Salé":       1,
    "Témara":     1,
    "Casablanca": 2,   # Casablanca Nord (MAR-CAS)
}
DEFAULT_TERRITORY_ID = 1


def get_territory_id(city: str) -> int:
    return CITY_TO_TERRITORY.get(city, DEFAULT_TERRITORY_ID)


# ─── SQL statements ───────────────────────────────────────────────────────────
DOCTOR_UPSERT_SQL = """
INSERT INTO doctors (
    territory_id, first_name, last_name, specialty,
    address, city, postal_code, region, phone,
    lat, lng, priority, is_active, created_at, updated_at
)
VALUES (
    %(territory_id)s, %(first_name)s, %(last_name)s, %(specialty)s,
    %(address)s, %(city)s, %(postal_code)s, %(region)s, %(phone)s,
    %(lat)s, %(lng)s, 'medium', 1, NOW(), NOW()
)
ON DUPLICATE KEY UPDATE
    address      = IF(VALUES(address) != '', VALUES(address), address),
    city         = VALUES(city),
    postal_code  = IF(VALUES(postal_code) != '', VALUES(postal_code), postal_code),
    region       = VALUES(region),
    phone        = IF(VALUES(phone) != '', VALUES(phone), phone),
    lat          = IF(VALUES(lat) IS NOT NULL, VALUES(lat), lat),
    lng          = IF(VALUES(lng) IS NOT NULL, VALUES(lng), lng),
    updated_at   = NOW()
"""

PHARMACY_UPSERT_SQL = """
INSERT INTO pharmacies (
    territory_id, name, address, city, postal_code, region,
    phone, lat, lng, geocoded_at, is_active, created_at, updated_at
)
VALUES (
    %(territory_id)s, %(name)s, %(address)s, %(city)s, %(postal_code)s, %(region)s,
    %(phone)s, %(lat)s, %(lng)s, NOW(), 1, NOW(), NOW()
)
ON DUPLICATE KEY UPDATE
    address     = IF(VALUES(address) != '', VALUES(address), address),
    city        = VALUES(city),
    phone       = IF(VALUES(phone) != '', VALUES(phone), phone),
    lat         = IF(VALUES(lat) IS NOT NULL, VALUES(lat), lat),
    lng         = IF(VALUES(lng) IS NOT NULL, VALUES(lng), lng),
    updated_at  = NOW()
"""


def add_unique_index_if_missing(cursor):
    """Ensure the unique index used by ON DUPLICATE KEY exists on doctors."""
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = 'doctors'
          AND index_name = 'idx_doctor_unique'
    """)
    row = cursor.fetchone()
    if row[0] == 0:
        print("[import] Removing existing duplicates before creating index…")
        cursor.execute("""
            DELETE d1 FROM doctors d1
            INNER JOIN doctors d2
            WHERE d1.id > d2.id
              AND SUBSTRING(d1.last_name, 1, 80) = SUBSTRING(d2.last_name, 1, 80)
              AND SUBSTRING(d1.first_name, 1, 80) = SUBSTRING(d2.first_name, 1, 80)
              AND SUBSTRING(d1.city, 1, 80) = SUBSTRING(d2.city, 1, 80)
              AND SUBSTRING(d1.specialty, 1, 80) = SUBSTRING(d2.specialty, 1, 80)
        """)
        deleted = cursor.rowcount
        if deleted > 0:
            print(f"[import] Removed {deleted} duplicate rows")
        print("[import] Creating unique index idx_doctor_unique…")
        cursor.execute("""
            ALTER TABLE doctors
            ADD UNIQUE INDEX idx_doctor_unique (last_name(80), first_name(80), city(80), specialty(80))
        """)
        print("[import] Index created.")

    # Same for pharmacies (by name + city)
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = 'pharmacies'
          AND index_name = 'idx_pharmacy_unique'
    """)
    row = cursor.fetchone()
    if row[0] == 0:
        print("[import] Creating unique index on pharmacies…")
        cursor.execute("""
            ALTER TABLE pharmacies
            ADD UNIQUE INDEX idx_pharmacy_unique (name(120), city(80))
        """)
        print("[import] Pharmacy index created.")


def main():
    if not INPUT_FILE.exists():
        print(f"[ERROR] Clean data file not found: {INPUT_FILE}")
        print("Run clean_data.py first.")
        sys.exit(1)

    print(f"[import] Reading: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, dtype=str).fillna("")
    total = len(df)
    print(f"[import] {total} records to import")

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as e:
        print(f"[ERROR] DB connection failed: {e}")
        sys.exit(1)

    cursor = conn.cursor()

    # Ensure unique indexes exist
    add_unique_index_if_missing(cursor)
    conn.commit()

    doc_inserted = 0; doc_updated = 0
    pha_inserted = 0; pha_updated = 0
    skipped = 0; errors = 0

    for _, row in df.iterrows():
        specialty = row.get("specialty", "")

        # Skip labs and irrelevant entities
        if specialty in SKIP_SPECIALTIES:
            skipped += 1
            continue

        territory_id = get_territory_id(row.get("city", ""))
        lat = float(row["lat"]) if row.get("lat") else None
        lng = float(row["lng"]) if row.get("lng") else None

        # ── Route to pharmacies table ─────────────────────────────────────────
        if specialty in PHARMACY_SPECIALTIES:
            name = f"{row.get('first_name','')} {row.get('last_name','')}".strip()
            params = {
                "territory_id": territory_id,
                "name":         name,
                "address":      row.get("address", ""),
                "city":         row.get("city", ""),
                "postal_code":  row.get("postal_code", ""),
                "region":       row.get("region", "Rabat-Salé-Kénitra"),
                "phone":        row.get("phone", ""),
                "lat":          lat,
                "lng":          lng,
            }
            try:
                cursor.execute(PHARMACY_UPSERT_SQL, params)
                if cursor.rowcount == 1:   pha_inserted += 1
                elif cursor.rowcount == 2: pha_updated  += 1
            except mysql.connector.Error as e:
                print(f"[WARN] Pharmacy error '{name}': {e}")
                errors += 1
            continue

        # ── Route to doctors table ────────────────────────────────────────────
        params = {
            "territory_id": territory_id,
            "first_name":   row.get("first_name", ""),
            "last_name":    row.get("last_name", ""),
            "specialty":    specialty,
            "address":      row.get("address", ""),
            "city":         row.get("city", ""),
            "postal_code":  row.get("postal_code", ""),
            "region":       row.get("region", "Rabat-Salé-Kénitra"),
            "phone":        row.get("phone", ""),
            "lat":          lat,
            "lng":          lng,
        }
        try:
            cursor.execute(DOCTOR_UPSERT_SQL, params)
            if cursor.rowcount == 1:   doc_inserted += 1
            elif cursor.rowcount == 2: doc_updated  += 1
        except mysql.connector.Error as e:
            print(f"[WARN] Doctor error '{params['last_name']}': {e}")
            errors += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n[import] [OK] Done")
    print(f"  Doctors  → inserted: {doc_inserted}  updated: {doc_updated}")
    print(f"  Pharmacy → inserted: {pha_inserted}  updated: {pha_updated}")
    print(f"  Skipped (labs): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Total processed: {total}")


if __name__ == "__main__":
    main()
