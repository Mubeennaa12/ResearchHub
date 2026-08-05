"""
Graph Search retriever branch. Extracts entity names from queries and returns connected nodes.
"""

import json
import logging
from knowledge_base.graph_store import GraphStore
from agents.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class GraphSearchAgent:
    def __init__(self, store: GraphStore, top_k: int):
        self.store = store
        self.top_k = top_k

    def search(self, query: str) -> list[dict]:
        """
        Uses LLM to extract entity identifiers from the user query,
        then queries the graph database for related connections.
        """
        # Step 1: Extract candidate entity IDs from the query
        system_prompt = (
            "You are a entity extraction module. Given a search query, "
            "identify any research entities (methods, papers, authors, repos, datasets, models) mentioned. "
            "Return a JSON list of strings representing the key entity IDs/slugs. "
            "Example input: 'Which datasets did SegFormer use?' -> Output: ['segformer']"
        )
        
        try:
            response = LLMProvider.call(
                prompt=f"Extract entities from: '{query}'",
                system_prompt=system_prompt,
                temperature=0.1,
                json_mode=True
            )
            
            # Simple JSON parse
            try:
                entity_ids = json.loads(response)
            except Exception:
                clean_response = response.strip().strip("```").strip("json").strip()
                entity_ids = json.loads(clean_response)
                
            if not isinstance(entity_ids, list):
                entity_ids = []
        except Exception as e:
            logger.warning(f"Failed to parse search entities from query: {e}")
            entity_ids = []

        # Step 2: Query GraphStore for each extracted entity ID
        related_entities = []
        seen_ids = set()
        
        for ent_id in entity_ids:
            ent_id_slug = ent_id.lower().strip()
            if not ent_id_slug:
                continue
                
            try:
                hits = self.store.query_related(ent_id_slug, relationship=None, top_k=self.top_k)
                for hit in hits:
                    hit_id = hit.get("id")
                    if hit_id and hit_id not in seen_ids:
                        seen_ids.add(hit_id)
                        related_entities.append(hit)
            except Exception as e:
                logger.error(f"Error querying graph database for '{ent_id_slug}': {e}")

        return related_entities
