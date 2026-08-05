"""
Context Merger. normalizes, deduplicates, ranks, and formats outputs from Vector, Graph, and Web searches.
"""

import logging
from typing import Any
from knowledge_base.chunker import Chunk

logger = logging.getLogger(__name__)


class MergedContext:
    def __init__(self, items: list[dict[str, Any]] = None):
        # Each item: {"text": str, "source": str, "source_type": str, "metadata": dict, "score": float}
        self.items = items or []

    def to_prompt_context(self) -> str:
        """Renders chunks into a formatted block the LLM can reference."""
        formatted_blocks = []
        for i, item in enumerate(self.items):
            idx = i + 1
            source_type = item.get("source_type", "unknown")
            source_name = item.get("source", "Unknown Source")
            
            # Extract additional positional coordinates where available
            coord_str = ""
            meta = item.get("metadata", {})
            if source_type == "pdf" and "page" in meta:
                coord_str = f", Page: {meta['page']}"
            elif source_type == "youtube" and "start_seconds" in meta:
                # Convert seconds to minutes/seconds
                sec = int(meta["start_seconds"])
                coord_str = f", Timestamp: {sec // 60}:{sec % 60:02d}"
            elif source_type == "github" and "file_path" in meta:
                coord_str = f", File: {meta['file_path']}"
                
            text = item.get("text", "").strip()
            formatted_blocks.append(
                f"[{idx}] (Type: {source_type}, Source: {source_name}{coord_str})\n{text}"
            )
        return "\n\n".join(formatted_blocks)


class ContextMerger:
    def _calculate_lexical_score(self, text: str, query: str) -> float:
        """Simple TF-based lexical term matching score to help rerank."""
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        if not query_words:
            return 0.0
        
        text_lower = text.lower()
        score = 0.0
        for word in query_words:
            count = text_lower.count(word)
            score += count * (1.0 / len(word))
        return score

    def merge(
        self,
        query: str,
        vector_results: list[Chunk],
        graph_results: list[dict],
        web_results: list[dict]
    ) -> MergedContext:
        """
        Normalizes and merges outputs from vector, graph, and web searches,
        deduplicating by document source and ranking by lexical overlap.
        """
        normalized_items = []
        seen_identifiers = set()

        # 1. Normalize Vector results
        for chunk in vector_results:
            source_name = chunk.metadata.get("title") or chunk.document_id
            # Deduplicate by document + text hash
            unique_id = hashlib_text = f"{chunk.document_id}_{hash(chunk.text[:50])}"
            
            if unique_id not in seen_identifiers:
                seen_identifiers.add(unique_id)
                normalized_items.append({
                    "text": chunk.text,
                    "source": source_name,
                    "source_type": chunk.source_type,
                    "metadata": chunk.metadata,
                    "score": 1.0  # Base rank
                })

        # 2. Normalize Graph results
        for entity in graph_results:
            ent_id = entity.get("id")
            ent_type = entity.get("type", "Entity")
            ent_rel = entity.get("relationship", "linked")
            
            # Build text representation from properties
            properties = {k: v for k, v in entity.items() if k not in ["id", "type", "relationship"]}
            text_desc = f"Graph Entity ({ent_type}) [{ent_id}]: " + ", ".join(f"{k}={v}" for k, v in properties.items())
            
            unique_id = f"graph_{ent_id}"
            if unique_id not in seen_identifiers:
                seen_identifiers.add(unique_id)
                normalized_items.append({
                    "text": text_desc,
                    "source": f"Knowledge Graph ({ent_rel})",
                    "source_type": "graph",
                    "metadata": {"entity_id": ent_id, "entity_type": ent_type},
                    "score": 0.8
                })

        # 3. Normalize Web results
        for web_hit in web_results:
            url = web_hit.get("url", "")
            unique_id = f"web_{url}" if url else f"web_{hash(web_hit.get('snippet', ''))}"
            
            if unique_id not in seen_identifiers:
                seen_identifiers.add(unique_id)
                normalized_items.append({
                    "text": web_hit.get("snippet", "") or web_hit.get("text", ""),
                    "source": web_hit.get("title", "") or url or "Web Result",
                    "source_type": "web",
                    "metadata": {"url": url},
                    "score": 0.9
                })

        # 4. Rerank based on query overlap + base scores
        for item in normalized_items:
            lexical = self._calculate_lexical_score(item["text"], query)
            item["score"] = item["score"] * (1.0 + lexical)

        # Sort by relevance score desc
        sorted_items = sorted(normalized_items, key=lambda x: x["score"], reverse=True)

        # Truncate context to keep LLM context budget reasonable (e.g. top 15 results)
        return MergedContext(items=sorted_items[:15])
