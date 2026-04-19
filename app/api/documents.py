from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db.corpus import CorpusSession
from app.db.parsed import ParsedSession
from app.models.corpus import Document, ParseQueue
from app.models.parsed import ParseRun

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
def list_documents(source_id: str | None = None, limit: int = 100) -> list[dict[str, object]]:
    with CorpusSession() as db:
        q = db.query(Document)
        if source_id:
            q = q.filter_by(source_id=source_id)
        rows = q.limit(limit).all()
        return [
            {
                "id": d.id,
                "source_id": d.source_id,
                "title": d.title,
                "citation": d.citation,
                "doc_type": d.doc_type,
                "current_version_id": d.current_version_id,
            }
            for d in rows
        ]


@router.get("/{document_id}")
def get_document(document_id: str) -> dict[str, object]:
    with CorpusSession() as db:
        d = db.get(Document, document_id)
        if d is None:
            raise HTTPException(404, "not found")
        return {
            "id": d.id,
            "source_id": d.source_id,
            "title": d.title,
            "citation": d.citation,
            "doc_type": d.doc_type,
            "jurisdiction": d.jurisdiction,
            "current_version_id": d.current_version_id,
            "metadata": d.doc_metadata,
        }


@router.post("/{document_id}/parse", status_code=202)
def enqueue_parse(document_id: str, parser: str = "noop") -> dict[str, object]:
    with CorpusSession() as db:
        d = db.get(Document, document_id)
        if d is None:
            raise HTTPException(404, "not found")
        if d.current_version_id is None:
            raise HTTPException(400, "document has no version to parse")
        item = ParseQueue(
            corpus_version_id=d.current_version_id,
            corpus_document_id=d.id,
            parser_name=parser,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"queue_id": item.id, "status": item.status}


@router.get("/{document_id}/parse-history")
def parse_history(document_id: str) -> list[dict[str, object]]:
    with ParsedSession() as db:
        rows = (
            db.query(ParseRun)
            .filter_by(corpus_document_id=document_id)
            .order_by(ParseRun.enqueued_at.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "parser_name": r.parser_name,
                "status": r.status,
                "enqueued_at": r.enqueued_at.isoformat() if r.enqueued_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "error": r.error,
            }
            for r in rows
        ]
