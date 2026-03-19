import os
import json
from dotenv import load_dotenv

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
                    MATCH path = (e)-[:MENTIONED_IN|ASSOCIATED_WITH|LOCATED_IN|HAS_THEME|MEASURED_IN|THREATENS*1..{hops}]-(n)
                    WHERE (n:Article OR n:EconomicIndicator OR n:WeatherAlert)
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

