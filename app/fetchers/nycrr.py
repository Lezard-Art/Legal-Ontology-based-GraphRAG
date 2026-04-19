"""NYCRR stub — New York Codes, Rules and Regulations.

LICENSING BLOCK: NYCRR is published under a commercial license by Westlaw
and LexisNexis. Free bulk XML access is not available from any official
government source. Do NOT scrape westlaw.com or lexisnexis.com.

See docs/nycrr-licensing.md for details and alternative paths.

This class registers in the fetcher registry so the Source row exists in the
DB and any accidental trigger raises a clear, actionable error.
"""
from __future__ import annotations

from app.fetchers.base import DocRef, FetchedDoc, Fetcher
from app.fetchers.registry import register_fetcher

_BLOCK_MSG = (
    "NYCRR is commercially licensed (Westlaw / LexisNexis). "
    "Bulk XML access is not available. See docs/nycrr-licensing.md."
)


@register_fetcher
class NYCRRFetcher(Fetcher):
    """Stub — NYCRR is commercially licensed; fetch is not implemented."""

    source_key = "nycrr"

    async def discover(self) -> list[DocRef]:
        raise NotImplementedError(_BLOCK_MSG)

    async def fetch_one(self, ref: DocRef) -> FetchedDoc:
        raise NotImplementedError(_BLOCK_MSG)
