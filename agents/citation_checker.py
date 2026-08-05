"""
Citation Checker Agent. Verifies every cited claim in the draft answer against the source context.
"""

import json
import logging
from dataclasses import dataclass
from agents.base_agent import BaseAgent
from retrieval.context_merger import MergedContext

logger = logging.getLogger(__name__)


@dataclass
class CitationCheckResult:
    verified_answer: str
    flagged_claims: list[str]


class CitationCheckerAgent(BaseAgent):
    system_prompt = (
        "You are an AI Research Citation Verification Agent. "
        "Your task is to review a Draft Answer containing inline [n] citation markers, "
        "and compare it to the numbered list of Context Chunks. "
        "You must output a JSON object matching this schema:\n"
        "{\n"
        "  \"verified_answer\": \"the updated answer with corrected and verified citations\",\n"
        "  \"flagged_claims\": [\n"
        "    \"description of any claims that were removed or modified because they were not supported by the referenced chunks\"\n"
        "  ]\n"
        "}\n\n"
        "Validation Rules:\n"
        "1. For each citation marker [n] in the draft, read Context Chunk [n] to ensure it supports the claim.\n"
        "2. If Context Chunk [n] does NOT support the claim, modify the claim to reflect the truth or remove it, and log it in 'flagged_claims'.\n"
        "3. Ensure the markdown structure is fully preserved in the verified_answer.\n"
        "4. Always respond strictly with a valid JSON object."
    )

    def check(self, draft_answer: str, context: MergedContext) -> CitationCheckResult:
        """
        Verifies citations in draft answer and outputs a cleaned verified answer.
        """
        context_str = context.to_prompt_context()
        
        user_content = (
            f"Draft Answer to Verify:\n{draft_answer}\n\n"
            f"Reference Context Chunks:\n{context_str}\n\n"
            "Perform citation verification check."
        )

        try:
            response = self.call(
                user_content=user_content,
                temperature=0.1,
                json_mode=True
            )
            clean_res = response.strip().strip("```").strip("json").strip()
            data = json.loads(clean_res)
            
            return CitationCheckResult(
                verified_answer=data.get("verified_answer", draft_answer),
                flagged_claims=data.get("flagged_claims", [])
            )
        except Exception as e:
            logger.error(f"Citation verification failed: {e}. Returning original draft.")
            return CitationCheckResult(
                verified_answer=draft_answer,
                flagged_claims=[]
            )
