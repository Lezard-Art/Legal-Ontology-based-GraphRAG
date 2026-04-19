"""End-to-end test of the parse seam using NoOpParser.

This is the v1 acceptance test: insert a fake document, enqueue it, drain the
queue, and verify a ParsedDocument row appears in the parsed DB with
status='noop'.
"""
from __future__ import annotations

import pytest

from app.db.corpus import CorpusSession, init_corpus
from app.db.parsed import ParsedSession, init_parsed
from app.models.corpus import ParseQueue
from app.models.parsed import ParsedDocument
from app.parse.worker import drain
from scripts.insert_fake_document import main as insert_fake


@pytest.mark.asyncio
async def test_noop_end_to_end() -> None:
    init_corpus()
    init_parsed()
    doc_id = insert_fake()

    # Enqueue via the ParseQueue model directly (mirrors what the API does).
    with CorpusSession() as db:
        from app.models.corpus import Document

        d = db.get(Document, doc_id)
        assert d is not None
        assert d.current_version_id is not None
        db.add(
            ParseQueue(
                corpus_version_id=d.current_version_id,
                corpus_document_id=d.id,
                parser_name="noop",
            )
        )
        db.commit()

    processed = await drain()
    assert processed >= 1

    with ParsedSession() as pdb:
        rows = pdb.query(ParsedDocument).filter_by(corpus_document_id=doc_id).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.status == "noop"
        assert row.parser_name == "noop"
        assert row.payload.get("bytes", 0) > 0

    with CorpusSession() as db:
        q = db.query(ParseQueue).filter_by(corpus_document_id=doc_id).all()
        assert len(q) == 1
        assert q[0].status == "noop"
        assert q[0].finished_at is not None


@pytest.mark.asyncio
async def test_parser_swap_is_one_file() -> None:
    """Verify the 'one file to change' promise: we can register a second parser
    without touching anything in app/api, app/db, app/models, or app/parse/worker.py.
    """
    from app.parse.interface import DocumentDTO, ParseResult, Parser, VersionDTO
    from app.parse.registry import get_parser, register_parser

    class EchoParser(Parser):
        name = "echo"
        version = "0.0.1"

        async def parse(
            self, *, document: DocumentDTO, version: VersionDTO, blob: bytes
        ) -> ParseResult:
            return ParseResult(
                status="ok",
                parser_name=self.name,
                parser_version=self.version,
                payload={"echo": blob[:8].decode(errors="replace")},
            )

    register_parser(EchoParser)
    assert isinstance(get_parser("echo"), EchoParser)
