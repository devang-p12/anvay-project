from intelligence_core import IntelligenceCore
import os

os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "Devang@0305"

core = IntelligenceCore()
print("\n--- TESTING RETRIEVER: UNITED STATES ---")
res = core.subgraph_retriever("united states")
print(f"Results length: {len(res)}")
print(res)
