"""
migrate_pharmacies.py
─────────────────────
Moves records with specialty='Pharmacie' (and 'Laboratoire') from the
doctors table into the pharmacies table, then deletes them from doctors.

Run once:
    python data-pipeline/migrate_pharmacies.py
"""
import os, sys
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime

load_dotenv(Path(__file__).parent.parent / '.env')

conn = mysql.connector.connect(
    host     = os.getenv('DB_HOST', '127.0.0.1'),
    port     = int(os.getenv('DB_PORT', 3306)),
    database = os.getenv('DB_DATABASE'),
    user     = os.getenv('DB_USERNAME'),
    password = os.getenv('DB_PASSWORD'),
    charset  = 'utf8mb4',
)
cur = conn.cursor(dictionary=True)

# ── Step 1: fetch all pharmacies sitting in doctors table ─────────────────────
cur.execute("""
    SELECT id, territory_id, first_name, last_name, address, city,
           postal_code, region, phone, lat, lng, specialty
    FROM doctors
    WHERE specialty IN ('Pharmacie', 'Laboratoire')
""")
rows = cur.fetchall()
print(f"[migrate] Found {len(rows)} pharmacy/lab records in doctors table")

# ── Step 2: insert into pharmacies (skip duplicates by name+city) ─────────────
inserted = 0
skipped  = 0
lab_ids  = []   # labs: just delete, don't move to pharmacies

for r in rows:
    # Reconstruct a name: "first_name last_name"  e.g. "Pharmacie Al Farabi"
    name = f"{r['first_name']} {r['last_name']}".strip()

    if r['specialty'] == 'Laboratoire':
        # Laboratories don't belong anywhere — just flag for deletion
        lab_ids.append(r['id'])
        continue

    # Check if already exists in pharmacies (by name + city)
    cur.execute(
        "SELECT id FROM pharmacies WHERE name = %s AND city = %s LIMIT 1",
        (name, r['city'])
    )
    if cur.fetchone():
        skipped += 1
        continue

    cur.execute("""
        INSERT INTO pharmacies
            (territory_id, name, address, city, postal_code, region,
             phone, lat, lng, geocoded_at, is_active, created_at, updated_at)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
    """, (
        r['territory_id'],
        name,
        r['address']  or '',
        r['city']     or 'Rabat',
        r['postal_code'] or '',
        r['region']   or 'Rabat-Salé-Kénitra',
        r['phone']    or '',
        r['lat'],
        r['lng'],
        datetime.now(),
        datetime.now(),
        datetime.now(),
    ))
    inserted += 1

conn.commit()
print(f"[migrate] Pharmacies inserted: {inserted}  |  Skipped (already exist): {skipped}")
print(f"[migrate] Labs flagged for deletion: {len(lab_ids)}")

# ── Step 3: delete all pharmacy+lab records from doctors table ────────────────
cur.execute("""
    DELETE FROM doctors
    WHERE specialty IN ('Pharmacie', 'Laboratoire')
""")
deleted = cur.rowcount
conn.commit()
print(f"[migrate] Deleted {deleted} records from doctors table")

# ── Step 4: final counts ──────────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) AS n FROM doctors")
doc_count = cur.fetchone()['n']

cur.execute("SELECT COUNT(*) AS n FROM pharmacies")
pha_count = cur.fetchone()['n']

cur.execute("SELECT specialty, COUNT(*) AS n FROM doctors GROUP BY specialty ORDER BY n DESC")
specs = cur.fetchall()

print(f"\n[RESULT]")
print(f"  Doctors table  : {doc_count} records")
print(f"  Pharmacies table: {pha_count} records")
print(f"\n  Doctor specialties:")
for s in specs:
    # safe encode for Windows console
    sp = s['specialty'].encode('ascii', 'replace').decode()
    print(f"    {sp}: {s['n']}")

conn.close()
print("\n[migrate] Done.")
