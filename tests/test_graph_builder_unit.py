import re


class _FakeSession:
    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query, params))
        return []


def _extract_normalized_entities(fake_session: _FakeSession):
    person_names = []
    org_names = []
    for query, params in fake_session.calls:
        if "MERGE (p:Person" in query:
            person_names.append(params.get("name"))
        if "MERGE (o:Organization" in query:
            org_names.append(params.get("name"))
    return person_names, org_names


def test_process_record_creates_strategic_report_article_and_normalizes_entities():
    # Import inside test so pytest collection doesn't require Neo4j running
    from graph_builder import GraphBuilder

    session = _FakeSession()
    builder = GraphBuilder()

    record = {
        "url": "https://example.com/a1",
        "title": "No Title",
        "source_name": "Example Source",
        "date": "20260101000000",
        "tone": "0.2,0,0,0,0,0,0",
        "source": "GDELT",
        "ingestion_timestamp": "2026-01-01T00:00:00Z",
        "persons": ["Mr. John Doe,123", "President Jane Roe", "Ms Alice"],
        "organizations": ["PM Office", "Mr Acme Corp,999"],
        "themes": ["TAX_FNCACT_TERRORISM,123", "CRISISLEX_C02,456"],
        "locations": ["US#New York", "Kabul"],
    }

    # Directly call the method under test (no DB)
    builder._process_record(session, record)

    # 1) Ensure article MERGE uses the enriched label set
    article_queries = [q for q, _ in session.calls if "MERGE (a:Article:StrategicReport" in q]
    assert article_queries, "Expected StrategicReport-labeled Article MERGE query."

    # 2) Ensure entity normalization removed titles and trailing offsets
    person_names, org_names = _extract_normalized_entities(session)

    # sanity: we created at least one person and org
    assert any(person_names)
    assert any(org_names)

    # Titles removed
    assert "John Doe" in person_names
    assert "Jane Roe" in person_names
    assert "Alice" in person_names

    # Numeric offsets removed from GDELT-like suffixes
    assert not any(re.search(r",\d+$", n or "") for n in person_names + org_names)


def test_process_record_creates_expected_relationship_queries():
    from graph_builder import GraphBuilder

    session = _FakeSession()
    builder = GraphBuilder()

    record = {
        "url": "https://example.com/a2",
        "title": "Example",
        "date": "20260102000000",
        "tone": "0,0,0,0,0,0,0",
        "source": "GDELT",
        "ingestion_timestamp": "2026-01-02T00:00:00Z",
        "persons": ["Mr John Doe"],
        "organizations": ["Acme Corp"],
        "themes": ["USPEC_SOMETHING,12"],
        "locations": ["IN#Delhi"],
    }

    builder._process_record(session, record)

    queries = "\n".join(q for q, _ in session.calls)
    assert "MERGE (a)-[:HAS_THEME]->(t)" in queries
    assert "MERGE (a)-[:LOCATED_IN]->(l)" in queries
    assert "MERGE (p)-[r:MENTIONED_IN]->(a)" in queries
    assert "MERGE (o)-[r:MENTIONED_IN]->(a)" in queries
    assert "MERGE (p)-[r:ASSOCIATED_WITH]->(o)" in queries

