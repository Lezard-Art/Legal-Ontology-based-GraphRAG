"""NY Senate Open Legislation fetcher — New York Consolidated Laws.

Source:    https://legislation.nysenate.gov/api/3/
License:   NY Open Data Law; see https://openlegislation.nysenate.gov/.
Rate limits: Not published; be respectful.
API key:   Required — set NY_SENATE_API_KEY in .env.
           Register at: https://legislation.nysenate.gov/register

discover() lists all NY Consolidated Law chapters.
fetch_one() retrieves each chapter's full text as JSON (the API's native format).
"""
from __future__ import annotations

import json

import httpx

from app.config import settings
from app.fetchers.base import DocRef, FetchedDoc, Fetcher
from app.fetchers.registry import register_fetcher

_BASE = "https://legislation.nysenate.gov/api/3"


@register_fetcher
class NYSenateFetcher(Fetcher):
    """Fetches NY Consolidated Law chapters via the Open Legislation API."""

    source_key = "ny_senate"

    def _api_key(self) -> str:
        key = settings.ny_senate_api_key
        if not key:
            raise RuntimeError(
                "NY_SENATE_API_KEY is not set. "
                "Register at https://legislation.nysenate.gov/register "
                "and add NY_SENATE_API_KEY=<your-key> to .env."
            )
        return key

    async def discover(self) -> list[DocRef]:
        api_key = self._api_key()
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            resp = await client.get(f"{_BASE}/laws", params={"key": api_key})
            resp.raise_for_status()
            data = resp.json()

        laws = data.get("result", {}).get("items", [])
        return [
            DocRef(
                external_id=law["lawId"],
                url=None,
                metadata={
                    "law_id": law["lawId"],
                    "name": law.get("name", ""),
                    "law_type": law.get("lawType", ""),
                    "chapter": law.get("chapter", ""),
                },
            )
            for law in laws
        ]

    async def fetch_one(self, ref: DocRef) -> FetchedDoc:
        api_key = self._api_key()
        law_id: str = ref.metadata["law_id"]

        async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
            resp = await client.get(
                f"{_BASE}/laws/{law_id}",
                params={"key": api_key, "full": "true"},
            )
            resp.raise_for_status()
            data = resp.json()

        return FetchedDoc(
            content=json.dumps(data).encode(),
            content_format="json",
            title=ref.metadata.get("name", law_id),
            doc_type="statute",
            citation=f"NY {law_id}",
            metadata={
                "law_id": law_id,
                "law_type": ref.metadata.get("law_type"),
                "chapter": ref.metadata.get("chapter"),
                "source": "legislation.nysenate.gov",
                "license": "ny_open_data",
            },
            raw_headers={},
        )
