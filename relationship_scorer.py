import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "Devang@0305")

# Use localhost for host-based execution
if "neo4j:7687" in NEO4J_URI:
    NEO4J_URI = NEO4J_URI.replace("neo4j:7687", "localhost:7687")

print(f"Connecting to Neo4j at {NEO4J_URI}...")

class RelationshipScorer:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return result.consume().counters

    def create_indexes(self):
        print("Creating indexes for faster MERGE operations...")
        self.run_query("CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.name)")
        self.run_query("CREATE INDEX IF NOT EXISTS FOR (o:Organization) ON (o.name)")
        self.run_query("CREATE INDEX IF NOT EXISTS FOR (l:Location) ON (l.name)")
        self.run_query("CREATE INDEX IF NOT EXISTS FOR (t:Theme) ON (t.name)")
        print("Indexes created.")

    def create_graph_schema_from_reports(self):
        print("Extracting Document Arrays into Graph Nodes...")
        
        # Extract Persons
        res = self.run_query('''
        MATCH (r:StrategicReport)
        WHERE r.persons IS NOT NULL
        UNWIND r.persons AS pName
        MERGE (p:Person {name: pName})
        MERGE (r)-[:MENTIONS_PERSON]->(p)
        ''')
        print(f"Persons extracted. Nodes created: {res.nodes_created}, Relationships: {res.relationships_created}")

        # Extract Orgs
        res = self.run_query('''
        MATCH (r:StrategicReport)
        WHERE r.organizations IS NOT NULL
        UNWIND r.organizations AS oName
        MERGE (o:Organization {name: oName})
        MERGE (r)-[:MENTIONS_ORG]->(o)
        ''')
        print(f"Organizations extracted. Nodes created: {res.nodes_created}, Relationships: {res.relationships_created}")

        # Extract Locations
        res = self.run_query('''
        MATCH (r:StrategicReport)
        WHERE r.locations IS NOT NULL
        UNWIND r.locations AS lName
        MERGE (l:Location {name: lName})
        MERGE (r)-[:MENTIONS_LOCATION]->(l)
        ''')
        print(f"Locations extracted. Nodes created: {res.nodes_created}, Relationships: {res.relationships_created}")
        
        # Extract Themes
        res = self.run_query('''
        MATCH (r:StrategicReport)
        WHERE r.themes IS NOT NULL
        UNWIND r.themes AS tName
        MERGE (t:Theme {name: tName})
        MERGE (r)-[:MENTIONS_THEME]->(t)
        ''')
        print(f"Themes extracted. Nodes created: {res.nodes_created}, Relationships: {res.relationships_created}")

    def score_relationships(self, min_cooccurrence=2):
        print(f"Scoring co-occurrences (threshold >= {min_cooccurrence})...")
        
        # Person to Organization
        res = self.run_query('''
        MATCH (p:Person)<-[:MENTIONS_PERSON]-(r:StrategicReport)-[:MENTIONS_ORG]->(o:Organization)
        WITH p, o, count(r) as weight
        WHERE weight >= $min_weight
        MERGE (p)-[rel:ASSOCIATED_WITH]->(o)
        SET rel.weight = weight
        ''', parameters={"min_weight": min_cooccurrence})
        print(f"Person-Org connections created: {res.relationships_created}")

        # Person to Location
        res = self.run_query('''
        MATCH (p:Person)<-[:MENTIONS_PERSON]-(r:StrategicReport)-[:MENTIONS_LOCATION]->(l:Location)
        WITH p, l, count(r) as weight
        WHERE weight >= $min_weight
        MERGE (p)-[rel:LOCATED_AT]->(l)
        SET rel.weight = weight
        ''', parameters={"min_weight": min_cooccurrence})
        print(f"Person-Location connections created: {res.relationships_created}")
        
        # Org to Location
        res = self.run_query('''
        MATCH (o:Organization)<-[:MENTIONS_ORG]-(r:StrategicReport)-[:MENTIONS_LOCATION]->(l:Location)
        WITH o, l, count(r) as weight
        WHERE weight >= $min_weight
        MERGE (o)-[rel:OPERATES_IN]->(l)
        SET rel.weight = weight
        ''', parameters={"min_weight": min_cooccurrence})
        print(f"Org-Location connections created: {res.relationships_created}")

        # Person to Person
        res = self.run_query('''
        MATCH (p1:Person)<-[:MENTIONS_PERSON]-(r:StrategicReport)-[:MENTIONS_PERSON]->(p2:Person)
        WHERE id(p1) < id(p2)
        WITH p1, p2, count(r) as weight
        WHERE weight >= $min_weight
        MERGE (p1)-[rel:KNOWS_OR_COOCCURRED_WITH]->(p2)
        SET rel.weight = weight
        ''', parameters={"min_weight": min_cooccurrence})
        print(f"Person-Person connections created: {res.relationships_created}")
        
        print("Graph normalization and relationship weighting completed!")

if __name__ == "__main__":
    scorer = RelationshipScorer(NEO4J_URI, NEO4J_USER, NEO4J_PASS)
    try:
        scorer.create_indexes()
        scorer.create_graph_schema_from_reports()
        scorer.score_relationships(min_cooccurrence=2)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        scorer.close()
