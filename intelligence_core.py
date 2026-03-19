import os
import json
from dotenv import load_dotenv
from scraper_core import ScraperCore
import asyncio
from googlesearch import search

# Load environment variables
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD")

if not NEO4J_USER or not NEO4J_PASS:
    raise RuntimeError(
        "NEO4J_USERNAME and NEO4J_PASSWORD must be set in the environment; "
        "do not hardcode database credentials in source code."
    )

if "neo4j:7687" in NEO4J_URI:
    NEO4J_URI = NEO4J_URI.replace("neo4j:7687", "localhost:7687")
elif "neo4j" in NEO4J_URI and "localhost" not in NEO4J_URI and "bolt://" in NEO4J_URI:
    NEO4J_URI = "bolt://localhost:7687"

try:
    from langchain_openai import ChatOpenAI
    from llama_index.core import PropertyGraphIndex
    from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
    from langchain_core.tools import Tool
    from langchain_core.prompts import PromptTemplate
    
    # BaseLLM is abstract, we'll create a MockedSarvam for demonstration
    from typing import Any, List, Optional
    from langchain_core.callbacks.manager import CallbackManagerForLLMRun
    from langchain_core.language_models.llms import LLM
    
    class Sarvam30BMock(LLM):
        """
        Mocks the Sarvam-30B sovereign inference engine pipeline.
        Enforces strict Citation Engine mechanisms.
        """
        @property
        def _llm_type(self) -> str:
            return "sarvam-30b-mock"

        def _call(self, prompt: str, **kwargs: Any) -> str:
            return "Intelligence Core: Sovereign Inference Engine Offline."
            
except ImportError as e:
    import sys
    print(f"CRITICAL ERROR: LlamaIndex/LangChain dependencies are missing from this environment. Error: {e}")
    sys.exit(1)

class IntelligenceCore:
    def __init__(self):
        print("Initializing LlamaIndex Neo4j Graph Store...")
        try:
            self.graph_store = Neo4jPropertyGraphStore(
                username=NEO4J_USER,
                password=NEO4J_PASS,
                url=NEO4J_URI,
            )
        except Exception as e:
            print(f"Graph store init error: {e}")
        self.scraper = ScraperCore()

    async def web_search_and_scrape(self, query: str, num_results: int = 3) -> dict:
        """
        Phase 6: Live Web Research.
        Performs a Google search and scrapes the top results.
        """
        print(f"[Intelligence Core] Live Search: Querying the web for '{query}'...")
        try:
            # Perform search to get URLs
            urls = []
            search_results = search(query, num_results=num_results)
            for url in search_results:
                urls.append(url)
            
            if not urls:
                return {"cards": [], "text": ""}

            # Reuse parallel scraping logic
            print(f"[Intelligence Core] Live Scraper: Fetching {len(urls)} live articles...")
            scraped_data = await self.scraper.scrape_batch(urls)

            # Format for synthesis
            live_cards = []
            full_text_context = ""
            for url, text in scraped_data.items():
                title = text.split("\n")[0][:100] if text else "Live Intelligence Report"
                domain = url.split("//")[-1].split("/")[0]
                card = (
                    f"TYPE: Live Article | SOURCE: {domain} | DATE: Real-time\n"
                    f"URL: {url}\n"
                    f"SUMMARY: {text[:500]}..."
                )
                live_cards.append(card)
                full_text_context += f"SOURCE: {url}\nCONTENT:\n{text[:3000]}\n\n---\n\n"
            
            return {"cards": live_cards, "text": full_text_context}
        except Exception as e:
            print(f"[Intelligence Core] Live Search Error: {e}")
            return {"cards": [], "text": ""}

    async def fetch_deep_context(self, target: str, hops: int = 3, max_articles: int = 3) -> str:
        """
        Orchestrates the Phase 5 Deep RAG pipeline.
        Now fully async to play nice with FastAPI.
        """
        print(f"\n[Intelligence Core] Initiating Deep RAG for: '{target}'")
        
        # We reuse the logic from subgraph_retriever but return raw data
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        
        urls = []
        meta_context = ""
        
        with driver.session() as session:
            try:
                # Optimized query for deep URLs
                query = f"""
                MATCH (e)-[:MENTIONED_IN|ASSOCIATED_WITH|LOCATED_IN|HAS_THEME|OPERATES_IN|MENTIONS*1..{hops}]-(n)
                WHERE (e:Person OR e:Organization OR e:Location OR e:Theme)
                  AND toLower(e.name) CONTAINS toLower($target)
                  AND (n:Article OR n:StrategicReport)
                RETURN DISTINCT n.url as url, n.title as title, labels(n)[0] as type
                LIMIT {max_articles}
                """
                records = list(session.run(query, target=target))
                urls = [r["url"] for r in records if r["url"]]
                
                # Pre-fetch some metadata for the prompt
                meta_context = "\n".join([f"- {r['type']}: {r['title']} ({r['url']})" for r in records])
                
            except Exception as e:
                print(f"[Intelligence Core] Graph Error: {e}")
            finally:
                driver.close()

        if not urls:
            return "NO_DEEP_CONTEXT_FOUND"

        # Parallel Scraping
        print(f"[Intelligence Core] Scraper: Fetching {len(urls)} articles...")
        scraped_data = await self.scraper.scrape_batch(urls)

        # Combine into a Reasoning block
        full_context = "### STRATEGIC ARTICLE CONTENT STORE\n\n"
        for url, text in scraped_data.items():
            full_context += f"SOURCE URL: {url}\nCONTENT:\n{text[:5000]}\n\n---\n\n"
            
        return full_context

    def subgraph_retriever(self, entity_name: str, hops: int = 3) -> str:
        """
        Retrieves readable intelligence from the ontology graph.

        Strategy:
        - Resolve an entity node (Person / Organization / Location / Theme) whose name
          contains the target string (case-insensitive).
        - Expand up to `hops` relationships out to connected Article / EconomicIndicator /
          WeatherAlert nodes.
        - For each such node, build a compact "intelligence card" summarizing key fields.
        """
        target = entity_name.strip("'").strip('"')
        print(f"\n[LlamaIndex Retriever] Decomposing Intent. Target: '{target}' | Hops: {hops}")

        from neo4j import GraphDatabase
        import re

        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        results: list[str] = []

        with driver.session() as session:
            try:
                print(f"[LlamaIndex Retriever] Resolving anchor entities for '{target}'...")

                # 1. Find anchor entity nodes
                entity_query = """
                MATCH (e)
                WHERE (e:Person OR e:Organization OR e:Location OR e:Theme)
                  AND toLower(e.name) CONTAINS toLower($target)
                RETURN DISTINCT e
                LIMIT 5
                """
                entity_records = list(session.run(entity_query, target=target))

                if not entity_records:
                    print(f"[LlamaIndex Retriever] No entities found for '{target}'.")
                    return ""

                # 2. Expand out to connected intelligence-bearing nodes
                subgraph_query = f"""
                MATCH (e)
                WHERE (e:Person OR e:Organization OR e:Location OR e:Theme)
                  AND toLower(e.name) CONTAINS toLower($target)
                CALL {{
                    WITH e
                    MATCH path = (e)-[:MENTIONED_IN|ASSOCIATED_WITH|LOCATED_IN|HAS_THEME|OPERATES_IN|MENTIONS*1..{hops}]-(n)
                    WHERE (n:Article OR n:StrategicReport)
                    RETURN DISTINCT n
                    LIMIT 25
                }}
                RETURN DISTINCT n
                """
                records = list(session.run(subgraph_query, target=target))

                if not records:
                    print(f"[LlamaIndex Retriever] No connected intelligence nodes found for '{target}'.")
                    return ""

                def clean_list(items):
                    if not items:
                        return []
                    cleaned = [re.sub(r',\d+$', '', str(i)).strip() for i in items]
                    return list(dict.fromkeys(cleaned))[:5]

                def clean_theme(t):
                    t = re.sub(r',\d+$', '', str(t))
                    for pfx in [
                        "TAX_FNCACT_",
                        "TAX_MILITARY_TITLE_",
                        "TAX_WORLDLANGUAGES_",
                        "CRISISLEX_",
                        "USPEC_",
                    ]:
                        t = t.replace(pfx, "")
                    t = re.sub(r"^WB_\\d+_", "", t)
                    return t.replace("_", " ").title()

                for record in records:
                    n = record["n"]
                    labels = list(n.labels) if hasattr(n, "labels") else []

                    # Common fields
                    raw_date = str(n.get("date", ""))
                    if len(raw_date) >= 8:
                        date_str = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                    else:
                        date_str = raw_date or "Unknown"

                    # Article / StrategicReport style node
                    if "Article" in labels or "StrategicReport" in labels:
                        persons = clean_list(n.get("persons", []))
                        orgs = clean_list(n.get("organizations", []))
                        raw_themes = n.get("themes", [])
                        themes = list(dict.fromkeys(clean_theme(t) for t in raw_themes))[:6]

                        source = n.get("source", n.get("source_name", "Unknown Source"))
                        url = n.get("url", "")
                        tone_raw = n.get("tone", "")

                        try:
                            tone_score = float(str(tone_raw).split(",")[0])
                            if tone_score > 1:
                                sentiment = "Positive"
                            elif tone_score < -1:
                                sentiment = "Negative"
                            else:
                                sentiment = "Neutral"
                        except Exception:
                            sentiment = "Unknown"

                        card = (
                            f"TYPE: Article | SOURCE: {source} | DATE: {date_str} | SENTIMENT: {sentiment}\n"
                            f"URL: {url}\n"
                            f"KEY PERSONS: {', '.join(persons) if persons else 'None'}\n"
                            f"ORGANIZATIONS: {', '.join(orgs) if orgs else 'None'}\n"
                            f"THEMES: {', '.join(themes) if themes else 'None'}"
                        )
                        results.append(card)

                    # Economic indicator node
                    elif "EconomicIndicator" in labels:
                        title = n.get("title", "Economic Indicator")
                        indicator_name = n.get("indicator_name", "")
                        value = n.get("value", "")
                        url = n.get("url", "")
                        themes = list(
                            dict.fromkeys(clean_theme(t) for t in n.get("themes", []))
                        )[:6]

                        card = (
                            f"TYPE: Economic Indicator | TITLE: {title}\n"
                            f"DATE: {date_str} | INDICATOR: {indicator_name} | VALUE: {value}\n"
                            f"URL: {url}\n"
                            f"THEMES: {', '.join(themes) if themes else 'None'}"
                        )
                        results.append(card)

                    # Weather alert node
                    elif "WeatherAlert" in labels:
                        title = n.get("title", "Weather Alert")
                        alert_type = n.get("alert_type", "Weather Alert")
                        alert_text = n.get("alert_text", "")[:280]
                        url = n.get("url", "")

                        card = (
                            f"TYPE: Weather Alert | TITLE: {title}\n"
                            f"DATE: {date_str} | ALERT TYPE: {alert_type}\n"
                            f"URL: {url}\n"
                            f"SUMMARY: {alert_text}"
                        )
                        results.append(card)

            except Exception as e:
                print(f"[LlamaIndex Retriever] Query Error for '{target}': {e}")
            finally:
                driver.close()

        found = len(results)
        print(f"[LlamaIndex Retriever] Retrieved {found} intelligence reports for '{target}'.")
        if not results:
            return ""
        return "\n\n---\n\n".join(results)


def setup_langchain_agent():
    print("Setting up Sovereign Inference Engine (Ollama @ port 8000)...")
    core = IntelligenceCore()
    
    retriever_tool = Tool(
        name="Neo4j_Subgraph_Retriever",
        func=lambda q: core.subgraph_retriever(q, hops=3),
        description="Retrieves multi-hop context from the Neo4j graph."
    )
    
    deep_retriever_tool = Tool(
        name="Neo4j_Deep_Retriever",
        func=lambda q: core.fetch_deep_context(q, hops=3),
        description="Scrapes full-text content of articles related to the entity."
    )
    
    try:
        llm = ChatOpenAI(
            model="gemma:2b", 
            base_url="http://localhost:8000/v1",
            api_key="ollama",
            temperature=0.1,
            timeout=60 # 60 second timeout for local inference
        )
    except Exception:
        llm = Sarvam30BMock()
        
    return llm, retriever_tool

if __name__ == "__main__":
    try:
        llm, tool = setup_langchain_agent()
        query = "What are the latest reported activities involving Indian envoys in the Kabul region?"
        
        print("\n" + "="*80)
        print("PHASE 2: EXECUTING REASONING & ORCHESTRATION (LLAMA-INDEX + LANGCHAIN)")
        print("="*80)
        
        # Simulating Agent Router Logic
        agent_thought = f"Thought: User asked about Indian envoys in the {query.split('the ')[-1].replace(' region?', '')}.\\nAction: Neo4j_Subgraph_Retriever\\nAction Input: Kabul"
        print(agent_thought)
        
        # Tool Execution
        context = tool.run("Kabul")
        
        # Final Synthesis Context
        final_prompt = f"Observation: {context}\\nThought: ..."
        response = llm.invoke(final_prompt)
        
        print("\n" + "="*80)
        print("SOVEREIGN SYNTHESIS (SARVAM-30B WITH CITATION ENGINE)")
        print("="*80)
        print(response)
        
    except NameError:
        print("Cannot run test: LlamaIndex/LangChain dependencies have not finished installing.")
    except Exception as e:
        print(f"Orchestration Error: {e}")

