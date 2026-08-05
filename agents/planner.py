"""
Planner Agent. Decides which retrieval routes to call and selects the specialized agent node.
"""

import json
import logging
from dataclasses import dataclass
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class RetrievalPlan:
    use_vector: bool
    use_graph: bool
    use_web: bool
    vector_query: str
    graph_query: str
    web_query: str
    selected_agent: str  # "github" | "paper" | "code" | "report" | "qa"


class PlannerAgent(BaseAgent):
    system_prompt = (
        "You are an AI Research Retrieval Planner. "
        "Your task is to analyze user queries and make routing and retrieval planning decisions. "
        "You must output a JSON object matching this schema:\n"
        "{\n"
        "  \"use_vector\": bool,\n"
        "  \"use_graph\": bool,\n"
        "  \"use_web\": bool,\n"
        "  \"vector_query\": \"semantic query to run against vector database, or empty if false\",\n"
        "  \"graph_query\": \"entity slug to search in knowledge graph, or empty if false\",\n"
        "  \"web_query\": \"web search terms to check, or empty if false\",\n"
        "  \"selected_agent\": \"github|paper|code|report|qa\"\n"
        "}\n\n"
        "Specialized Agent Routing Guidelines:\n"
        "- Choose 'github' for repository layouts, AST, files, class/method, and architecture questions.\n"
        "- Choose 'paper' for paper comparisons, methodologies, dataset, model details, and literature reviews.\n"
        "- Choose 'code' for writing implementation code, APIs (FastAPI), SQL tables, and algorithms.\n"
        "- Choose 'report' for outlining presentation decks, roadmaps, literature synthesis, and study notes.\n"
        "- Choose 'qa' for general questions.\n\n"
        "Always respond strictly with a valid JSON object."
    )

    def plan(self, query: str, workspace_facts: list[str] = None) -> RetrievalPlan:
        """
        Creates a structured RetrievalPlan from the query.
        """
        facts_block = ""
        if workspace_facts:
            facts_block = "\nKnown user preferences & workspace context:\n- " + "\n- ".join(workspace_facts)

        user_content = f"Query: {query}{facts_block}\n\nCreate a retrieval and agent plan."
        
        try:
            response = self.call(
                user_content=user_content,
                temperature=0.1,
                json_mode=True
            )
            # Clean possible markdown formatting
            clean_res = response.strip().strip("```").strip("json").strip()
            data = json.loads(clean_res)
            
            return RetrievalPlan(
                use_vector=data.get("use_vector", True),
                use_graph=data.get("use_graph", False),
                use_web=data.get("use_web", False),
                vector_query=data.get("vector_query", query),
                graph_query=data.get("graph_query", ""),
                web_query=data.get("web_query", ""),
                selected_agent=data.get("selected_agent", "qa").lower()
            )
        except Exception as e:
            logger.error(f"Failed to generate retrieval plan: {e}. Using safe defaults.")
            # Safe default fallback
            return RetrievalPlan(
                use_vector=True,
                use_graph=False,
                use_web=False,
                vector_query=query,
                graph_query="",
                web_query="",
                selected_agent="qa"
            )
