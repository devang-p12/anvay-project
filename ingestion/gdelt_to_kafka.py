import os
import requests
import zipfile
import io
import pandas as pd
import json
import time
from datetime import datetime
from kafka import KafkaProducer

# Configuration
GDELT_V2_MASTER_LIST_URL = "http://data.gdeltproject.org/gdeltv2/masterfilelist.txt"
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = "raw_strategic_news"

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Filter Settings
TARGET_WORDS = ["India", "Defense", "Defence", "Ministry of Defense", "MoD", "Security", "Strategic", "Economy"]

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
    """Downloads, parses, filters and publishes to Kafka."""
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
                    producer.send(KAFKA_TOPIC, record)
                
                producer.flush()
                print(f"Published {len(filtered_df)} records to Kafka topic: {KAFKA_TOPIC}")
                    
    except Exception as e:
        print(f"Error processing GKG file: {e}")

def run_poller():
    last_processed_url = None
    print("Starting Sovereign GDELT Producer (Kafka Sink)...")
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
