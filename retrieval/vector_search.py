"""
Implements the Vector Search retriever branch.
"""

from knowledge_base.vector_store import VectorStore
from knowledge_base.chunker import Chunk


class VectorSearchAgent:
    def __init__(self, store: VectorStore, top_k: int):
        self.store = store
        self.top_k = top_k

    def search(self, query: str, workspace_id: str) -> list[Chunk]:
        """
        Embeds the query and searches the vector store, filtering by workspace_id.
        """
        return self.store.query(query, workspace_id=workspace_id, top_k=self.top_k)
