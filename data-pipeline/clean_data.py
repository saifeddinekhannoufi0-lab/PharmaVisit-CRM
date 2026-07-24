"""
Pandas Data Cleaner
=====================
Reads raw_doctors.csv from the Scrapy spider output, cleans and deduplicates
it, and writes clean_doctors.csv ready for import_data.py.

Run:
  cd data-pipeline
  python clean_data.py

Input:  output/raw_doctors.csv
Output: output/clean_doctors.csv
"""

import re
import sys
from pathlib import Path

import pandas as pd


INPUT_FILE  = Path(__file__).parent / "output" / "raw_doctors.csv"
OUTPUT_FILE = Path(__file__).parent / "output" / "clean_doctors.csv"


# ─── City / region normalization maps ─────────────────────────────────────────

CITY_ALIASES = {
    "casa":       "Casablanca",
    "casablanca": "Casablanca",
    "rabat":      "Rabat",
    "sale":       "Salé",
    "salé":       "Salé",
    "temara":     "Témara",
    "témara":     "Témara",
    "fes":        "Fès",
    "fès":        "Fès",
    "marrakech":  "Marrakech",
    "tanger":     "Tanger",
    "agadir":     "Agadir",
    "meknes":     "Meknès",
    "meknès":     "Meknès",
    "oujda":      "Oujda",
}

REGION_MAP = {
    "Rabat":      "Rabat-Salé-Kénitra",
    "Salé":       "Rabat-Salé-Kénitra",
    "Témara":     "Rabat-Salé-Kénitra",
    "Casablanca": "Casablanca-Settat",
    "Fès":        "Fès-Meknès",
    "Meknès":     "Fès-Meknès",
    "Marrakech":  "Marrakech-Safi",
    "Tanger":     "Tanger-Tétouan-Al Hoceïma",
    "Agadir":     "Souss-Massa",
    "Oujda":      "Oriental",
}


def normalize_phone(phone: str) -> str:
    """Normalize Moroccan phone numbers to +212XXXXXXXXX format."""
    if pd.isna(phone) or not str(phone).strip():
        return ""
    digits = re.sub(r"[^\d+]", "", str(phone))
    if digits.startswith("00212"):
        digits = "+" + digits[2:]
    elif digits.startswith("212"):
        digits = "+" + digits
    elif digits.startswith("0") and len(digits) == 10:
        digits = "+212" + digits[1:]
    return digits if digits.startswith("+212") else digits


def normalize_city(city: str) -> str:
    return CITY_ALIASES.get(city.lower().strip(), city.strip().title())


def normalize_name_part(name: str) -> str:
    """Title-case, trim, collapse spaces."""
    return " ".join(str(name).strip().split()).title()


def normalize_specialty(spec: str) -> str:
    return " ".join(str(spec).strip().split()).title()


def clean(df: pd.DataFrame) -> pd.DataFrame:
    print(f"  → Raw rows: {len(df)}")

    # ── Column normalization ──────────────────────────────────────────────────
    df["first_name"]  = df["first_name"].fillna("").apply(normalize_name_part)
    df["last_name"]   = df["last_name"].fillna("").apply(normalize_name_part)
    df["specialty"]   = df["specialty"].fillna("").apply(normalize_specialty)
    df["address"]     = df["address"].fillna("").str.strip()
    df["city"]        = df["city"].fillna("").apply(normalize_city)
    df["postal_code"] = df["postal_code"].fillna("").str.strip()
    df["phone"]       = df["phone"].fillna("").apply(normalize_phone)
    df["source"]      = df.get("source", pd.Series("unknown", index=df.index)).fillna("unknown")

    # ── Add region ────────────────────────────────────────────────────────────
    df["region"] = df["city"].map(REGION_MAP).fillna("Morocco")

    # ── Drop rows with missing required fields ────────────────────────────────
    before = len(df)
    df = df[df["last_name"].str.len() > 0]
    df = df[df["address"].str.len() > 0]
    print(f"  → After dropping missing required fields: {len(df)} (removed {before - len(df)})")

    # ── Deduplicate: same name + city + specialty ─────────────────────────────
    # Keep the row with the most complete data (non-null count)
    df["_completeness"] = df.notna().sum(axis=1)
    df = df.sort_values("_completeness", ascending=False)
    before = len(df)
    df = df.drop_duplicates(subset=["last_name", "first_name", "city", "specialty"], keep="first")
    df = df.drop(columns=["_completeness"])
    print(f"  → After deduplication: {len(df)} (removed {before - len(df)} dupes)")

    # ── Additional dedupe: same address + last_name (different first name captured) ──
    before = len(df)
    df = df.drop_duplicates(subset=["last_name", "address"], keep="first")
    print(f"  → After address-level dedupe: {len(df)} (removed {before - len(df)})")

    # ── Reset index ───────────────────────────────────────────────────────────
    df = df.reset_index(drop=True)
    df.insert(0, "row_id", range(1, len(df) + 1))

    return df


def main():
    if not INPUT_FILE.exists():
        print(f"[ERROR] Input file not found: {INPUT_FILE}")
        print("Run the Scrapy spider first:")
        print("  scrapy crawl sample_local -o output/raw_doctors.csv")
        sys.exit(1)

    print(f"[clean_data] Reading: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, dtype=str)

    print("[clean_data] Cleaning…")
    df_clean = clean(df)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print(f"[clean_data] ✅ Wrote {len(df_clean)} clean records to: {OUTPUT_FILE}")
    print("\nSample output:")
    print(df_clean[["first_name", "last_name", "specialty", "city", "address"]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
