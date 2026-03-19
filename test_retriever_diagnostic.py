from intelligence_core import IntelligenceCore

core = IntelligenceCore()
print("\n--- TESTING RETRIEVER: KABUL ---")
print(core.subgraph_retriever("kabul"))

print("\n--- TESTING RETRIEVER: INDIAN ---")
print(core.subgraph_retriever("indian"))

print("\n--- CHECKING NODE LABELS ---")
from neo4j import GraphDatabase
from intelligence_core import NEO4J_URI, NEO4J_USER, NEO4J_PASS

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
with driver.session() as s:
    res = s.run("MATCH (n) RETURN labels(n), n.name LIMIT 5")
    for r in res:
        print(r)
driver.close()
