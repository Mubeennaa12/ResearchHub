"""
Entity/relationship graph store mapping papers, methods, datasets, models, and repositories.
Includes a fully compliant in-memory fallback if the Neo4j database is offline.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class GraphStore:
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.use_fallback = False
        
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Check connection
            self.driver.verify_connectivity()
            logger.info("Connected to Neo4j Graph Database successfully.")
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}. Falling back to In-Memory GraphStore.")
            self.use_fallback = True
            self.nodes = {}  # node_id -> {"type": type, "properties": properties}
            self.edges = []  # list of {"from_id": from, "to_id": to, "relationship": rel}

    def close(self):
        if not self.use_fallback and hasattr(self, "driver"):
            self.driver.close()

    def add_entity(self, entity_type: str, entity_id: str, properties: dict[str, Any]) -> None:
        """Adds or updates a node in the graph."""
        if self.use_fallback:
            self.nodes[entity_id] = {
                "type": entity_type,
                "properties": properties
            }
            logger.info(f"[Fallback Graph] Added entity {entity_type} ({entity_id})")
            return

        cypher = (
            f"MERGE (n:{entity_type} {{id: $entity_id}}) "
            "ON CREATE SET n += $properties "
            "ON MATCH SET n += $properties"
        )
        try:
            with self.driver.session() as session:
                session.run(cypher, entity_id=entity_id, properties=properties)
        except Exception as e:
            logger.error(f"Failed to add entity to Neo4j: {e}")

    def add_relationship(self, from_id: str, to_id: str, relationship: str) -> None:
        """Creates a directed relationship between two nodes."""
        if self.use_fallback:
            self.edges.append({
                "from_id": from_id,
                "to_id": to_id,
                "relationship": relationship
            })
            logger.info(f"[Fallback Graph] Created relationship {from_id} -[{relationship}]-> {to_id}")
            return

        # Note: Cypher query matching node IDs dynamically
        cypher = (
            "MATCH (a {id: $from_id}) "
            "MATCH (b {id: $to_id}) "
            f"MERGE (a)-[r:{relationship}]->(b)"
        )
        try:
            with self.driver.session() as session:
                session.run(cypher, from_id=from_id, to_id=to_id)
        except Exception as e:
            logger.error(f"Failed to create Neo4j relationship '{relationship}': {e}")

    def query_related(self, entity_id: str, relationship: str | None = None, top_k: int = 5) -> list[dict]:
        """Queries neighbors linked to the entity_id."""
        if self.use_fallback:
            results = []
            for edge in self.edges:
                matched = False
                target_id = None
                
                # Check directional match
                if edge["from_id"] == entity_id:
                    target_id = edge["to_id"]
                    matched = True
                elif edge["to_id"] == entity_id:
                    target_id = edge["from_id"]
                    matched = True

                if matched:
                    # Filter relationship type if provided
                    if relationship and edge["relationship"] != relationship:
                        continue
                        
                    if target_id in self.nodes:
                        node_info = self.nodes[target_id]
                        results.append({
                            "id": target_id,
                            "type": node_info["type"],
                            "relationship": edge["relationship"],
                            **node_info["properties"]
                        })
                        if len(results) >= top_k:
                            break
            return results

        cypher = (
            "MATCH (n {id: $entity_id})-[r]-(related) "
            "WHERE $relationship IS NULL OR type(r) = $relationship "
            "RETURN related, type(r) as rel_type LIMIT $top_k"
        )
        try:
            with self.driver.session() as session:
                result = session.run(cypher, entity_id=entity_id, relationship=relationship, top_k=top_k)
                nodes = []
                for record in result:
                    node = record["related"]
                    nodes.append({
                        "id": node.get("id"),
                        "type": list(node.labels)[0] if node.labels else "Unknown",
                        "relationship": record["rel_type"],
                        **dict(node)
                    })
                return nodes
        except Exception as e:
            logger.error(f"Neo4j query failed: {e}")
            return []

    def entity_extraction_pipeline(self, chunk_text: str) -> list[dict[str, Any]]:
        """
        Extracts key research nodes and relationships from text using the LLM provider.
        """
        # Defer import to prevent circular dependency
        from agents.llm_provider import LLMProvider

        system_prompt = (
            "You are an expert NLP extraction engine. "
            "Analyze the text and extract entities and relationships. "
            "Return JSON in this format:\n"
            "{\n"
            "  \"entities\": [\n"
            "    {\"type\": \"Paper|Method|Dataset|Model|Repository|Author\", \"id\": \"unique_slug\", \"properties\": {\"name\": \"...\", \"title\": \"...\"}}\n"
            "  ],\n"
            "  \"relationships\": [\n"
            "    {\"from_id\": \"entity_slug_1\", \"to_id\": \"entity_slug_2\", \"type\": \"CITES|TRAINED_ON|IMPLEMENTED_IN|COMPARED_WITH|AUTHORED_BY\"}\n"
            "  ]\n"
            "}"
        )
        
        prompt = f"Extract from text:\n\n{chunk_text}"
        try:
            response = LLMProvider.call(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                json_mode=True
            )
            data = json = {}
            try:
                data = json.loads(response)
            except Exception:
                # Basic parsing extraction cleaning
                # Remove markdown code fence if present
                clean_response = response.strip().strip("```").strip("json").strip()
                data = json.loads(clean_response)
            return data
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            return {"entities": [], "relationships": []}
