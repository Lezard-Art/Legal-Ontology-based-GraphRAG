from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db.corpus import CorpusSession
from app.models.corpus import Source

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("")
def list_sources() -> list[dict[str, object]]:
    with CorpusSession() as db:
        rows = db.query(Source).order_by(Source.key).all()
        return [
            {
                "id": s.id,
                "key": s.key,
                "jurisdiction": s.jurisdiction,
                "enabled": s.enabled,
                "licensing_status": s.licensing_status,
                "cadence_cron": s.cadence_cron,
                "fetcher_class": s.fetcher_class,
            }
            for s in rows
        ]


@router.post("/{source_id}/fetch", status_code=202)
def fetch_source(source_id: str) -> dict[str, str]:
    """Manual fetch trigger. v1 note: no concrete Fetcher subclasses are wired
    in, so this returns 501 for every known source. The endpoint exists so the
    call site can be written now and will Just Work once a Fetcher is added."""
    with CorpusSession() as db:
        source = db.get(Source, source_id)
        if source is None:
            raise HTTPException(404, "source not found")
        raise HTTPException(
            501,
            f"No concrete fetcher registered for source '{source.key}'. "
            "Implement a Fetcher subclass and set source.fetcher_class.",
        )


@router.post("/{source_id}/parse-all")
def parse_all_for_source(source_id: str) -> dict[str, object]:
    from app.models.corpus import Document, DocumentVersion, ParseQueue

    with CorpusSession() as db:
        source = db.get(Source, source_id)
        if source is None:
            raise HTTPException(404, "source not found")
        docs = db.query(Document).filter_by(source_id=source_id).all()
        enqueued = 0
        for d in docs:
            if d.current_version_id is None:
                continue
            db.add(
                ParseQueue(
                    corpus_version_id=d.current_version_id,
                    corpus_document_id=d.id,
                    parser_name="noop",
                )
            )
            enqueued += 1
        db.commit()
        return {"source_id": source_id, "enqueued": enqueued}
