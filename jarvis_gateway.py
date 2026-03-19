from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import json
import os

# Import the existing Intelligence Engine built in Phase 2
from intelligence_core import setup_langchain_agent, NEO4J_URI, NEO4J_USER, NEO4J_PASS

from neo4j import GraphDatabase

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="JARVIS Backend Gateway", description="Sovereign AI Mini-Palantir API for India")

# Enable CORS for the React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the exact frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("[JARVIS Gateway] Initializing Sovereign GraphRAG Inference Engine...")
try:
    llm, retriever_tool = setup_langchain_agent()
    # In a full deployment, we'd use AgentExecutor. We map the simplified logic.
except Exception as e:
    print(f"[JARVIS Gateway] Error initializing GraphRAG: {e}")
    llm = None
    retriever_tool = None

# Pydantic Schemas
class QueryRequest(BaseModel):
    query: str
    include_graph: bool = False
    hops: int = Field(default=3, ge=1, le=5)
    limit: int = Field(default=25, ge=1, le=100)
    
class VoiceRequest(BaseModel):
    audio_base64: str
    language: str = "hi-IN"

@app.get("/")
async def root():
    """
    Root endpoint for health checks and status.
    """
    return {
        "status": "online",
        "system": "JARVIS Sovereign AI Gateway",
        "version": "1.0.0",
        "endpoints": {
            "intelligence": "/intelligence [POST]",
            "graph_health": "/health/graph [GET]",
            "alerts": "/alerts [GET]",
            "voice": "/voice [POST]"
        }
    }


@app.get("/health/graph")
async def graph_health():
    """
    Lightweight health check for Neo4j connectivity and basic schema presence.
    """
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        with driver.session() as session:
            # Simple ping and a tiny introspection query
            summary = session.run("RETURN 1 AS ok").single()
            node_counts = session.run(
                """
                CALL db.labels() YIELD label
                WHERE label IN ['Article', 'Person', 'Organization', 'Location', 'Theme']
                WITH collect(label) AS labels
                RETURN labels
                """
            ).single()
        driver.close()
        return {
            "status": "online",
            "neo4j_uri": NEO4J_URI,
            "ping": bool(summary and summary["ok"] == 1),
            "core_labels": node_counts["labels"] if node_counts else [],
        }
    except Exception as e:
        return {
            "status": "degraded",
            "neo4j_uri": NEO4J_URI,
            "error": str(e),
        }

@app.post("/intelligence")
async def get_intelligence(request: QueryRequest):
    """
    Task 2: Route natural language queries into the Neo4j LlamaIndex array and synthesize with Sarvam-30B.
    """
    if not llm or not retriever_tool:
        raise HTTPException(status_code=503, detail="Inference engine offline.")
        
    try:
        # 1. Advanced Extractor: preserve original casing for Neo4j CONTAINS match
        stop_words = {"about", "tell", "show", "what", "where", "info", "information", "something", "on", "the", "know"}
        # Keep original-cased words but filter by lowercase stop-words
        original_words = request.query.replace("?", "").split()
        filtered_words = [w for w in original_words if len(w) > 3 and w.lower() not in stop_words]
        
        if len(filtered_words) >= 2:
            target = " ".join(filtered_words[-2:])  # e.g. "United States"
        elif filtered_words:
            target = filtered_words[-1]
        else:
            target = "India"
        target = target.strip()
        
        import time
        start_time = time.time()
        
        # 2. Graph Retrieval Path
        if not retriever_tool:
            print("[JARVIS Gateway] WARNING: Retriever tool is not initialized.")
            return {"synthesis": "Retriever Offline", "graph_paths": "No data retrieved."}
            
        print(f"[JARVIS Gateway] Fetching sub-graph context for target: '{target}'...")
        context = retriever_tool.run(target)
        retrieval_time = time.time() - start_time
        print(f"[JARVIS Gateway] Retrieval completed in {retrieval_time:.2f}s.")
        
        if not context:
            print(f"[JARVIS Gateway] WARNING: No graph data found for target '{target}'. Returning early.")
            return {
                "query": request.query,
                "extracted_entities": [target],
                "graph_paths": "",
                "synthesis": f"No intelligence data was found in the graph database for **'{target}'**. The entity may not have been ingested yet, or the search term may need to be more specific (e.g., try 'India' instead of 'Indian foreign policy')."
            }
        
        # 3. Ask the LLM to answer conversationally using the graph context
        cards = [c.strip() for c in context.strip().split("\n\n---\n\n") if c.strip()]

        prompt = f"""
You are ANVAY, a strategic intelligence assistant.

The user has asked:
\"\"\"{request.query}\"\"\"

You have access to structured intelligence cards from an ontology-backed Neo4j graph.
Each card describes one finding (articles, economic indicators, weather alerts, etc.).

INTELLIGENCE CARDS:
\"\"\"{context}\"\"\"

Instructions:
- Answer in a natural, concise way like a professional analyst.
- Synthesize across the cards instead of listing them verbatim.
- Be explicit when something is uncertain or missing from the graph.
- If relevant, refer to patterns over time or entities, but do NOT invent facts that are not supported.
- Use short paragraphs and, when helpful, bullet points.
"""

        try:
            llm_response = llm.invoke(prompt)
            # ChatOpenAI returns an object with .content; mock may just be a string
            synthesis_text = getattr(llm_response, "content", llm_response)
        except Exception as e:
            print(f"[JARVIS Gateway] LLM synthesis failed, falling back to raw cards: {e}")
            formatted_cards = ""
            for i, card in enumerate(cards, 1):
                formatted_cards += f"\n### Finding {i}\n```\n{card}\n```\n"
            synthesis_text = formatted_cards or "Intelligence retrieved, but no readable synthesis is available."
        
        print(f"[JARVIS Gateway] Report generated for '{target}' ({len(cards)} findings).")

        graph_payload = None
        if request.include_graph:
            graph_start = time.time()
            try:
                driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
                with driver.session() as session:
                    cypher = f"""
                    MATCH (e)
                    WHERE (e:Person OR e:Organization OR e:Location OR e:Theme)
                      AND toLower(e.name) CONTAINS toLower($target)
                    WITH e
                    MATCH p = (e)-[:MENTIONED_IN|ASSOCIATED_WITH|LOCATED_IN|HAS_THEME|MEASURED_IN|THREATENS*1..{request.hops}]-(n)
                    WHERE (n:Article OR n:EconomicIndicator OR n:WeatherAlert OR n:Person OR n:Organization OR n:Location OR n:Theme)
                    RETURN p
                    LIMIT $limit
                    """
                    paths = list(session.run(cypher, target=target, limit=request.limit))
                driver.close()

                nodes = {}
                edges = {}

                for rec in paths:
                    path = rec.get("p")
                    if not path:
                        continue

                    for node in path.nodes:
                        node_id = str(node.id)
                        if node_id in nodes:
                            continue
                        nodes[node_id] = {
                            "id": node_id,
                            "labels": list(node.labels),
                            "properties": {
                                k: v
                                for k, v in dict(node).items()
                                if k in {"name", "title", "url", "date", "source", "indicator_name", "value", "alert_type"}
                            },
                        }

                    for rel in path.relationships:
                        rel_id = str(rel.id)
                        if rel_id in edges:
                            continue
                        edges[rel_id] = {
                            "id": rel_id,
                            "type": rel.type,
                            "source": str(rel.start_node.id),
                            "target": str(rel.end_node.id),
                            "properties": dict(rel),
                        }

                graph_payload = {
                    "target": target,
                    "hops": request.hops,
                    "limit": request.limit,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "nodes": list(nodes.values()),
                    "edges": list(edges.values()),
                }
            except Exception as e:
                graph_payload = {
                    "status": "error",
                    "error": str(e),
                }
            graph_time = time.time() - graph_start
            print(f"[JARVIS Gateway] Graph payload built in {graph_time:.2f}s.")
        
        return {
            "query": request.query,
            "extracted_entities": [target],
            "graph_paths": context,
            "synthesis": synthesis_text,
            "graph": graph_payload,
        }
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"[JARVIS Gateway] CRITICAL ERROR during intelligence processing: {e}")
        print(error_msg)
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": error_msg})

@app.get("/alerts")
async def get_alerts():
    """
    Task 3: Parse the active Threat Matrix JSON cache generated by the background daemon.
    """
    if os.path.exists("threat_matrix.json"):
        with open("threat_matrix.json", "r") as f:
            return json.load(f)
    return {"active_threats": [], "status": "No anomalies detected."}

@app.post("/voice")
async def process_voice(request: VoiceRequest):
    """
    Task 4: WebRTC Integration with Sarvam Saaras/Bulbul models for native linguistic translation.
    Currently mocked to handle schemas dynamically.
    """
    # Placeholder for Sarvam audio processing pipeline
    mocked_transcript = "What are the active threats in Kabul?" if "hi" in request.language else "Translate failure."
    
    return {
        "status": "processing",
        "sarvam_audio_engine": "MOCKED",
        "stt_transcript": mocked_transcript,
        "note": "Requires active Sarvam API keys to translate base64 stream"
    }

if __name__ == "__main__":
    import uvicorn
    # Task 4: Host precisely on port 8080 or 8000 depending on frontend mappings
    print("\n" + "="*60)
    print("         JARVIS GATEWAY: SOVEREIGN AI SECURE ACCESS        ")
    print("="*60)
    print(f"[JARVIS] Intelligence Core: ONLINE")
    print(f"[JARVIS] Access URL: http://localhost:8888/")
    print(f"[JARVIS] Monitoring: http://localhost:8888/alerts")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8888)
