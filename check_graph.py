from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
URI = "bolt://localhost:7687"
USER = os.getenv("NEO4J_USERNAME", "neo4j")
PASS = os.getenv("NEO4J_PASSWORD", "Devang@0305")

def check():
    driver = GraphDatabase.driver(URI, auth=(USER, PASS))
    with driver.session() as session:
        # Check for ARMEDCONFLICT theme connectivity
        query = """
        MATCH (e:Theme)-[r]-(n)
        WHERE e.name CONTAINS 'ARMEDCONFLICT'
        RETURN type(r) as rel_type, labels(n) as target_labels, n.title as title LIMIT 10
        """
        records = session.run(query)
        print("--- ARMEDCONFLICT CONNECTIONS ---")
        for r in records:
            print(f"({r['rel_type']}) -> {r['target_labels']} (Title: {r['title']})")

    driver.close()

if __name__ == "__main__":
    check()
