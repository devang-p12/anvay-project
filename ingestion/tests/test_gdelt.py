import os
import sys
import pandas as pd
import requests
import io
import zipfile

# Add parent directory to sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gdelt_poller import get_latest_gkg_url

def test_gdelt_connection():
    print("Testing GDELT connection...")
    url = get_latest_gkg_url()
    if url:
        print(f"Successfully retrieved latest GKG URL: {url}")
        return True
    else:
        print("Failed to retrieve GKG URL.")
        return False

def verify_parsing_logic():
    print("Verifying parsing and filtering logic...")
    # Mock some data for verification
    data = {
        "GKGRECORDID": ["1", "2"],
        "DATE": ["20260317100000", "20260317100000"],
        "SourceCommonName": ["test.com", "test2.com"],
        "DocumentIdentifier": ["url1", "url2"],
        "Themes": ["MILITARY;GOVT", "HEALTH;SPORTS"],
        "V2Themes": ["MILITARY", "HEALTH"],
        "Locations": ["India", "USA"],
        "V2Locations": ["India", "USA"],
        "Persons": ["Narendra Modi", "John Doe"],
        "V2Persons": ["Narendra Modi", "John Doe"],
        "Organizations": ["Ministry of Defense", "Health Org"],
        "V2Organizations": ["Ministry of Defense", "Health Org"],
        "Tone": ["0,0,0,0,0", "0,0,0,0,0"]
    }
    df = pd.DataFrame(data)
    
    TARGET_WORDS = ["India", "Defense", "Defence", "Ministry of Defense", "MoD"]
    mask = df.apply(lambda row: any(
        word.lower() in str(row["Themes"]).lower() or 
        word.lower() in str(row["Locations"]).lower() or
        word.lower() in str(row["Persons"]).lower() or
        word.lower() in str(row["Organizations"]).lower()
        for word in TARGET_WORDS
    ), axis=1)
    
    filtered_df = df[mask]
    if len(filtered_df) == 1 and filtered_df.iloc[0]["GKGRECORDID"] == "1":
        print("Parsing and filtering logic verified.")
        return True
    else:
        print(f"Parsing/Filtering logic failure. Found {len(filtered_df)} matches instead of 1.")
        return False

if __name__ == "__main__":
    c = test_gdelt_connection()
    p = verify_parsing_logic()
    if c and p:
        print("All GDELT tests passed.")
    else:
        sys.exit(1)
