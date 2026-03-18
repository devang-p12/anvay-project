import os
import json

STORAGE_FILE = "data/ingested_data.json"

def peek_data():
    if not os.path.exists(STORAGE_FILE):
        print(f"No data file found at {STORAGE_FILE}.")
        print("Run the pollers first:\nUpdate: python ingestion/gdelt_poller.py")
        return

    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        count = len(data)
        print(f"Total documents ingested: {count}")
        
        if count > 0:
            print("\nRecent 3 records:")
            # Sort by timestamp (assuming ISO format strings work for simple sort here)
            sorted_data = sorted(data, key=lambda x: x.get("ingestion_timestamp", ""), reverse=True)
            print(json.dumps(sorted_data[:3], indent=2))
        else:
            print("\nData file is empty.")
            
    except Exception as e:
        print(f"Error reading data file: {e}")

if __name__ == "__main__":
    peek_data()
