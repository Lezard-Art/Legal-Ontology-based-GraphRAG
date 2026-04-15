"""GraphRAG retrieval strategies — local (entity-centric) search over Neo4j."""
import logging
from .neo4j_client import neo4j_client
from .embeddings import embedding_service

logger = logging.getLogger(__name__)


class LocalRetriever:
    def retrieve(self, question: str, top_k: int = 10) -> list[dict]:
        if neo4j_client is None or embedding_service is None:
            return []

        try:
            query_embedding = embedding_service.embed_text(question)
        except Exception as e:
            logger.warning(f"Failed to embed query: {e}")
            return []

        results = []
        try:
            with neo4j_client.get_session() as session:
                # Vector similarity search over all :Entity nodes
                vector_rows = session.run(
                    "CALL db.index.vector.queryNodes('entity_embeddings', $top_k, $embedding) "
                    "YIELD node, score "
                    "RETURN node, score",
                    top_k=top_k,
                    embedding=query_embedding,
                )
                hits = [(r["node"], r["score"]) for r in vector_rows]

                for node, score in hits:
                    node_id = node.get("id")
                    if not node_id:
                        continue
                    entity_type = node.get("entity_type", "Unknown")

                    # 1–2-hop neighbourhood traversal (capped to avoid runaway)
                    hop_rows = session.run(
                        "MATCH (n:Entity {id: $id})-[r*1..2]-(m) "
                        "RETURN type(r[0]) AS rel_type, "
                        "labels(m) AS m_labels, "
                        "m.id AS m_id, "
                        "m.name AS m_name, "
                        "m.label AS m_label, "
                        "m.description AS m_desc, "
                        "m.text AS m_text "
                        "LIMIT 50",
                        id=node_id,
                    )

                    relationships: list[dict] = []
                    clauses: list[dict] = []
                    seen_clause_ids: set[str] = set()

                    for rec in hop_rows:
                        rel_type = rec["rel_type"]
                        m_labels = rec["m_labels"] or []
                        m_id = rec["m_id"]
                        m_text = rec["m_text"]
                        neighbor_name = (
                            rec["m_name"]
                            or rec["m_label"]
                            or rec["m_desc"]
                            or ""
                        )

                        relationships.append({
                            "rel_type": rel_type,
                            "neighbor_id": m_id,
                            "neighbor_labels": m_labels,
                            "neighbor_name": neighbor_name,
                        })

                        if "Clause" in m_labels and m_text and m_id not in seen_clause_ids:
                            clauses.append({"id": m_id, "text": m_text})
                            seen_clause_ids.add(m_id)

                    description = (
                        node.get("description")
                        or node.get("text")
                        or node.get("name")
                        or node.get("label")
                        or node.get("description_text")
                        or ""
                    )

                    results.append({
                        "entity_type": entity_type,
                        "id": node_id,
                        "description": description,
                        "relationships": relationships,
                        "clauses": clauses,
                        "score": score,
                    })

        except Exception as e:
            logger.warning(f"LocalRetriever.retrieve failed: {e}")
            return []

        return results
