"""
Reasoning Agent. Evaluates if the collected context is sufficient to answer the query.
"""

import json
import logging
from dataclasses import dataclass
from agents.base_agent import BaseAgent
from retrieval.context_merger import MergedContext

logger = logging.getLogger(__name__)


@dataclass
class ReasoningResult:
    sufficient: bool
    reasoning: str
    missing_info: str | None = None


class ReasoningAgent(BaseAgent):
    system_prompt = (
        "You are an AI Research Reasoning Agent. "
        "Your task is to review the user's query and the current retrieved context, "
        "and determine if there is enough information to fully and high-fidelity answer the query. "
        "You must output a JSON object matching this schema:\n"
        "{\n"
        "  \"sufficient\": bool,\n"
        "  \"reasoning\": \"brief explanation of your decision\",\n"
        "  \"missing_info\": \"a specific search query to find the missing details, or null if sufficient is true\"\n"
        "}\n\n"
        "Guidelines:\n"
        "- If the retrieved text lacks the direct definitions, results, or data requested, set 'sufficient' to false.\n"
        "- The 'missing_info' query should target specific facts, files, or papers missing (e.g. 'SegFormer model parameters config table').\n"
        "- Always respond strictly with a valid JSON object."
    )

    def evaluate(self, query: str, context: MergedContext) -> ReasoningResult:
        """
        Evaluates context sufficiency.
        """
        context_str = context.to_prompt_context()
        if not context_str.strip():
            return ReasoningResult(
                sufficient=False,
                reasoning="No context retrieved yet.",
                missing_info=query
            )

        user_content = f"Query: {query}\n\nRetrieved Context:\n{context_str}\n\nEvaluate sufficiency."
        
        try:
            response = self.call(
                user_content=user_content,
                temperature=0.1,
                json_mode=True
            )
            clean_res = response.strip().strip("```").strip("json").strip()
            data = json.loads(clean_res)
            
            return ReasoningResult(
                sufficient=data.get("sufficient", True),
                reasoning=data.get("reasoning", ""),
                missing_info=data.get("missing_info")
            )
        except Exception as e:
            logger.error(f"Reasoning evaluation failed: {e}. Defaulting to sufficient.")
            return ReasoningResult(
                sufficient=True,
                reasoning="Fallback due to processing error."
            )
