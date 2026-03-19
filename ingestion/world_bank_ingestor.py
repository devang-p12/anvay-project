"""
World Bank Economic Ingestor
Free API, no key required: https://api.worldbank.org/v2
Fetches key economic indicators for India and strategic partner/rival nations.
"""
import requests
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
STORAGE_FILE = os.path.join(DATA_DIR, "ingested_data.json")
os.makedirs(DATA_DIR, exist_ok=True)

WB_API = "https://api.worldbank.org/v2"

# Focus countries for strategic analysis
TARGET_COUNTRIES = {
    "IN": "India", "CN": "China", "PK": "Pakistan",
    "US": "United States", "RU": "Russia", "AF": "Afghanistan"
}

# Key economic indicators: (code, human-readable name)
INDICATORS = [
    ("MS.MIL.XPND.GD.ZS", "Military Expenditure % GDP"),
    ("NY.GDP.MKTP.CD",     "GDP (Current USD)"),
    ("SL.UEM.TOTL.ZS",     "Unemployment Rate %"),
    ("GC.DOD.TOTL.GD.ZS",  "Government Debt % GDP"),
    ("BX.KLT.DINV.CD.WD",  "Foreign Direct Investment"),
    ("SP.POP.TOTL",         "Total Population"),
]

def save_records(records):
    existing = []
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except:
            pass
    existing_ids = {r.get("record_id") for r in existing}
    new_records = [r for r in records if r.get("record_id") not in existing_ids]
    if new_records:
        existing.extend(new_records)
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, default=str)
        print(f"[WorldBank] Saved {len(new_records)} new economic records.")
    else:
        print("[WorldBank] No new records.")

def fetch_indicator(country_code: str, country_name: str, indicator_code: str, indicator_name: str) -> list:
    """Fetch the latest 5 years of a World Bank indicator for a country."""
    url = f"{WB_API}/country/{country_code}/indicator/{indicator_code}"
    params = {"format": "json", "mrv": 5, "per_page": 5}
    records = []
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if len(data) < 2 or not data[1]:
            return []
        for entry in data[1]:
            value = entry.get("value")
            if value is None:
                continue
            year = entry.get("date", "Unknown")
            record_id = f"wb-{country_code}-{indicator_code}-{year}"
            record = {
                "source": "WorldBank",
                "record_id": record_id,
                "date": f"{year}0101",  # Normalize to YYYYMMDD
                "url": f"https://data.worldbank.org/indicator/{indicator_code}?locations={country_code}",
                "title": f"{indicator_name} — {country_name} ({year}): {value:.2f}",
                "themes": ["Economics", indicator_name],
                "persons": [],
                "organizations": ["World Bank"],
                "locations": [country_name],
                "tone": "0",
                "ingestion_timestamp": datetime.utcnow().isoformat(),
                # Extended economic fields
                "indicator_code": indicator_code,
                "indicator_name": indicator_name,
                "value": value,
                "year": year,
                "country": country_name,
            }
            records.append(record)
    except Exception as e:
        print(f"[WorldBank] Error fetching {indicator_code} for {country_code}: {e}")
    return records

def run_ingestor():
    print("[WorldBank] Starting World Bank Economic ingestor...")
    all_records = []
    for code, name in TARGET_COUNTRIES.items():
        for indicator_code, indicator_name in INDICATORS:
            records = fetch_indicator(code, name, indicator_code, indicator_name)
            print(f"[WorldBank] {name} | {indicator_name}: {len(records)} years")
            all_records.extend(records)

    save_records(all_records)
    print(f"[WorldBank] Done. Total economic records: {len(all_records)}")

if __name__ == "__main__":
    run_ingestor()
