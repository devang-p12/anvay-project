import os
import requests
import zipfile
import io
import pandas as pd
import json
import time
from datetime import datetime

# Configuration
GDELT_V2_MASTER_LIST_URL = "http://data.gdeltproject.org/gdeltv2/masterfilelist.txt"
DATA_DIR = "data"
STORAGE_FILE = os.path.join(DATA_DIR, "ingested_data.json")

# Filter Settings
TARGET_WORDS = ["India", "Defense", "Defence", "Ministry of Defense", "MoD"]
TARGET_THEMES = ["MILITARY", "GOVT", "ARMED_FORCES"]

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def save_to_json(records):
    """Appends records to a local JSON file."""
    existing_data = []
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            existing_data = []
    
    existing_data.extend(records)
    
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, default=str)
    print(f"Saved {len(records)} records to {STORAGE_FILE}")

def get_latest_gkg_url():
    """Fetches the latest GKG 2.0 file URL from GDELT master list."""
    try:
        response = requests.get(GDELT_V2_MASTER_LIST_URL)
        response.raise_for_status()
        lines = response.text.strip().split("\n")
        # The master list is chronological, so the latest is at the bottom
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            if "gkg.csv.zip" in line:
                parts = line.split(" ")
                return parts[-1]
    except Exception as e:
        print(f"Error fetching GDELT master list: {e}")
    return None

def process_gkg_file(url):
    """Downloads, parses, filters and saves GKG data."""
    print(f"Processing GKG file: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            csv_filename = z.namelist()[0]
            with z.open(csv_filename) as f:
                columns = [
                    "GKGRECORDID", "DATE", "SourceCollectionIdentifier", "SourceCommonName",
                    "DocumentIdentifier", "Counts", "V2Counts", "Themes", "V2Themes",
                    "Locations", "V2Locations", "Persons", "V2Persons", "Organizations",
                    "V2Organizations", "Tone", "EnhancedDates", "EnhancedLocations",
                    "EnhancedThemes", "EnhancedPersons", "EnhancedOrganizations",
                    "GCAM", "SharingImage", "RelatedImages", "SocialImageEmbeds",
                    "SocialVideoEmbeds", "Quotations", "AllNames", "Amounts",
                    "TranslationInfo", "Extras"
                ]
                
                df = pd.read_csv(f, sep="\t", names=columns, encoding="utf-8", on_bad_lines='skip')
                
                mask = df.apply(lambda row: any(
                    word.lower() in str(row["Themes"]).lower() or 
                    word.lower() in str(row["Locations"]).lower() or
                    word.lower() in str(row["Persons"]).lower() or
                    word.lower() in str(row["Organizations"]).lower()
                    for word in TARGET_WORDS
                ), axis=1)
                
                filtered_df = df[mask]
                print(f"Found {len(filtered_df)} relevant records.")
                
                records = []
                for _, row in filtered_df.iterrows():
                    record = {
                        "source": "GDELT",
                        "record_id": row["GKGRECORDID"],
                        "date": row["DATE"],
                        "url": row["DocumentIdentifier"],
                        "source_name": row["SourceCommonName"],
                        "themes": str(row["V2Themes"]).split(";") if pd.notna(row["V2Themes"]) else [],
                        "persons": str(row["V2Persons"]).split(";") if pd.notna(row["V2Persons"]) else [],
                        "organizations": str(row["V2Organizations"]).split(";") if pd.notna(row["V2Organizations"]) else [],
                        "locations": str(row["V2Locations"]).split(";") if pd.notna(row["V2Locations"]) else [],
                        "tone": row["Tone"],
                        "ingestion_timestamp": datetime.utcnow().isoformat()
                    }
                    records.append(record)
                
                if records:
                    save_to_json(records)
                    
    except Exception as e:
        print(f"Error processing GKG file: {e}")

def run_poller():
    last_processed_url = None
    print("Starting GDELT Poller (Local JSON Storage)...")
    while True:
        current_url = get_latest_gkg_url()
        if current_url and current_url != last_processed_url:
            process_gkg_file(current_url)
            last_processed_url = current_url
        else:
            print("No new file found. Sleeping for 5 minutes.")
        
        time.sleep(300)

if __name__ == "__main__":
    run_poller()
