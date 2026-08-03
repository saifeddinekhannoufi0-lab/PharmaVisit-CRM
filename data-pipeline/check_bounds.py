import mysql.connector, os
from dotenv import load_dotenv
load_dotenv()
conn = mysql.connector.connect(
    host=os.getenv('DB_HOST','127.0.0.1'),
    port=int(os.getenv('DB_PORT',3306)),
    database=os.getenv('DB_DATABASE'),
    user=os.getenv('DB_USERNAME'),
    password=os.getenv('DB_PASSWORD')
)
cur = conn.cursor(dictionary=True)

# Rabat-Sale-Temara Bounding Box
# Lat: 33.80 to 34.15
# Lng: -7.10 to -6.65

def check_bounds(table, name_col):
    cur.execute(f"SELECT id, {name_col} as name, city, lat, lng FROM {table}")
    rows = cur.fetchall()
    out_of_bounds = []
    for r in rows:
        lat = float(r['lat']) if r['lat'] else 0
        lng = float(r['lng']) if r['lng'] else 0
        if not (33.80 <= lat <= 34.15 and -7.10 <= lng <= -6.65):
            out_of_bounds.append(r)
    return len(rows), out_of_bounds

doc_total, doc_out = check_bounds('doctors', 'last_name')
pha_total, pha_out = check_bounds('pharmacies', 'name')

print(f"Checked {doc_total} doctors and {pha_total} pharmacies.")

if not doc_out and not pha_out:
    print("SUCCESS: Every single location is strictly inside the Rabat/Sale/Temara region!")
else:
    print(f"Found {len(doc_out)} doctors and {len(pha_out)} pharmacies outside the region.")
    for o in doc_out:
        print(f"Doctor: {o['name']} in {o['city']} (Lat: {o['lat']}, Lng: {o['lng']})")
    for o in pha_out:
        print(f"Pharmacy: {o['name']} in {o['city']} (Lat: {o['lat']}, Lng: {o['lng']})")

conn.close()
