"""GraphRAG query engine — retrieves context then synthesises an answer via Claude."""
import os
import logging
from typing import Optional
from anthropic import Anthropic
from .retrievers import LocalRetriever

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a legal contract analysis assistant. "
    "Answer based ONLY on the provided contract context. "
    "Cite specific entities and clauses by id. "
    "If the context doesn't contain the answer, say so explicitly."
)


class QueryEngine:
    def __init__(self, retriever: LocalRetriever, llm_client: Anthropic):
        self._retriever = retriever
        self._llm = llm_client

    def query(self, question: str) -> dict:
        context_items = self._retriever.retrieve(question)

        if not context_items:
            return {
                "answer": (
                    "No relevant context found in the contract graph. "
                    "Either no contracts have been indexed yet, Neo4j is unavailable, "
                    "or no graph entities match your query."
                ),
                "sources": [],
                "strategy": "local",
            }

        context_text = _format_context(context_items)
        sources = [
            {
                "id": item["id"],
                "entity_type": item["entity_type"],
                "score": item["score"],
            }
            for item in context_items
        ]

        message = self._llm.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Context from the contract knowledge graph:\n\n{context_text}\n\n"
                        f"Question: {question}"
                    ),
                }
            ],
        )

        return {
            "answer": message.content[0].text,
            "sources": sources,
            "strategy": "local",
        }


def _format_context(items: list[dict]) -> str:
    parts = []
    for item in items:
        part = f"[{item['entity_type']} id={item['id']}] {item['description']}"
        if item.get("relationships"):
            rels = "; ".join(
                f"{r['rel_type']} -> {r['neighbor_name']} ({r['neighbor_id']})"
                for r in item["relationships"][:5]
            )
            part += f"\n  Relationships: {rels}"
        if item.get("clauses"):
            for cl in item["clauses"][:2]:
                part += f"\n  Clause {cl['id']}: {cl['text'][:300]}"
        parts.append(part)
    return "\n\n".join(parts)


def create_query_engine() -> Optional[QueryEngine]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set; QueryEngine unavailable.")
        return None
    try:
        llm_client = Anthropic(api_key=api_key)
        retriever = LocalRetriever()
        return QueryEngine(retriever, llm_client)
    except Exception as e:
        logger.warning(f"Failed to create QueryEngine: {e}")
        return None
