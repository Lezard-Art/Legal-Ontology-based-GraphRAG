"""Embedding service — wraps OpenAI embeddings for entity and query text."""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Description templates used to turn entity property dicts into embeddable text.
# These match the templates from implementation.md § 2.2.
_TEMPLATES = {
    "Contract": lambda p: (
        f"{p.get('name', '')}: {p.get('governing_law', 'unknown law')} contract "
        f"effective {p.get('effective_date', 'unknown date')}"
    ),
    "Party": lambda p: f"{p.get('name', '')}: {p.get('type', '')}",
    "Role": lambda p: f"Role: {p.get('label', '')}",
    "Obligation": lambda p: (
        f"{p.get('debtor_role', '?')} must {p.get('description', '')} "
        f"for {p.get('creditor_role', '?')}"
    ),
    "Power": lambda p: (
        f"{p.get('creditor_role', '?')} may {p.get('description', '')}. "
        f"Trigger: {p.get('trigger_condition', 'none')}"
    ),
    "Clause": lambda p: f"{p.get('section_number', '?')}: {p.get('text', '')}",
    "Constraint": lambda p: (
        f"Constraint: {p.get('description', '')} — {p.get('expression', '')}"
    ),
    "Asset": lambda p: f"Asset: {p.get('name', '')} — {p.get('description', '')}",
    "LegalPosition": lambda p: (
        f"{p.get('position_type', '')} held by {p.get('holder_role', '?')} "
        f"against {p.get('counter_role', '?')}: {p.get('description', '')}"
    ),
}


class EmbeddingService:
    def __init__(self, model: str = "text-embedding-3-small"):
        from openai import OpenAI
        self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self._model = model

    def embed_text(self, text: str) -> list[float]:
        cleaned = text.replace("\n", " ").strip() or " "
        response = self._client.embeddings.create(input=[cleaned], model=self._model)
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        cleaned = [t.replace("\n", " ").strip() or " " for t in texts]
        response = self._client.embeddings.create(input=cleaned, model=self._model)
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]

    def embed_entity(self, entity_type: str, props: dict) -> list[float]:
        template = _TEMPLATES.get(entity_type)
        text = template(props) if template else str(props)
        return self.embed_text(text)


def _create_embedding_service() -> Optional[EmbeddingService]:
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set. Embedding features will be disabled.")
        return None
    try:
        return EmbeddingService()
    except Exception as e:
        logger.warning(f"Failed to create EmbeddingService: {e}")
        return None


embedding_service: Optional[EmbeddingService] = _create_embedding_service()
