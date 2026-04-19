from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.db.corpus import CorpusSession
from app.models.corpus import DocumentVersion, ParseQueue
from app.parse.worker import drain

router = APIRouter(prefix="/api/parse-queue", tags=["parse-queue"])


@router.get("")
def list_queue(status: str | None = None, limit: int = 100) -> list[dict[str, object]]:
    with CorpusSession() as db:
        q = db.query(ParseQueue).order_by(ParseQueue.enqueued_at.desc())
        if status:
            q = q.filter_by(status=status)
        rows = q.limit(limit).all()
        return [
            {
                "id": r.id,
                "corpus_document_id": r.corpus_document_id,
                "corpus_version_id": r.corpus_version_id,
                "parser_name": r.parser_name,
                "status": r.status,
                "attempts": r.attempts,
                "enqueued_at": r.enqueued_at.isoformat() if r.enqueued_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "last_error": r.last_error,
            }
            for r in rows
        ]


@router.post("/enqueue-missing")
def enqueue_missing(parser: str = "noop") -> dict[str, int]:
    """Enqueue every DocumentVersion that has no entry (for this parser) in the
    queue. Does NOT check the parsed DB — that's a cross-DB join we skip in v1.
    """
    with CorpusSession() as db:
        existing = {
            row[0]
            for row in db.execute(
                select(ParseQueue.corpus_version_id).where(ParseQueue.parser_name == parser)
            ).all()
        }
        versions = db.query(DocumentVersion).all()
        count = 0
        for v in versions:
            if v.id in existing:
                continue
            db.add(
                ParseQueue(
                    corpus_version_id=v.id,
                    corpus_document_id=v.document_id,
                    parser_name=parser,
                )
            )
            count += 1
        db.commit()
        return {"enqueued": count}


@router.post("/drain")
async def drain_now() -> dict[str, int]:
    """Process the queue synchronously. Useful for tests and manual triggers."""
    n = await drain()
    return {"processed": n}
