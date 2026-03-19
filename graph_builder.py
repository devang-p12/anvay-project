import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_USERNAME or not NEO4J_PASSWORD:
    raise RuntimeError(
        "NEO4J_USERNAME and NEO4J_PASSWORD must be set in the environment; "
        "do not hardcode database credentials in source code."
    )
DATA_FILE = "data/ingested_data.json"

if "neo4j:7687" in NEO4J_URI:
    NEO4J_URI = NEO4J_URI.replace("neo4j:7687", "localhost:7687")

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
                "CREATE CONSTRAINT theme_name IF NOT EXISTS FOR (t:Theme) REQUIRE t.name IS UNIQUE",
                # New source types
                "CREATE CONSTRAINT economic_id IF NOT EXISTS FOR (e:EconomicIndicator) REQUIRE e.record_id IS UNIQUE",
                "CREATE CONSTRAINT weather_id IF NOT EXISTS FOR (w:WeatherAlert) REQUIRE w.record_id IS UNIQUE",
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
                source = record.get("source", "GDELT")
                if source in ("WorldBank", "NDAP"):
                    self._process_economic_indicator(session, record)
                elif source == "IMD":
                    self._process_weather_alert(session, record)
                else:
                    self._process_record(session, record)  # GDELT, PIB, default
        
        print("Graph construction complete.")

    def _process_record(self, session, record):
        # 1. Create Article Node
        # GDELT doesn't have titles, so we use the Source Name or URL as a backup name
        title = record.get("title")
        if not title or title == "No Title":
            title = f"Report from {record.get('source_name', 'Unknown Source')}"

        cypher_article = """
        MERGE (a:Article:StrategicReport {url: $url})
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

    def _process_economic_indicator(self, session, record):
        """Creates an EconomicIndicator node from World Bank / NDAP data."""
        session.run("""
        MERGE (e:EconomicIndicator {record_id: $record_id})
        SET e.title = $title,
            e.date = $date,
            e.indicator_name = $indicator_name,
            e.value = $value,
            e.url = $url,
            e.source = $source,
            e.ingestion_timestamp = $timestamp
        """,
        record_id=record["record_id"], title=record.get("title"),
        date=record.get("date"), indicator_name=record.get("indicator_name", ""),
        value=str(record.get("value", "")), url=record.get("url"),
        source=record.get("source"), timestamp=record.get("ingestion_timestamp"))

        # Link to countries/locations
        for loc in set(filter(None, record.get("locations", []))):
            session.run("""
            MERGE (l:Location {name: $name})
            MATCH (e:EconomicIndicator {record_id: $record_id})
            MERGE (e)-[:MEASURED_IN]->(l)
            """, name=loc, record_id=record["record_id"])

        for theme in set(filter(None, record.get("themes", []))):
            session.run("""
            MERGE (t:Theme {name: $name})
            MATCH (e:EconomicIndicator {record_id: $record_id})
            MERGE (e)-[:HAS_THEME]->(t)
            """, name=theme, record_id=record["record_id"])

    def _process_weather_alert(self, session, record):
        """Creates a WeatherAlert node from IMD data."""
        session.run("""
        MERGE (w:WeatherAlert {record_id: $record_id})
        SET w.title = $title,
            w.date = $date,
            w.alert_type = $alert_type,
            w.alert_text = $alert_text,
            w.url = $url,
            w.source = 'IMD',
            w.ingestion_timestamp = $timestamp
        """,
        record_id=record["record_id"], title=record.get("title"),
        date=record.get("date"), alert_type=record.get("alert_type", "Weather Alert"),
        alert_text=record.get("alert_text", "")[:500], url=record.get("url"),
        timestamp=record.get("ingestion_timestamp"))

        # Link regions affected
        for loc in set(filter(None, record.get("locations", []))):
            if not loc: continue
            session.run("""
            MERGE (l:Location {name: $name})
            MATCH (w:WeatherAlert {record_id: $record_id})
            MERGE (w)-[:THREATENS]->(l)
            """, name=loc, record_id=record["record_id"])


if __name__ == "__main__":
    builder = GraphBuilder()
    try:
        builder.initialize_schema()
        builder.build_graph()
    finally:
        builder.close()
