"""
Shared base for agents. Wraps the LLMProvider call, making model requests unified
across all specialized roles.
"""

from agents.llm_provider import LLMProvider


class BaseAgent:
    system_prompt: str = ""

    def call(
        self,
        user_content: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = False
    ) -> str:
        """
        Executes the agent's LLM call with its configured system prompt.
        """
        return LLMProvider.call(
            prompt=user_content,
            system_prompt=self.system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode
        )
