import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
DATA_FILE = "data/ingested_data.json"

class GraphBuilder:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def initialize_schema(self):
        """Creates unique constraints for the ontology."""
        with self.driver.session() as session:
            # Constraints in Neo4j 4.4+
            constraints = [
                "CREATE CONSTRAINT article_url IF NOT EXISTS FOR (a:Article) REQUIRE a.url IS UNIQUE",
                "CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
                "CREATE CONSTRAINT org_name IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE",
                "CREATE CONSTRAINT loc_name IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE",
                "CREATE CONSTRAINT theme_name IF NOT EXISTS FOR (t:Theme) REQUIRE t.name IS UNIQUE"
            ]
            for query in constraints:
                try:
                    session.run(query)
                except Exception as e:
                    print(f"Constraint error (may already exist): {e}")
        print("Schema constraints initialized.")

    def build_graph(self):
        if not os.path.exists(DATA_FILE):
            print(f"Data file {DATA_FILE} not found.")
            return

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)

        print(f"Processing {len(records)} records into Neo4j...")
        
        with self.driver.session() as session:
            for record in tqdm(records):
                self._process_record(session, record)
        
        print("Graph construction complete.")

    def _process_record(self, session, record):
        # 1. Create Article Node
        # GDELT doesn't have titles, so we use the Source Name or URL as a backup name
        title = record.get("title")
        if not title or title == "No Title":
            title = f"Report from {record.get('source_name', 'Unknown Source')}"

        cypher_article = """
        MERGE (a:Article {url: $url})
        SET a.title = $title,
            a.name = $title,
            a.date = $date,
            a.tone = $tone,
            a.source = $source,
            a.ingestion_timestamp = $timestamp
        """
        session.run(cypher_article, 
                    url=record.get("url"), 
                    title=title,
                    date=record.get("date"),
                    tone=record.get("tone"),
                    source=record.get("source"),
                    timestamp=record.get("ingestion_timestamp"))

        # 2. Map Themes
        themes = record.get("themes", [])
        if record.get("source") == "GDELT" and isinstance(themes, list):
            themes = [t.split(",")[0] for t in themes if t]
        
        for theme_name in themes:
            cypher_theme = """
            MATCH (a:Article {url: $url})
            MERGE (t:Theme {name: $theme_name})
            MERGE (a)-[:HAS_THEME]->(t)
            """
            session.run(cypher_theme, url=record["url"], theme_name=theme_name)

        # 3. Map Locations
        locations = record.get("locations", [])
        for loc in locations:
            if not loc: continue
            loc_name = loc.split("#")[1] if "#" in loc else loc
            cypher_loc = """
            MATCH (a:Article {url: $url})
            MERGE (l:Location {name: $loc_name})
            MERGE (a)-[:LOCATED_IN]->(l)
            """
            session.run(cypher_loc, url=record["url"], loc_name=loc_name)

        # 4. Map Entities (Persons & Organizations) with Basic Normalization
        persons = record.get("persons", [])
        organizations = record.get("organizations", [])

        # Clean GDELT names and normalize (Entity Resolution)
        def normalize_name(name):
            # Basic normalization: strip titles and common suffixes
            n = name.split(",")[0] if "," in name else name
            prefixes = ["Mr ", "Ms ", "Mr. ", "Ms. ", "PM ", "President "]
            for p in prefixes:
                if n.startswith(p): n = n[len(p):]
            return n.strip()

        clean_persons = [normalize_name(p) for p in persons if p]
        clean_orgs = [normalize_name(o) for o in organizations if o]

        for p_name in set(clean_persons):
            cypher_p = """
            MATCH (a:Article {url: $url})
            MERGE (p:Person {name: $name})
            MERGE (p)-[r:MENTIONED_IN]->(a)
            ON CREATE SET r.weight = 1
            ON MATCH SET r.weight = r.weight + 1
            """
            session.run(cypher_p, url=record["url"], name=p_name)

        for o_name in set(clean_orgs):
            cypher_o = """
            MATCH (a:Article {url: $url})
            MERGE (o:Organization {name: $name})
            MERGE (o)-[r:MENTIONED_IN]->(a)
            ON CREATE SET r.weight = 1
            ON MATCH SET r.weight = r.weight + 1
            """
            session.run(cypher_o, url=record["url"], name=o_name)

        # 5. Co-occurrence (Person-Organization Links)
        if clean_persons and clean_orgs:
            cypher_assoc = """
            UNWIND $persons as p_name
            UNWIND $orgs as o_name
            MATCH (p:Person {name: p_name}), (o:Organization {name: o_name})
            MERGE (p)-[r:ASSOCIATED_WITH]->(o)
            ON CREATE SET r.weight = 1
            ON MATCH SET r.weight = r.weight + 1
            """
            session.run(cypher_assoc, persons=list(set(clean_persons)), orgs=list(set(clean_orgs)))

if __name__ == "__main__":
    builder = GraphBuilder()
    try:
        builder.initialize_schema()
        builder.build_graph()
    finally:
        builder.close()
