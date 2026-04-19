"""Network integration tests for all concrete fetchers.

SKIPPED by default. Run with:
    RUN_NETWORK_TESTS=1 pytest tests/test_fetchers_network.py -v

These tests make real HTTP requests.  They verify:
  - discover() returns at least one DocRef
  - fetch_one(refs[0]) returns non-empty bytes
  - SHA256 of the content is stable across two consecutive fetch_one() calls

No DB writes are performed — a MagicMock source is used in place of a real
Source ORM object, since discover() and fetch_one() never access self.source.
"""
from __future__ import annotations

import hashlib
import os
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_NETWORK_TESTS") != "1",
    reason="set RUN_NETWORK_TESTS=1 to run network tests (makes real HTTP requests)",
)


def _mock_source(key: str) -> MagicMock:
    src = MagicMock()
    src.key = key
    src.id = f"test-{key}"
    src.jurisdiction = "us_federal"
    return src


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


# ---------------------------------------------------------------------------
# USC
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_usc_fetcher_network() -> None:
    from app.fetchers.uscode import USCodeFetcher

    fetcher = USCodeFetcher(_mock_source("usc"))
    refs = await fetcher.discover()
    assert len(refs) == 54

    # Use title 5 (Administrative Procedure Act area) — one of the smaller titles.
    title5_ref = next(r for r in refs if r.metadata["title_number"] == 5)
    doc1 = await fetcher.fetch_one(title5_ref)
    assert doc1.content
    assert doc1.content_format == "xml"

    doc2 = await fetcher.fetch_one(title5_ref)
    assert _sha(doc1.content) == _sha(doc2.content), "USC content not stable across calls"


# ---------------------------------------------------------------------------
# eCFR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ecfr_fetcher_network() -> None:
    from app.fetchers.ecfr import ECFRFetcher

    fetcher = ECFRFetcher(_mock_source("ecfr"))
    refs = await fetcher.discover()
    assert len(refs) == 50

    # Title 1 (General Provisions) is small and always present.
    title1_ref = next(r for r in refs if r.metadata["title_number"] == 1)
    doc = await fetcher.fetch_one(title1_ref)
    assert doc.content
    assert doc.content_format == "xml"


# ---------------------------------------------------------------------------
# Federal Register
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_federal_register_fetcher_network() -> None:
    from app.fetchers.federal_register import FederalRegisterFetcher

    fetcher = FederalRegisterFetcher(_mock_source("federal_register"))
    refs = await fetcher.discover()
    assert len(refs) > 0, "Expected at least one Executive Order"

    doc = await fetcher.fetch_one(refs[0])
    assert doc.content
    assert doc.content_format in ("xml", "html", "json")


# ---------------------------------------------------------------------------
# Congress (requires CONGRESS_API_KEY)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("CONGRESS_API_KEY"),
    reason="CONGRESS_API_KEY not set",
)
async def test_congress_fetcher_network() -> None:
    from app.fetchers.congress import CongressFetcher

    fetcher = CongressFetcher(_mock_source("congress"))
    refs = await fetcher.discover()
    assert len(refs) > 0

    doc = await fetcher.fetch_one(refs[0])
    assert doc.content
    assert doc.content_format == "json"


# ---------------------------------------------------------------------------
# CourtListener (requires COURTLISTENER_API_KEY)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("COURTLISTENER_API_KEY"),
    reason="COURTLISTENER_API_KEY not set",
)
async def test_courtlistener_fetcher_network() -> None:
    from app.fetchers.courtlistener import CourtListenerFetcher

    fetcher = CourtListenerFetcher(_mock_source("courtlistener"))
    refs = await fetcher.discover()
    assert len(refs) > 0

    doc = await fetcher.fetch_one(refs[0])
    assert doc.content
    assert doc.content_format in ("txt", "html", "json")


# ---------------------------------------------------------------------------
# NY Senate (requires NY_SENATE_API_KEY)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("NY_SENATE_API_KEY"),
    reason="NY_SENATE_API_KEY not set",
)
async def test_ny_senate_fetcher_network() -> None:
    from app.fetchers.ny_senate import NYSenateFetcher

    fetcher = NYSenateFetcher(_mock_source("ny_senate"))
    refs = await fetcher.discover()
    assert len(refs) > 0

    doc = await fetcher.fetch_one(refs[0])
    assert doc.content
    assert doc.content_format == "json"


# ---------------------------------------------------------------------------
# NYCRR — should raise immediately (licensing block)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nycrr_raises_not_implemented() -> None:
    from app.fetchers.nycrr import NYCRRFetcher

    fetcher = NYCRRFetcher(_mock_source("nycrr"))
    with pytest.raises(NotImplementedError, match="commercially licensed"):
        await fetcher.discover()
