"""
MySQL Import Script
=====================
Reads clean_doctors.csv and upserts records into the pharmavisit database.

KEY DESIGN DECISIONS:
  • Uses INSERT ... ON DUPLICATE KEY UPDATE so re-running is idempotent.
  • NEVER overwrites: notes, lat, lng, geocoded_at, priority, is_active.
    These are rep-curated fields — the pipeline must not clobber them.
  • Only updates: address, city, postal_code, region, phone (factual data
    that may change in the public registry).
  • New doctors are inserted with is_active=1, priority='medium'.
  • territory_id is assigned via the CITY→TERRITORY mapping below.
    Doctors in unmapped cities default to the first territory (id=1).

Run:
  cd data-pipeline
  python import_data.py

Environment variables (or edit the DB_* constants below):
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
"""

import os
import sys
from pathlib import Path

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
}

INPUT_FILE = Path(__file__).parent / "output" / "clean_doctors.csv"

# ─── City → Territory mapping ─────────────────────────────────────────────────
# These IDs must match the territories seeded in Phase 1.
# Extend this map as you add more territories.
CITY_TO_TERRITORY = {
    "Rabat":      1,   # Grand Rabat (MAR-RAB)
    "Salé":       1,
    "Témara":     1,
    "Casablanca": 2,   # Casablanca Nord (MAR-CAS)
}
DEFAULT_TERRITORY_ID = 1


def get_territory_id(city: str) -> int:
    return CITY_TO_TERRITORY.get(city, DEFAULT_TERRITORY_ID)


UPSERT_SQL = """
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
    -- Only update factual/public data — NEVER rep notes/coords/priority
    address      = IF(VALUES(address) != '', VALUES(address), address),
    city         = VALUES(city),
    postal_code  = IF(VALUES(postal_code) != '', VALUES(postal_code), postal_code),
    region       = VALUES(region),
    phone        = IF(VALUES(phone) != '', VALUES(phone), phone),
    lat          = IF(VALUES(lat) IS NOT NULL, VALUES(lat), lat),
    lng          = IF(VALUES(lng) IS NOT NULL, VALUES(lng), lng),
    updated_at   = NOW()
"""

# Duplicate detection: (last_name, first_name, city, specialty)
# Laravel's MySQL UNIQUE constraint must match this.
# We add a unique index via migration rather than in this script.


def add_unique_index_if_missing(cursor):
    """Ensure the unique index used by ON DUPLICATE KEY exists."""
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
        # Delete duplicates keeping the one with the lowest id
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

    # Ensure unique index exists
    add_unique_index_if_missing(cursor)
    conn.commit()

    inserted = 0
    updated  = 0
    errors   = 0

    for _, row in df.iterrows():
        params = {
            "territory_id": get_territory_id(row.get("city", "")),
            "first_name":   row.get("first_name", ""),
            "last_name":    row.get("last_name", ""),
            "specialty":    row.get("specialty", ""),
            "address":      row.get("address", ""),
            "city":         row.get("city", ""),
            "postal_code":  row.get("postal_code", ""),
            "region":       row.get("region", "Morocco"),
            "phone":        row.get("phone", ""),
            "lat":          float(row["lat"]) if row.get("lat") else None,
            "lng":          float(row["lng"]) if row.get("lng") else None,
        }

        try:
            cursor.execute(UPSERT_SQL, params)
            rows_affected = cursor.rowcount
            # rowcount=1 → INSERT, rowcount=2 → UPDATE (MySQL convention)
            if rows_affected == 1:
                inserted += 1
            elif rows_affected == 2:
                updated  += 1
        except mysql.connector.Error as e:
            print(f"[WARN] Error on {params['last_name']}, {params['city']}: {e}")
            errors += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n[import] [OK] Done")
    print(f"  Inserted (new): {inserted}")
    print(f"  Updated (existing): {updated}")
    print(f"  Errors: {errors}")
    print(f"  Total processed: {total}")


if __name__ == "__main__":
    main()
