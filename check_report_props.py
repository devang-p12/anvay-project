from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "Devang@0305")
if "neo4j:7687" in NEO4J_URI:
    NEO4J_URI = NEO4J_URI.replace("neo4j:7687", "localhost:7687")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

print("=== StrategicReport node properties ===")
with driver.session() as s:
    res = s.run("MATCH (r:StrategicReport) RETURN r LIMIT 3")
    for record in res:
        node = record["r"]
        print("\n--- Report ---")
        for k, v in node.items():
            val = str(v)[:200]  # truncate long values
            print(f"  {k}: {val}")

print("\n=== Entity node properties sample ===")
with driver.session() as s:
    res = s.run("MATCH (n) WHERE NOT n:StrategicReport AND NOT n:Theme RETURN labels(n)[0] as label, n LIMIT 3")
    for record in res:
        node = record["n"]
        label = record["label"]
        print(f"\n--- {label} ---")
        for k, v in node.items():
            val = str(v)[:200]
            print(f"  {k}: {val}")

driver.close()
