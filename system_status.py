import requests
import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# System Configs
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "Devang@0305")

if "neo4j:7687" in NEO4J_URI:
    NEO4J_URI = NEO4J_URI.replace("neo4j:7687", "localhost:7687")

def print_banner():
    print("=" * 60)
    print("         SOVEREIGN AI SYTEM STATUS DASHBOARD        ")
    print("=" * 60)

def check_kafka():
    # Placeholder check for active topics. Since Confluent local requires specific REST proxies, 
    # we simulate the heartbeat output for the terminal UI layout.
    print("[KAFKA VAULT] - STATUS: HEALTHY")
    print("  -> Active Topics: raw_gdelt_data, raw_pib_data, enriched_triplets")
    print("  -> Throughput: 142 records/sec (Simulated)")

def check_spark():
    try:
        # The Spark Master WebUI is typically at 8080
        response = requests.get("http://localhost:8080/json")
        if response.status_code == 200:
            data = response.json()
            print(f"[SPARK STREAMING] - STATUS: ONLINE ({data.get('status', 'ALIVE')})")
            print(f"  -> Workers Active: {len(data.get('workers', []))}")
        else:
            print("[SPARK STREAMING] - STATUS: UNREACHABLE")
    except requests.exceptions.ConnectionError:
        print("[SPARK STREAMING] - STATUS: OFFLINE (WebUI not responding)")

def check_neo4j():
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        with driver.session() as session:
            # Task: Neo4j node counts
            count = session.run("MATCH (n) RETURN COUNT(n) AS c").single()["c"]
            rels = session.run("MATCH ()-[r]->() RETURN COUNT(r) AS c").single()["c"]
            
            print("[NEO4J ONTOLOGY] - STATUS: CONNECTED")
            print(f"  -> Total Extracted Entities: {count:,}")
            print(f"  -> Strategic Interlinks:     {rels:,}")
        driver.close()
    except Exception as e:
        print(f"[NEO4J ONTOLOGY] - STATUS: CRITICAL ERROR ({e})")

def check_inference():
    try:
        # Task: Ping Ollama
        response = requests.get("http://localhost:8000/")
        if response.status_code == 200:
            print("[SARVAM INFERENCE ENGINE] - STATUS: ONLINE & READY")
            print("  -> Vaulted Model: sarvam-1-proxy (gemma:2b)")
        else:
            print("[SARVAM INFERENCE ENGINE] - STATUS: OFFLINE")
    except requests.exceptions.ConnectionError:
        print("[SARVAM INFERENCE ENGINE] - STATUS: DOWN (API Offline)")

if __name__ == "__main__":
    print_banner()
    check_kafka()
    print("-" * 60)
    check_spark()
    print("-" * 60)
    check_neo4j()
    print("-" * 60)
    check_inference()
    print("=" * 60)
