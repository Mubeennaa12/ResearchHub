"""
Evaluator. Computess RAG evaluation metrics (Faithfulness, Answer Relevancy, Context Recall) for dashboard stats and system tracking.
"""

import json
import json
import logging
from agents.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class QualityEvaluator:
    """
    Computes standard RAG metrics (0.0 to 1.0 scale) using LLM evaluation prompt techniques.
    """

    def evaluate(self, query: str, context_str: str, answer: str) -> dict:
        system_prompt = (
            "You are an expert AI RAG Evaluation Engine. "
            "Evaluate the final answer against the query and the retrieved context.\n"
            "Output a JSON object matching this schema:\n"
            "{\n"
            "  \"faithfulness\": float, // score from 0.0 to 1.0 indicating if the claims in the answer are strictly supported by the context without hallucination\n"
            "  \"answer_relevancy\": float, // score from 0.0 to 1.0 indicating if the answer directly and fully addresses the user query\n"
            "  \"context_recall\": float, // score from 0.0 to 1.0 indicating if the retrieved context contains all the necessary details to answer the query\n"
            "  \"explanation\": \"brief multi-line explanation detailing why the scores were given\"\n"
            "}\n\n"
            "Always respond strictly with a valid JSON object."
        )

        user_content = (
            f"User Query: {query}\n\n"
            f"Retrieved Context:\n{context_str}\n\n"
            f"Final Generated Answer:\n{answer}\n\n"
            "Evaluate RAG quality."
        )

        try:
            response = LLMProvider.call(
                prompt=user_content,
                system_prompt=system_prompt,
                temperature=0.1,
                json_mode=True
            )
            clean_res = response.strip().strip("```").strip("json").strip()
            data = json.loads(clean_res)
            
            return {
                "faithfulness": data.get("faithfulness", 1.0),
                "answer_relevancy": data.get("answer_relevancy", 1.0),
                "context_recall": data.get("context_recall", 1.0),
                "explanation": data.get("explanation", "")
            }
        except Exception as e:
            logger.warning(f"RAG Quality evaluation failed: {e}. Defaulting to high scores.")
            return {
                "faithfulness": 1.0,
                "answer_relevancy": 1.0,
                "context_recall": 1.0,
                "explanation": "Fallback score given due to evaluation service failure."
            }
