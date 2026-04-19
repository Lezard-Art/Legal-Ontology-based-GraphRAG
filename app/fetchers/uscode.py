"""USC fetcher — downloads all 54 US Code titles in USLM XML format.

Source:    https://uscode.house.gov/download/annualhistoricalarchive/
License:   US Government work; public domain (17 USC §105).
Rate limits: None documented. ZIPs range from ~1 MB to ~80 MB; use 300 s timeout.
API key:   Not required.

To update to a newer annual release, bump _ARCHIVE_YEAR.
Note: some titles are reserved/repealed and their ZIPs may return 404 or contain
no XML — those are counted as failed in the FetchRun stats, which is correct.
"""
from __future__ import annotations

import io
import zipfile

import httpx

from app.fetchers.base import DocRef, FetchedDoc, Fetcher
from app.fetchers.registry import register_fetcher

_ARCHIVE_YEAR = "2023"
_ARCHIVE_BASE = f"https://uscode.house.gov/download/annualhistoricalarchive/{_ARCHIVE_YEAR}"
_ALL_TITLES = list(range(1, 55))  # Titles 1–54; reserved titles 404 gracefully.


@register_fetcher
class USCodeFetcher(Fetcher):
    """Fetches all 54 US Code titles from the House.gov annual archive in USLM XML."""

    source_key = "usc"

    async def discover(self) -> list[DocRef]:
        return [
            DocRef(
                external_id=f"usc_title_{title:02d}_{_ARCHIVE_YEAR}",
                url=f"{_ARCHIVE_BASE}/usc{title:02d}.zip",
                metadata={"title_number": title, "archive_year": _ARCHIVE_YEAR},
            )
            for title in _ALL_TITLES
        ]

    async def fetch_one(self, ref: DocRef) -> FetchedDoc:
        title: int = ref.metadata["title_number"]
        assert ref.url is not None

        async with httpx.AsyncClient(follow_redirects=True, timeout=300.0) as client:
            response = await client.get(ref.url)
            response.raise_for_status()

        xml_parts: list[bytes] = []
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            for name in sorted(zf.namelist()):
                if name.lower().endswith(".xml"):
                    xml_parts.append(zf.read(name))

        if not xml_parts:
            raise ValueError(f"No XML files in zip for USC title {title}: {ref.url}")

        return FetchedDoc(
            content=b"\n".join(xml_parts),
            content_format="xml",
            title=f"US Code Title {title}",
            doc_type="statute",
            citation=f"{title} U.S.C.",
            metadata={
                "title_number": title,
                "archive_year": _ARCHIVE_YEAR,
                "source": "uscode.house.gov",
                "license": "public_domain_usgov",
            },
            raw_headers={},
        )
