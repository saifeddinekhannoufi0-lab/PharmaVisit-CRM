"""
clean_pharmacies.py
───────────────────
Cleans pharmacies table:
  1. Strips Arabic / Tifinagh characters from name, city, address
  2. Removes Laboratoire entries (not visit targets)
  3. Normalises city values to proper French names
  4. Deduplicates by name+city
"""
import os, re, sys
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

# Arabic unicode block: 0600-06FF
# Tifinagh:             2D30-2D7F
# Also strip ® ™ and weird box chars
ARABIC_RE = re.compile(r'[\u0600-\u06FF\u2D30-\u2D7F\u0750-\u077F]+')

# City normalisation — map Arabic/mixed city names to clean French names
CITY_MAP = {
    'ربﺎﻃ': 'Rabat', 'الرباط': 'Rabat',
    'سلا': 'Salé',  'سلى': 'Salé',
    'تمارة': 'Témara',
    '': 'Rabat',  # empty → default
}
VALID_CITIES = {'Rabat', 'Salé', 'Témara', 'Casablanca'}

def strip_arabic(text: str) -> str:
    """Remove Arabic/Tifinagh blocks, then collapse whitespace."""
    if not text:
        return text
    cleaned = ARABIC_RE.sub(' ', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Remove leading/trailing punctuation
    cleaned = cleaned.strip('|·-–—,;:.')
    return cleaned.strip()

def normalise_city(city: str) -> str:
    if not city:
        return 'Rabat'
    # Strip Arabic chars first
    clean = strip_arabic(city).strip()
    # Map known Arabic city names
    if not clean or clean in ('', '-'):
        return 'Rabat'
    # If it already looks French, keep it
    for valid in VALID_CITIES:
        if valid.lower() in clean.lower():
            return valid
    return clean if clean else 'Rabat'


conn = mysql.connector.connect(
    host=os.getenv('DB_HOST','127.0.0.1'),
    port=int(os.getenv('DB_PORT',3306)),
    database=os.getenv('DB_DATABASE'),
    user=os.getenv('DB_USERNAME'),
    password=os.getenv('DB_PASSWORD'),
    charset='utf8mb4',
)
cur = conn.cursor(dictionary=True)

# ── Step 1: Remove Laboratoires from pharmacies ───────────────────────────────
cur.execute("DELETE FROM pharmacies WHERE name LIKE '%Laboratoire%' OR name LIKE '%Labo%'")
deleted_labs = cur.rowcount
conn.commit()
print(f'Deleted {deleted_labs} lab entries from pharmacies')

# ── Step 2: Fetch all pharmacies and clean fields ─────────────────────────────
cur.execute('SELECT id, name, city, address FROM pharmacies')
rows = cur.fetchall()
print(f'Processing {len(rows)} pharmacies...')

cleaned = 0
for r in rows:
    new_name    = strip_arabic(r['name']    or '')
    new_city    = normalise_city(r['city']  or '')
    new_address = strip_arabic(r['address'] or '')

    # Skip if nothing changed
    if new_name == r['name'] and new_city == r['city'] and new_address == r['address']:
        continue

    cur.execute(
        'UPDATE pharmacies SET name=%s, city=%s, address=%s WHERE id=%s',
        (new_name, new_city, new_address, r['id'])
    )
    cleaned += 1

conn.commit()
print(f'Cleaned {cleaned} pharmacy records')

# ── Step 3: Remove duplicates by name+city ────────────────────────────────────
cur.execute("""
    DELETE p1 FROM pharmacies p1
    INNER JOIN pharmacies p2
    WHERE p1.id > p2.id
      AND LOWER(TRIM(p1.name))  = LOWER(TRIM(p2.name))
      AND LOWER(TRIM(p1.city))  = LOWER(TRIM(p2.city))
""")
deduped = cur.rowcount
conn.commit()
print(f'Removed {deduped} duplicate pharmacies')

# ── Step 4: Delete pharmacies with empty/garbled names ───────────────────────
cur.execute("DELETE FROM pharmacies WHERE TRIM(name) = '' OR name IS NULL OR LENGTH(name) < 3")
bad_names = cur.rowcount
conn.commit()
print(f'Removed {bad_names} pharmacies with invalid names')

# ── Step 5: Also clean the doctors table city/name fields ────────────────────
cur.execute('SELECT id, first_name, last_name, specialty, city, address FROM doctors')
doc_rows = cur.fetchall()
doc_cleaned = 0
for r in doc_rows:
    new_fn   = strip_arabic(r['first_name']  or '')
    new_ln   = strip_arabic(r['last_name']   or '')
    new_city = normalise_city(r['city']       or '')
    new_addr = strip_arabic(r['address']     or '')
    if new_fn==r['first_name'] and new_ln==r['last_name'] and new_city==r['city'] and new_addr==r['address']:
        continue
    cur.execute(
        'UPDATE doctors SET first_name=%s, last_name=%s, city=%s, address=%s WHERE id=%s',
        (new_fn, new_ln, new_city, new_addr, r['id'])
    )
    doc_cleaned += 1

conn.commit()
print(f'Cleaned {doc_cleaned} doctor records')

# ── Final counts ──────────────────────────────────────────────────────────────
cur.execute('SELECT COUNT(*) AS n FROM pharmacies'); pha = cur.fetchone()['n']
cur.execute('SELECT COUNT(*) AS n FROM doctors');    doc = cur.fetchone()['n']
cur.execute('SELECT city, COUNT(*) AS n FROM pharmacies GROUP BY city ORDER BY n DESC')
cities = cur.fetchall()
conn.close()

print(f'\nFinal: {doc} doctors | {pha} pharmacies')
print('Pharmacy cities:')
for c in cities:
    try:
        print(f'  {c["city"]}: {c["n"]}')
    except:
        print(f'  [unreadable]: {c["n"]}')
