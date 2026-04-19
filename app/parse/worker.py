"""Parse queue worker.

Pulls queued rows from the corpus DB's parse_queue, invokes the registered
parser (v1: NoOpParser), and writes results into the parsed DB. The worker
knows nothing about what the parser does — that's the point of the seam.
"""
from __future__ import annotations

from datetime import datetime

from app.db.corpus import CorpusSession
from app.db.parsed import ParsedSession
from app.models.corpus import Document, DocumentVersion, ParseQueue
from app.models.parsed import ParsedDocument, ParseRun
from app.parse.interface import DocumentDTO, VersionDTO
from app.parse.registry import get_parser
from app.storage import default_store


async def process_one() -> bool:
    """Process a single queued item. Returns True if work was done."""
    with CorpusSession() as corpus_db:
        item = (
            corpus_db.query(ParseQueue)
            .filter(ParseQueue.status == "queued")
            .order_by(ParseQueue.enqueued_at.asc())
            .first()
        )
        if item is None:
            return False
        item.status = "running"
        item.started_at = datetime.utcnow()
        item.attempts += 1
        corpus_db.commit()
        corpus_db.refresh(item)

        version = corpus_db.get(DocumentVersion, item.corpus_version_id)
        document = corpus_db.get(Document, item.corpus_document_id)
        if version is None or document is None:
            item.status = "error"
            item.last_error = "version or document not found"
            item.finished_at = datetime.utcnow()
            corpus_db.commit()
            return True

        doc_dto = DocumentDTO(
            id=document.id,
            source_id=document.source_id,
            title=document.title,
            doc_type=document.doc_type,
            jurisdiction=document.jurisdiction,
            citation=document.citation,
        )
        ver_dto = VersionDTO(
            id=version.id,
            document_id=version.document_id,
            version_seq=version.version_seq,
            content_format=version.content_format,
            content_sha256=version.content_sha256,
            blob_path=version.blob_path,
        )
        parser_name = item.parser_name
        queue_id = item.id
        enqueued_at = item.enqueued_at
        started_at = item.started_at

    try:
        blob = default_store.get(ver_dto.blob_path)
    except Exception as e:  # noqa: BLE001
        _mark_error(queue_id, f"blob read failed: {e}")
        return True

    try:
        parser = get_parser(parser_name)
        result = await parser.parse(document=doc_dto, version=ver_dto, blob=blob)
    except Exception as e:  # noqa: BLE001
        _mark_error(queue_id, f"parser raised: {e}")
        return True

    finished = datetime.utcnow()
    with ParsedSession() as parsed_db:
        parsed_db.add(
            ParsedDocument(
                corpus_document_id=doc_dto.id,
                corpus_version_id=ver_dto.id,
                parser_name=result.parser_name,
                parser_version=result.parser_version,
                status=result.status,
                payload=result.payload,
                error=result.error,
            )
        )
        parsed_db.add(
            ParseRun(
                corpus_document_id=doc_dto.id,
                corpus_version_id=ver_dto.id,
                parser_name=result.parser_name,
                enqueued_at=enqueued_at,
                started_at=started_at,
                finished_at=finished,
                status=result.status,
                error=result.error,
            )
        )
        parsed_db.commit()

    with CorpusSession() as corpus_db:
        q = corpus_db.get(ParseQueue, queue_id)
        if q is not None:
            q.status = result.status if result.status in ("ok", "noop") else "error"
            q.finished_at = finished
            q.last_error = result.error
            corpus_db.commit()
    return True


def _mark_error(queue_id: str, msg: str) -> None:
    with CorpusSession() as corpus_db:
        q = corpus_db.get(ParseQueue, queue_id)
        if q is not None:
            q.status = "error"
            q.last_error = msg
            q.finished_at = datetime.utcnow()
            corpus_db.commit()


async def drain() -> int:
    """Process all queued items. Returns count processed."""
    n = 0
    while await process_one():
        n += 1
    return n
