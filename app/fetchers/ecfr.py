"""eCFR fetcher — downloads all 50 CFR titles in XML format.

Source:    https://www.ecfr.gov/api/versioner/v1/full/current/title-{N}.xml
License:   US Government work; public domain.
Rate limits: Not published. Titles vary from ~1 MB to ~150 MB. Use 300 s timeout.
API key:   Not required.

Each title is fetched as a single XML document representing the current version.
"""
from __future__ import annotations

import httpx

from app.fetchers.base import DocRef, FetchedDoc, Fetcher
from app.fetchers.registry import register_fetcher

_BASE = "https://www.ecfr.gov/api/versioner/v1/full/current"
_ALL_TITLES = list(range(1, 51))  # CFR titles 1–50.


@register_fetcher
class ECFRFetcher(Fetcher):
    """Fetches all 50 CFR titles from the eCFR versioner API in XML format."""

    source_key = "ecfr"

    async def discover(self) -> list[DocRef]:
        return [
            DocRef(
                external_id=f"cfr_title_{title:02d}",
                url=f"{_BASE}/title-{title}.xml",
                metadata={"title_number": title},
            )
            for title in _ALL_TITLES
        ]

    async def fetch_one(self, ref: DocRef) -> FetchedDoc:
        title: int = ref.metadata["title_number"]
        assert ref.url is not None

        async with httpx.AsyncClient(follow_redirects=True, timeout=300.0) as client:
            response = await client.get(ref.url)
            response.raise_for_status()

        return FetchedDoc(
            content=response.content,
            content_format="xml",
            title=f"Code of Federal Regulations Title {title}",
            doc_type="regulation",
            citation=f"{title} C.F.R.",
            metadata={
                "title_number": title,
                "fetched_url": str(response.url),
                "source": "ecfr.gov",
                "license": "public_domain_usgov",
            },
            raw_headers=dict(response.headers),
        )
