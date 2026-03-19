"""
IMD India Weather Alert Ingestor
Source: India Meteorological Department public data (mausam.imd.gov.in)
No API key required.
Fetches cyclone, flood, and extreme weather warnings.
"""
import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
STORAGE_FILE = os.path.join(DATA_DIR, "ingested_data.json")
os.makedirs(DATA_DIR, exist_ok=True)

# IMD public bulletin endpoints
IMD_CYCLONE_URL  = "https://rsmcnewdelhi.imd.gov.in/report.php?internal_menu=MQ=="  # RSMC cyclone track
IMD_WEATHER_URL  = "https://mausam.imd.gov.in/responsive/all_india_warning_bulletin.php"
IMD_WARNINGS_RSS = "https://mausam.imd.gov.in/rss/warning.xml"

# Indian states/regions to search for
INDIA_REGIONS = [
    "Andhra Pradesh", "Assam", "Bihar", "Gujarat", "Himachal Pradesh",
    "Jammu", "Kashmir", "Karnataka", "Kerala", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal", "Bay of Bengal", "Arabian Sea",
    "Lakshadweep", "Andaman", "North India", "South India"
]

ALERT_KEYWORDS = [
    "cyclone", "flood", "warning", "alert", "heavy rain", "thunderstorm",
    "heatwave", "cold wave", "storm", "disaster", "red alert", "orange alert"
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
        print(f"[IMD] Saved {len(new_records)} new weather alerts.")
    else:
        print("[IMD] No new alerts.")

def scrape_imd_warnings() -> list:
    """Scrape IMD public warning bulletin page."""
    records = []
    try:
        resp = requests.get(IMD_WEATHER_URL, timeout=20,
                            headers={"User-Agent": "Mozilla/5.0 Anvay-AI Research Bot"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        # Find all text blocks and look for alert-related content
        text_blocks = soup.find_all(["p", "li", "td", "div"], string=True)
        today_str = datetime.utcnow().strftime("%Y%m%d")

        for block in text_blocks:
            text = block.get_text(strip=True)
            if len(text) < 20:
                continue

            text_lower = text.lower()
            has_alert = any(kw in text_lower for kw in ALERT_KEYWORDS)
            has_region = any(r.lower() in text_lower for r in INDIA_REGIONS)

            if has_alert and has_region:
                # Determine affected region
                affected = [r for r in INDIA_REGIONS if r.lower() in text_lower]
                alert_type = next((kw.title() for kw in ALERT_KEYWORDS if kw in text_lower), "Weather Alert")

                record_id = f"imd-{today_str}-{hash(text) % 999999}"
                record = {
                    "source": "IMD",
                    "record_id": record_id,
                    "date": today_str,
                    "url": IMD_WEATHER_URL,
                    "title": f"IMD Alert: {alert_type} — {', '.join(affected[:3])}",
                    "themes": ["Weather", "Disaster", alert_type],
                    "persons": [],
                    "organizations": ["India Meteorological Department"],
                    "locations": affected,
                    "tone": "-3",  # Negative tone for disaster alerts
                    "ingestion_timestamp": datetime.utcnow().isoformat(),
                    "alert_text": text[:500],
                    "alert_type": alert_type,
                }
                records.append(record)

    except Exception as e:
        print(f"[IMD] Error scraping warnings: {e}")
    return records

def fetch_imd_rss() -> list:
    """Fetch IMD warning RSS feed."""
    records = []
    try:
        resp = requests.get(IMD_WARNINGS_RSS, timeout=20,
                            headers={"User-Agent": "Mozilla/5.0 Anvay-AI Research Bot"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "xml")
        items = soup.find_all("item")

        for item in items:
            title = item.find("title")
            link = item.find("link")
            desc = item.find("description")
            pub_date = item.find("pubDate")

            if not title:
                continue

            title_text = title.get_text(strip=True)
            desc_text = desc.get_text(strip=True) if desc else ""
            url = link.get_text(strip=True) if link else IMD_WARNINGS_RSS

            # Parse date
            try:
                date_obj = datetime.strptime(pub_date.get_text(strip=True)[:16], "%a, %d %b %Y")
                date_str = date_obj.strftime("%Y%m%d")
            except:
                date_str = datetime.utcnow().strftime("%Y%m%d")

            affected = [r for r in INDIA_REGIONS if r.lower() in (title_text + desc_text).lower()]
            record = {
                "source": "IMD",
                "record_id": f"imd-rss-{hash(title_text) % 999999}",
                "date": date_str,
                "url": url,
                "title": title_text,
                "themes": ["Weather", "Disaster"],
                "persons": [],
                "organizations": ["India Meteorological Department"],
                "locations": affected or ["India"],
                "tone": "-3",
                "ingestion_timestamp": datetime.utcnow().isoformat(),
                "alert_text": desc_text[:500],
            }
            records.append(record)

    except Exception as e:
        print(f"[IMD] RSS fetch failed (may be unavailable): {e}")
    return records

def run_ingestor():
    print("[IMD] Starting India Meteorological Department ingestor...")
    records = []
    records.extend(scrape_imd_warnings())
    records.extend(fetch_imd_rss())
    save_records(records)
    print(f"[IMD] Done. Total weather alerts collected: {len(records)}")

if __name__ == "__main__":
    run_ingestor()
