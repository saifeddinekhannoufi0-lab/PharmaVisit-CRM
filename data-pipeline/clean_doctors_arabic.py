"""
clean_doctors_arabic.py
────────────────────────
Strips Arabic/Tifinagh chars from the doctors table,
skipping updates that would create duplicates.
"""
import os, re
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

ARABIC_RE = re.compile(r'[\u0600-\u06FF\u2D30-\u2D7F\u0750-\u077F]+')
VALID_CITIES = {'Rabat', 'Salé', 'Témara', 'Casablanca', 'Sale', 'Temara'}

def strip_arabic(text):
    if not text: return text
    cleaned = ARABIC_RE.sub(' ', text)
    return re.sub(r'\s+', ' ', cleaned).strip().strip('|·-–—,;:.')

def normalise_city(city):
    if not city: return 'Rabat'
    clean = strip_arabic(city).strip()
    if not clean: return 'Rabat'
    for v in VALID_CITIES:
        if v.lower() in clean.lower(): return v
    return clean

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST','127.0.0.1'),
    port=int(os.getenv('DB_PORT',3306)),
    database=os.getenv('DB_DATABASE'),
    user=os.getenv('DB_USERNAME'),
    password=os.getenv('DB_PASSWORD'),
    charset='utf8mb4',
)
cur = conn.cursor(dictionary=True)

cur.execute('SELECT id, first_name, last_name, specialty, city, address FROM doctors')
rows = cur.fetchall()

cleaned = 0
skipped_dup = 0
deleted_dup = 0

for r in rows:
    new_fn   = strip_arabic(r['first_name'] or '')
    new_ln   = strip_arabic(r['last_name']  or '')
    new_city = normalise_city(r['city']     or '')
    new_addr = strip_arabic(r['address']    or '')

    if (new_fn == r['first_name'] and new_ln == r['last_name'] and
        new_city == r['city']    and new_addr == r['address']):
        continue

    # Check if the cleaned version would collide with an existing record
    cur.execute("""
        SELECT id FROM doctors
        WHERE last_name = %s AND first_name = %s AND city = %s AND specialty = %s
          AND id != %s
        LIMIT 1
    """, (new_ln, new_fn, new_city, r['specialty'], r['id']))
    collision = cur.fetchone()

    if collision:
        # This record becomes a duplicate after cleaning → delete it
        cur.execute('DELETE FROM doctors WHERE id = %s', (r['id'],))
        deleted_dup += 1
        continue

    try:
        cur.execute(
            'UPDATE doctors SET first_name=%s, last_name=%s, city=%s, address=%s WHERE id=%s',
            (new_fn, new_ln, new_city, new_addr, r['id'])
        )
        cleaned += 1
    except mysql.connector.errors.IntegrityError:
        cur.execute('DELETE FROM doctors WHERE id = %s', (r['id'],))
        deleted_dup += 1

conn.commit()

# Final counts
cur.execute('SELECT COUNT(*) AS n FROM doctors'); doc = cur.fetchone()['n']
cur.execute('SELECT specialty, COUNT(*) AS n FROM doctors GROUP BY specialty ORDER BY n DESC')
specs = cur.fetchall()
conn.close()

print(f'Doctors: updated={cleaned}  deleted_dupes={deleted_dup}')
print(f'Final doctor count: {doc}')
print('Specialties:')
for s in specs:
    print(f'  {s["specialty"]}: {s["n"]}')
