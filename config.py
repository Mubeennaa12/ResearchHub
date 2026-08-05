"""
Central configuration. Load everything from environment variables so
nothing sensitive is hardcoded.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # LLM Configuration
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3")

    # Local Embeddings model
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

    # Databases
    vector_db_path: str = os.getenv("VECTOR_DB_PATH", "./data/vector_store")
    vector_db_url: str = os.getenv("VECTOR_DB_URL", "")  # e.g., "http://localhost:6333" for Docker Qdrant
    
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/sqlite.db")
    redis_url: str = os.getenv("REDIS_URL", "")  # empty means local in-memory fallback

    graph_db_uri: str = os.getenv("GRAPH_DB_URI", "bolt://localhost:7687")
    graph_db_user: str = os.getenv("GRAPH_DB_USER", "neo4j")
    graph_db_password: str = os.getenv("GRAPH_DB_PASSWORD", "")

    # API keys and integration tokens
    web_search_api_key: str = os.getenv("WEB_SEARCH_API_KEY", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")

    # RAG Settings
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))

    max_retrieval_loops: int = int(os.getenv("MAX_RETRIEVAL_LOOPS", "3"))
    top_k_vector: int = int(os.getenv("TOP_K_VECTOR", "8"))
    top_k_graph: int = int(os.getenv("TOP_K_GRAPH", "5"))
    top_k_web: int = int(os.getenv("TOP_K_WEB", "5"))

    # Observability
    langchain_tracing_v2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    langchain_api_key: str = os.getenv("LANGCHAIN_API_KEY", "")


settings = Settings()
