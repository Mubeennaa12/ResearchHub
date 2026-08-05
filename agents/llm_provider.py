import json
import logging
import requests
from config import settings

logger = logging.getLogger(__name__)


class LLMProvider:
    """
    Unified interface to interact with various LLM providers:
    Gemini, OpenAI, Anthropic, and Ollama.
    """

    @staticmethod
    def call(
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = False
    ) -> str:
        provider = settings.llm_provider

        try:
            if provider == "gemini":
                return LLMProvider._call_gemini(prompt, system_prompt, temperature, max_tokens, json_mode)
            elif provider == "openai":
                return LLMProvider._call_openai(prompt, system_prompt, temperature, max_tokens, json_mode)
            elif provider == "anthropic":
                return LLMProvider._call_anthropic(prompt, system_prompt, temperature, max_tokens, json_mode)
            elif provider == "ollama":
                return LLMProvider._call_ollama(prompt, system_prompt, temperature, max_tokens, json_mode)
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        except Exception as e:
            logger.error(f"Error calling LLM provider '{provider}': {e}")
            raise

    @staticmethod
    def _call_gemini(prompt: str, system_prompt: str, temperature: float, max_tokens: int, json_mode: bool) -> str:
        # Import dynamically to ensure the library is only needed if this provider is chosen
        from google import genai
        from google.genai import types

        api_key = settings.gemini_api_key
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables.")

        client = genai.Client(api_key=api_key)
        
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt if system_prompt else None,
            response_mime_type="application/json" if json_mode else "text/plain"
        )

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=config
        )
        return response.text

    @staticmethod
    def _call_openai(prompt: str, system_prompt: str, temperature: float, max_tokens: int, json_mode: bool) -> str:
        from openai import OpenAI

        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment variables.")

        client = OpenAI(api_key=api_key)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response_format = {"type": "json_object"} if json_mode else None

        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format
        )
        return response.choices[0].message.content

    @staticmethod
    def _call_anthropic(prompt: str, system_prompt: str, temperature: float, max_tokens: int, json_mode: bool) -> str:
        from anthropic import Anthropic

        api_key = settings.anthropic_api_key
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set in environment variables.")

        client = Anthropic(api_key=api_key)

        # Note: Anthropic doesn't support a direct json_mode switch parameter like OpenAI in their basic API,
        # so we rely on prompt engineering if json_mode is requested, or pass standard parameters.
        if json_mode:
            prompt = prompt + "\nReturn the response strictly as a JSON object."

        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            system=system_prompt if system_prompt else None,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        return "".join(block.text for block in response.content if block.type == "text")

    @staticmethod
    def _call_ollama(prompt: str, system_prompt: str, temperature: float, max_tokens: int, json_mode: bool) -> str:
        url = f"{settings.ollama_base_url}/api/chat"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.ollama_model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            },
            "stream": False
        }

        if json_mode:
            payload["format"] = "json"

        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["message"]["content"]
