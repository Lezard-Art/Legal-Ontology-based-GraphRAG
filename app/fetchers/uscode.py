"""USC fetcher — downloads US Code titles 5, 28, and 42 in USLM XML format.

MVP scope: three titles only.  Extend _MVP_TITLES to add more.
Source: https://uscode.house.gov/download/annualhistoricalarchive/
"""
from __future__ import annotations

import io
import zipfile

import httpx

from app.fetchers.base import DocRef, FetchedDoc, Fetcher

# Annual historical archive base URL.  The year is the most recent annual
# release; update when a newer one is available.
_ARCHIVE_BASE = "https://uscode.house.gov/download/annualhistoricalarchive/2023"

# Only these three titles for the MVP.
_MVP_TITLES: list[int] = [5, 28, 42]


class USCodeFetcher(Fetcher):
    """Fetches US Code (USC) titles from the House.gov annual archive in USLM XML."""

    source_key = "uscode"

    async def discover(self) -> list[DocRef]:
        """Return one DocRef per MVP title — no network call needed."""
        return [
            DocRef(
                external_id=f"usc_title_{title:02d}",
                url=f"{_ARCHIVE_BASE}/usc{title:02d}.zip",
                metadata={"title_number": title},
            )
            for title in _MVP_TITLES
        ]

    async def fetch_one(self, ref: DocRef) -> FetchedDoc:
        """Download the zip for a single title and extract XML content."""
        title: int = ref.metadata["title_number"]

        async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
            response = await client.get(ref.url)
            response.raise_for_status()

        xml_parts: list[bytes] = []
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            for name in sorted(zf.namelist()):
                if name.lower().endswith(".xml"):
                    xml_parts.append(zf.read(name))

        if not xml_parts:
            raise ValueError(f"No XML files in zip for USC title {title}: {ref.url}")

        # Join multiple XML files with a newline separator.  In practice each
        # title zip contains exactly one XML file.
        xml_bytes = b"\n".join(xml_parts)

        return FetchedDoc(
            content=xml_bytes,
            content_format="xml",
            title=f"US Code Title {title}",
            doc_type="statute",
            citation=f"Title {title} USC",
            effective_date=None,
            metadata={"title_number": title, "source": "uscode.house.gov"},
        )
