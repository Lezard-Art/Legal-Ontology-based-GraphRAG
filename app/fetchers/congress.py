"""Congress.gov fetcher — bills from the 118th Congress.

Source:    https://api.congress.gov/v3/
License:   US Government work; public domain.
Rate limits: 5,000 requests/hour (with API key).
API key:   Required — set CONGRESS_API_KEY in .env.
           Register at: https://api.congress.gov/sign-up/

discover() paginates all bill types for the 118th Congress.
fetch_one() retrieves the full bill detail record as JSON.
Full bill text (XML/TXT) can be added in Phase 3 via the /text endpoint.
"""
from __future__ import annotations

import json

import httpx

from app.config import settings
from app.fetchers.base import DocRef, FetchedDoc, Fetcher
from app.fetchers.registry import register_fetcher

_BASE = "https://api.congress.gov/v3"
_CONGRESS = 118  # Most recent enacted congress; bump to 119 when available.
_BILL_TYPES = ["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"]


@register_fetcher
class CongressFetcher(Fetcher):
    """Fetches bills from the 118th Congress via the Congress.gov API."""

    source_key = "congress"

    def _api_key(self) -> str:
        key = settings.congress_api_key
        if not key:
            raise RuntimeError(
                "CONGRESS_API_KEY is not set. "
                "Register at https://api.congress.gov/sign-up/ "
                "and add CONGRESS_API_KEY=<your-key> to .env."
            )
        return key

    async def discover(self) -> list[DocRef]:
        api_key = self._api_key()
        refs: list[DocRef] = []
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            for bill_type in _BILL_TYPES:
                offset = 0
                while True:
                    resp = await client.get(
                        f"{_BASE}/bill/{_CONGRESS}/{bill_type}",
                        params={
                            "format": "json",
                            "limit": 250,
                            "offset": offset,
                            "api_key": api_key,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    bills = data.get("bills", [])
                    for bill in bills:
                        number = bill.get("number", "")
                        refs.append(
                            DocRef(
                                external_id=f"{_CONGRESS}-{bill_type}-{number}",
                                url=bill.get("url"),
                                metadata={
                                    "congress": _CONGRESS,
                                    "bill_type": bill_type,
                                    "bill_number": number,
                                    "title": bill.get("title", ""),
                                    "origin_chamber": bill.get("originChamber", ""),
                                    "latest_action": bill.get("latestAction", {}),
                                },
                            )
                        )
                    total = data.get("pagination", {}).get("count", 0)
                    offset += 250
                    if offset >= total:
                        break
        return refs

    async def fetch_one(self, ref: DocRef) -> FetchedDoc:
        api_key = self._api_key()
        meta = ref.metadata
        congress = meta["congress"]
        bill_type = meta["bill_type"]
        number = meta["bill_number"]

        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            resp = await client.get(
                f"{_BASE}/bill/{congress}/{bill_type}/{number}",
                params={"format": "json", "api_key": api_key},
            )
            resp.raise_for_status()
            detail = resp.json().get("bill", {})

        return FetchedDoc(
            content=json.dumps(detail).encode(),
            content_format="json",
            title=detail.get("title", meta.get("title", ref.external_id)),
            doc_type="statute",
            citation=f"{bill_type.upper()} {number}, {congress}th Cong.",
            metadata={
                "congress": congress,
                "bill_type": bill_type,
                "bill_number": number,
                "source": "api.congress.gov",
                "license": "public_domain_usgov",
            },
            raw_headers={},
        )
