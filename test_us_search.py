from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "Devang@0305"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
with driver.session() as s:
    print("\n--- DETAILED SEARCH: UNITED STATES ---")
    res = s.run("MATCH (n:Location) WHERE toLower(n.name) CONTAINS 'united states' RETURN n.name LIMIT 5")
    recs = list(res)
    if not recs:
        print("COULD NOT FIND 'UNITED STATES' AS LOCATION.")
        print("Checking all Location names snippet...")
        res2 = s.run("MATCH (n:Location) RETURN n.name LIMIT 10")
        for r in res2: print(r)
    else:
        for r in recs: print(r)

    print("\n--- SEARCHING WITHOUT LABEL ---")
    res3 = s.run("MATCH (n) WHERE toLower(coalesce(n.name, n.title, '')) CONTAINS 'united states' RETURN labels(n), n.name, n.title LIMIT 5")
    for r in res3: print(r)

driver.close()
