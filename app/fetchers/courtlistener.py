"""CourtListener fetcher — federal court opinions.

Source:    https://www.courtlistener.com/api/rest/v3/
License:   US Government-authored opinions are public domain; third-party
           opinions may carry their own restrictions.
           See https://www.courtlistener.com/terms/.
Rate limits: 5,000 requests/day (authenticated). Unauthenticated requests
             are severely throttled — the API key is required.
API key:   Required — set COURTLISTENER_API_KEY in .env.
           Create a free account at https://www.courtlistener.com/register/

Scope: SCOTUS + all 13 federal circuit courts, ordered by recency.
       _MAX_PAGES caps each court at ~2,000 opinions per run so the initial
       fetch completes in a reasonable time. Increase for Phase 3 full ingestion.
"""
from __future__ import annotations

import json

import httpx

from app.config import settings
from app.fetchers.base import DocRef, FetchedDoc, Fetcher
from app.fetchers.registry import register_fetcher

_BASE = "https://www.courtlistener.com/api/rest/v3"
_FEDERAL_COURTS = [
    "scotus",
    "ca1", "ca2", "ca3", "ca4", "ca5", "ca6", "ca7",
    "ca8", "ca9", "ca10", "ca11", "cadc", "cafc",
]
_PAGE_SIZE = 100
_MAX_PAGES = 20  # ~2,000 opinions per court; bump in Phase 3.


@register_fetcher
class CourtListenerFetcher(Fetcher):
    """Fetches federal court opinions from CourtListener."""

    source_key = "courtlistener"

    def _auth_headers(self) -> dict[str, str]:
        key = settings.courtlistener_api_key
        if not key:
            raise RuntimeError(
                "COURTLISTENER_API_KEY is not set. "
                "Create a free account at https://www.courtlistener.com/register/ "
                "and add COURTLISTENER_API_KEY=<your-token> to .env."
            )
        return {"Authorization": f"Token {key}"}

    async def discover(self) -> list[DocRef]:
        refs: list[DocRef] = []
        headers = self._auth_headers()
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            for court in _FEDERAL_COURTS:
                for page in range(1, _MAX_PAGES + 1):
                    resp = await client.get(
                        f"{_BASE}/opinions/",
                        headers=headers,
                        params={
                            "court": court,
                            "order_by": "-date_created",
                            "page_size": _PAGE_SIZE,
                            "page": page,
                            "format": "json",
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    for opinion in data.get("results", []):
                        refs.append(
                            DocRef(
                                external_id=str(opinion["id"]),
                                url=None,
                                metadata={
                                    "court": court,
                                    "date_created": opinion.get("date_created"),
                                    "opinion_type": opinion.get("type", ""),
                                },
                            )
                        )
                    if not data.get("next"):
                        break
        return refs

    async def fetch_one(self, ref: DocRef) -> FetchedDoc:
        headers = self._auth_headers()
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            resp = await client.get(
                f"{_BASE}/opinions/{ref.external_id}/",
                headers=headers,
                params={"format": "json"},
            )
            resp.raise_for_status()
            opinion = resp.json()

        # Prefer plain text; fall back to HTML variants; last resort: raw JSON.
        plain = opinion.get("plain_text", "")
        html_cited = opinion.get("html_with_citations", "")
        html = opinion.get("html", "")

        if plain:
            content, fmt = plain.encode(), "txt"
        elif html_cited:
            content, fmt = html_cited.encode(), "html"
        elif html:
            content, fmt = html.encode(), "html"
        else:
            content, fmt = json.dumps(opinion).encode(), "json"

        court = ref.metadata.get("court", "unknown")
        return FetchedDoc(
            content=content,
            content_format=fmt,
            title=f"Opinion {ref.external_id} ({court})",
            doc_type="opinion",
            citation=ref.external_id,
            metadata={
                "opinion_id": ref.external_id,
                "court": court,
                "date_created": ref.metadata.get("date_created"),
                "source": "courtlistener.com",
            },
            raw_headers={},
        )
