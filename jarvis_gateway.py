import os
import json
import time
import re
import asyncio
from typing import List, Optional, Literal
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from intelligence_core import IntelligenceCore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="JARVIS Strategic Intelligence Gateway")

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---

class ChatMessage(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    query: str
    messages: list[ChatMessage] = []
    mode: Literal["general", "graph_heavy"] = "general"
    include_graph: bool = False
    live: bool = False
    hops: int = Field(default=3, ge=1, le=5)
    limit: int = Field(default=25, ge=1, le=100)

# --- Intelligence Core ---

@app.post("/intelligence")
async def get_intelligence(request: QueryRequest):
    """
    Sovereign Intelligence Protocol (Phase 5 & 6)
    Combines GraphRAG (Neo4j) with Deep Scraper (Trafilatura) and Live Search.
    """
    start_time = time.time()
    target = request.query
    evidence = []
    context_cards = ""
    synthesis_text = ""
    graph_payload = {}
    
    try:
        # 1. Entity Resolution & Subgraph Retrieval
        from intelligence_core import setup_langchain_agent
        llm, retriever_tool = setup_langchain_agent()
        
        print(f"[JARVIS Gateway] Fetching sub-graph context for target: '{target}'...")
        context_cards = retriever_tool.run(target)
        
        # Multi-Keyword Fusion Logic
        if " " in target and (not context_cards or len(context_cards) < 100):
            keywords = [w for w in target.lower().split() if w not in ["about", "tell", "the", "in", "what", "is"]]
            for kw in keywords[:3]:
                kw_cards = retriever_tool.run(kw)
                if kw_cards:
                    if not context_cards:
                        context_cards = kw_cards
                    else:
                        # Simple de-dupe
                        if kw_cards.split("\n")[0] not in context_cards:
                            context_cards += "\n\n---\n\n" + kw_cards
        
        # 2. Deep Intelligence & Live Search
        core_instance = IntelligenceCore()
        
        # Deep Context (Graph-linked scrapes)
        deep_context = await core_instance.fetch_deep_context(target, max_articles=1)
        
        # Phase 6: Live Web Research Fallback
        live_results = {"cards": [], "text": ""}
        if request.live or not context_cards or (deep_context == "NO_DEEP_CONTEXT_FOUND"):
            print(f"[JARVIS Gateway] Initializing Live Web Research for: '{target}'...")
            live_results = await core_instance.web_search_and_scrape(target, num_results=2)
            
            if live_results.get("cards"):
                if not context_cards:
                    context_cards = "\n\n---\n\n".join(live_results["cards"])
                else:
                    context_cards += "\n\n---\n\n" + "\n\n---\n\n".join(live_results["cards"])

        # Truncate deep context
        if len(deep_context) > 5000:
            deep_context = deep_context[:5000] + "... [TRUNCATED] ..."
            
        full_intelligence_context = (deep_context if deep_context != "NO_DEEP_CONTEXT_FOUND" else "") 
        if live_results.get("text"):
            full_intelligence_context += "\n\n" + live_results["text"]
            
        retrieval_time = time.time() - start_time
        print(f"[JARVIS Gateway] Total Retrieval completed in {retrieval_time:.2f}s.")

        # 3. Citation Mapping
        evidence = []
        cards = [c.strip() for c in (context_cards or "").split("\n\n---\n\n") if c.strip()]
        for idx, card in enumerate(cards, 1):
            m_url = re.search(r"URL:\s*(\S+)", card)
            m_src = re.search(r"SOURCE:\s*([^\s|]+)", card)
            evidence.append({
                "id": idx,
                "url": m_url.group(1) if m_url else "",
                "card": card,
                "source": m_src.group(1) if m_src else "Unknown"
            })

        # 4. LLM Synthesis
        prompt_cards = "\n\n---\n\n".join(cards[:5])
        prompt = f"""### SOVEREIGN INTELLIGENCE PROTOCOL
Role: JARVIS (Anvay Project Reasoning Core)
Task: Extract and synthesize all specific facts from the provided sources.

<deep_intel>
{full_intelligence_context or "No deep/live intelligence found. Rely on graph metadata."}
</deep_intel>

<graph_metadata>
{prompt_cards or "No graph ontology cards found."}
</graph_metadata>

INSTRUCTIONS:
1. Synthesize a factual intelligence report based ONLY on the provided contexts.
2. Use numeric citations like [1], [2] corresponding to the SOURCE index in <graph_metadata>.
3. For <deep_intel> findings, mention the SOURCE URL explicitly.
4. DO NOT provide meta-commentary on content quality. 
5. If no info exists, state "Inference: No tactical records found for this query."
6. FORMAT: Use bold headings and bullet points.

REPORT:"""

        response = llm.invoke(prompt)
        synthesis_text = response.content if hasattr(response, "content") else str(response)

        # 5. Graph Payload (Optional)
        graph_payload = {"status": "skipped"}
        if request.include_graph:
            # Re-fetch for visualizer if needed
            graph_payload = {"status": "mocked", "nodes": [], "edges": []}

        # Final filtered sources for UI
        cited_ids = set(int(x) for x in re.findall(r"\[(\d+)\]", str(synthesis_text)) if x.isdigit())
        sources = [
            {"id": e["id"], "source": e["source"], "url": e["url"]}
            for e in evidence
            if (e["id"] in cited_ids or "Live" in str(e["card"])) and e["url"]
        ]

        return {
            "query": request.query,
            "extracted_entities": [target],
            "synthesis": synthesis_text,
            "graph": graph_payload,
            "sources": sources[:5], # Limit to top 5 citations
        }

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"[JARVIS Gateway] CRITICAL ERROR: {e}")
        print(error_msg)
        raise HTTPException(status_code=500, detail={"error": str(e)})

@app.get("/alerts")
async def get_alerts():
    if os.path.exists("threat_matrix.json"):
        with open("threat_matrix.json", "r") as f:
            return json.load(f)
    return {"active_threats": [], "status": "No anomalies detected."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
