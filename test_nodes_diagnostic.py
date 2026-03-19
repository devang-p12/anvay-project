from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD")

if not NEO4J_USER or not NEO4J_PASS:
    raise RuntimeError(
        "NEO4J_USERNAME and NEO4J_PASSWORD must be set (e.g. via a .env file) "
        "to run diagnostics."
    )

if "neo4j" in NEO4J_URI and "localhost" not in NEO4J_URI:
    NEO4J_URI = "bolt://localhost:7687"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
with driver.session() as s:
    print("--- NODE COUNT BY LABEL ---")
    res = s.run("MATCH (n) RETURN labels(n) as labels, count(*) as count ORDER BY count DESC")
    for r in res:
        print(f"Labels: {r['labels']} | Count: {r['count']}")
    
    print("\n--- SAMPLE KABUL SEARCH ---")
    res = s.run("MATCH (n) WHERE toLower(coalesce(n.name, n.title, '')) CONTAINS 'kabul' RETURN n.name, n.title LIMIT 5")
    for r in res:
        print(r)

driver.close()
