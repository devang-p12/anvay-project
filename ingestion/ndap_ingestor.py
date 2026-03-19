"""
NDAP (National Data and Analytics Platform) Ingestor
Source: NITI Aayog Open Data Portal - api.ndap.gov.in
No API key required for public datasets.
Fetches district-level economic and social indicators for India.
"""
import requests
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
STORAGE_FILE = os.path.join(DATA_DIR, "ingested_data.json")
os.makedirs(DATA_DIR, exist_ok=True)

NDAP_BASE = "https://ndap.niti.gov.in/api"
NDAP_SEARCH = f"{NDAP_BASE}/3/action/datastore_search"

# Key NDAP dataset resource IDs (publicly accessible)
# These cover economic and social development indicators
NDAP_DATASETS = [
    {
        "resource_id": "ff9985f2-2c76-4f9c-98d7-1921a9dc6f8b",
        "name": "State-wise GDP",
        "themes": ["Economics", "GDP"],
    },
    {
        "resource_id": "7ad3f11e-44f0-4e28-8b49-48c4cbbdd7ee",
        "name": "District Unemployment Rate",
        "themes": ["Economics", "Unemployment"],
    },
    {
        "resource_id": "5c1a1c36-c8a6-4e19-b2f3-a5d3c4dff9f2",
        "name": "State-wise Defense Budget Allocations",
        "themes": ["Defense", "Economics", "Budget"],
    },
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
        print(f"[NDAP] Saved {len(new_records)} new records.")
    else:
        print("[NDAP] No new records found.")

def fetch_ndap_dataset(dataset: dict, limit: int = 50) -> list:
    """Fetch records from an NDAP public dataset."""
    records = []
    resource_id = dataset["resource_id"]
    dataset_name = dataset["name"]
    themes = dataset["themes"]

    try:
        params = {"resource_id": resource_id, "limit": limit}
        resp = requests.get(NDAP_SEARCH, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("success"):
            print(f"[NDAP] Dataset {dataset_name} returned no data (may be unavailable).")
            return []

        rows = data.get("result", {}).get("records", [])
        print(f"[NDAP] {dataset_name}: {len(rows)} rows fetched.")

        for row in rows:
            # Try to extract state/district from common NDAP column names
            location = (row.get("State") or row.get("state") or
                        row.get("District") or row.get("district") or "India")
            year = str(row.get("Year") or row.get("year") or
                       row.get("Financial_Year") or datetime.utcnow().year)
            value_key = next((k for k in row if k not in ["State", "District", "Year",
                                                            "state", "district", "year",
                                                            "_id", "Financial_Year"]), None)
            value = row.get(value_key, "N/A") if value_key else "N/A"
            record_id = f"ndap-{resource_id[:8]}-{row.get('_id', hash(str(row)) % 999999)}"

            record = {
                "source": "NDAP",
                "record_id": record_id,
                "date": f"{year[:4]}0101",
                "url": f"https://ndap.niti.gov.in/dataset/{resource_id}",
                "title": f"{dataset_name} — {location} ({year}): {value}",
                "themes": themes,
                "persons": [],
                "organizations": ["NITI Aayog"],
                "locations": [location, "India"],
                "tone": "0",
                "ingestion_timestamp": datetime.utcnow().isoformat(),
                # Extended economic fields
                "indicator_name": dataset_name,
                "value": value,
                "year": year,
                "raw_row": row,
            }
            records.append(record)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"[NDAP] Dataset '{dataset_name}' not found (resource ID may have changed).")
        else:
            print(f"[NDAP] HTTP Error for {dataset_name}: {e}")
    except Exception as e:
        print(f"[NDAP] Error fetching {dataset_name}: {e}")

    return records

def run_ingestor():
    print("[NDAP] Starting NITI Aayog NDAP ingestor...")
    all_records = []
    for dataset in NDAP_DATASETS:
        print(f"[NDAP] Fetching: {dataset['name']}...")
        records = fetch_ndap_dataset(dataset)
        all_records.extend(records)

    save_records(all_records)
    print(f"[NDAP] Done. Total records collected: {len(all_records)}")

if __name__ == "__main__":
    run_ingestor()
