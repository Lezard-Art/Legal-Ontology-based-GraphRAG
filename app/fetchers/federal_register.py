"""Federal Register fetcher — Executive Orders via the Federal Register public API.

Source:    https://www.federalregister.gov/api/v1/
License:   US Government work; public domain.
Rate limits: ~1,000 requests/day (unauthenticated). No API key required.
Scope:     Presidential Documents → Executive Orders (Phase 0).
           Rules, proposed rules, and notices can be added in Phase 3.

discover() paginates through all EOs, returning one DocRef per document.
fetch_one() downloads the full-text XML when available; falls back to HTML,
then to storing the metadata JSON.
"""
from __future__ import annotations

import json

import httpx

from app.fetchers.base import DocRef, FetchedDoc, Fetcher
from app.fetchers.registry import register_fetcher

_BASE = "https://www.federalregister.gov/api/v1"
_FIELDS = [
    "document_number",
    "title",
    "publication_date",
    "executive_order_number",
    "full_text_xml_url",
    "body_html_url",
    "type",
    "presidential_document_type",
]


@register_fetcher
class FederalRegisterFetcher(Fetcher):
    """Fetches all Executive Orders from the Federal Register public API."""

    source_key = "federal_register"

    async def discover(self) -> list[DocRef]:
        refs: list[DocRef] = []
        page = 1
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            while True:
                resp = await client.get(
                    f"{_BASE}/documents.json",
                    params={
                        "type[]": "PRESDOCU",
                        "presidential_document_type[]": "EXECUTIVE_ORDER",
                        "per_page": 1000,
                        "page": page,
                        "fields[]": _FIELDS,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                for doc in data.get("results", []):
                    refs.append(
                        DocRef(
                            external_id=doc["document_number"],
                            url=doc.get("full_text_xml_url") or doc.get("body_html_url"),
                            metadata={
                                "title": doc.get("title", ""),
                                "publication_date": doc.get("publication_date"),
                                "executive_order_number": doc.get("executive_order_number"),
                                "full_text_xml_url": doc.get("full_text_xml_url"),
                                "body_html_url": doc.get("body_html_url"),
                            },
                        )
                    )
                if data.get("next_page_url") is None:
                    break
                page += 1
        return refs

    async def fetch_one(self, ref: DocRef) -> FetchedDoc:
        meta = ref.metadata
        xml_url: str | None = meta.get("full_text_xml_url")
        html_url: str | None = meta.get("body_html_url")
        fetch_url = xml_url or html_url

        if fetch_url:
            async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
                resp = await client.get(fetch_url)
                resp.raise_for_status()
            content = resp.content
            fmt = "xml" if xml_url else "html"
        else:
            content = json.dumps(meta).encode()
            fmt = "json"

        eo_num = meta.get("executive_order_number")
        citation = f"EO {eo_num}" if eo_num else ref.external_id

        return FetchedDoc(
            content=content,
            content_format=fmt,
            title=meta.get("title", ref.external_id),
            doc_type="rule",
            citation=citation,
            metadata={
                "document_number": ref.external_id,
                "publication_date": meta.get("publication_date"),
                "executive_order_number": eo_num,
                "source": "federalregister.gov",
                "license": "public_domain_usgov",
            },
            raw_headers={},
        )
