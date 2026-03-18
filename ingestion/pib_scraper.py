import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime

# Configuration
PIB_HOME_URL = "https://pib.gov.in/indexd.aspx"
PIB_RELEASES_URL = "https://pib.gov.in/allRel.aspx"
DATA_DIR = "data"
STORAGE_FILE = os.path.join(DATA_DIR, "ingested_data.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def save_to_json(record):
    """Appends a single record to the local JSON file."""
    existing_data = []
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            existing_data = []
    
    # Check for duplicates by URL
    if any(r.get("url") == record["url"] for r in existing_data):
        return

    existing_data.append(record)
    
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, default=str)
    print(f"Saved PIB record: {record['title']}")

def translate_hindi_to_english(text):
    # Placeholder for Bhashini API call logic
    return text

def scrape_pib_releases():
    """Scrapes latest PIB releases from the portal."""
    print("Scraping PIB releases...")
    try:
        response = requests.get(PIB_RELEASES_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        release_links = soup.find_all('a', href=True)
        
        for link in release_links:
            href = link['href']
            if 'PressReleseDetail.aspx' in href:
                full_url = "https://pib.gov.in/" + href
                process_pib_release(full_url)
                
    except Exception as e:
        print(f"Error scraping PIB: {e}")

def process_pib_release(url):
    """Processes an individual PIB release."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = soup.find('h2').text.strip() if soup.find('h2') else "No Title"
        content_div = soup.find('div', class_='ReleaseText')
        content = content_div.text.strip() if content_div else ""
        
        is_hindi = any('\u0900' <= char <= '\u097F' for char in content)
        
        processed_content = content
        if is_hindi:
            processed_content = translate_hindi_to_english(content)
            
        record = {
            "source": "PIB",
            "url": url,
            "title": title,
            "original_content": content,
            "processed_content": processed_content,
            "is_translated": is_hindi,
            "language": "Hindi" if is_hindi else "English",
            "ingestion_timestamp": datetime.utcnow().isoformat()
        }
        
        save_to_json(record)
        
    except Exception as e:
        print(f"Error processing PIB release {url}: {e}")

def run_scraper():
    print("Starting PIB Scraper (Local JSON Storage)...")
    while True:
        scrape_pib_releases()
        print("PIB scrape cycle complete. Sleeping for 1 hour.")
        time.sleep(3600)

if __name__ == "__main__":
    run_scraper()
