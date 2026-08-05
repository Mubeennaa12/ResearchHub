"""
Answer Generator Agent. Produces a draft answer with inline citation markers grounded strictly in context.
"""

from agents.base_agent import BaseAgent
from retrieval.context_merger import MergedContext


class AnswerGeneratorAgent(BaseAgent):
    system_prompt = (
        "You are an AI Research Answer Generator. "
        "Your task is to answer the user's query by summarizing, comparing, or explaining code "
        "using ONLY the provided Context Chunks. "
        "You must cite your sources inline using [n] markers matching the numbered Context Chunks.\n\n"
        "Rules:\n"
        "1. Ground every statement in the context. Do not make claims that cannot be found in the provided sources.\n"
        "2. Add a citation marker [n] next to every claim that references a source chunk.\n"
        "3. If the context does not contain enough information to fully support a claim, state that clearly.\n"
        "4. Output in clean Markdown format."
    )

    def generate(self, query: str, context: MergedContext, workspace_facts: list[str] = None) -> str:
        """
        Generates the draft answer containing inline [n] citation markers.
        """
        context_str = context.to_prompt_context()
        
        prompt = f"User Query: {query}\n\nContext Chunks:\n{context_str}"
        
        if workspace_facts:
            prompt += "\n\nUser preferences and workspace facts to consider:\n- " + "\n- ".join(workspace_facts)
            
        prompt += "\n\nGenerate draft response:"
        
        return self.call(prompt=prompt, temperature=0.2)
