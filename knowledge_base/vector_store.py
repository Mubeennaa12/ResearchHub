"""
Wrapper around Qdrant vector database and SentenceTransformers for local embedding.
Supports both local file persistence and external server instances.
"""

import os
import logging
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.errors import UnexpectedResponse
from config import settings
from knowledge_base.chunker import Chunk

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, path: str = None, url: str = None):
        # 1. Load the SentenceTransformer model locally
        logger.info(f"Loading local SentenceTransformer model: {settings.embedding_model}")
        self.model = SentenceTransformer(settings.embedding_model)
        
        # 2. Connect to Qdrant
        qdrant_url = url or settings.vector_db_url
        qdrant_path = path or settings.vector_db_path

        if qdrant_url:
            logger.info(f"Connecting to Qdrant server at: {qdrant_url}")
            self.client = QdrantClient(url=qdrant_url)
        else:
            # Ensure local storage path directory exists
            os.makedirs(qdrant_path, exist_ok=True)
            logger.info(f"Connecting to local file Qdrant store at: {qdrant_path}")
            self.client = QdrantClient(path=qdrant_path)

        self.collection_name = "ai_research_workspace"
        self._ensure_collection_exists()

    def _ensure_collection_exists(self) -> None:
        """Create collection if it doesn't already exist."""
        # BAAI/bge-small-en-v1.5 has size 384. all-MiniLM-L6-v2 has size 384.
        # Let's dynamically get the vector size of the model.
        vector_size = self.model.get_sentence_embedding_dimension()
        
        try:
            collections = self.client.get_collections()
            exist = any(c.name == self.collection_name for c in collections.collections)
            if not exist:
                logger.info(f"Creating vector collection '{self.collection_name}' with size {vector_size}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=vector_size,
                        distance=qmodels.Distance.COSINE
                    )
                )
        except Exception as e:
            logger.error(f"Failed to verify/create Qdrant collection: {e}")

    def upsert(self, chunks: list[Chunk], workspace_id: str) -> None:
        """Embeds text chunks and uploads to Qdrant collection under specified workspace_id."""
        if not chunks:
            return

        texts = [chunk.text for chunk in chunks]
        logger.info(f"Embedding {len(chunks)} chunks locally...")
        embeddings = self.model.encode(texts, show_progress_bar=False).tolist()

        points = []
        for chunk, vector in zip(chunks, embeddings):
            payload = {
                "document_id": chunk.document_id,
                "text": chunk.text,
                "source_type": chunk.source_type,
                "workspace_id": workspace_id
            }
            # Add metadata keys to payload
            payload.update(chunk.metadata)

            points.append(
                qmodels.PointStruct(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload=payload
                )
            )

        logger.info(f"Uploading points to Qdrant collection '{self.collection_name}'")
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def query(self, query_text: str, workspace_id: str, top_k: int = 8) -> list[Chunk]:
        """Embeds query text and returns top_k matching chunks filtered by workspace_id."""
        query_vector = self.model.encode(query_text).tolist()

        # Workspace ID filter to keep search context isolated
        query_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="workspace_id",
                    match=qmodels.MatchValue(value=workspace_id)
                )
            ]
        )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k
        )

        chunks = []
        for hit in results:
            payload = hit.payload
            document_id = payload.pop("document_id", "")
            text = payload.pop("text", "")
            source_type = payload.pop("source_type", "")
            # remaining payload details are metadata
            chunks.append(Chunk(
                chunk_id=str(hit.id),
                document_id=document_id,
                text=text,
                source_type=source_type,
                metadata=payload
            ))
            
        return chunks

    def delete_by_source(self, source_id: str) -> None:
        """Removes all indexed chunks associated with document_id."""
        logger.info(f"Deleting chunks for document: {source_id}")
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="source_id",
                            match=qmodels.MatchValue(value=source_id)
                        )
                    ]
                )
            )
        )
