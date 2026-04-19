from __future__ import annotations

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.db.corpus import corpus_engine
from app.db.parsed import parsed_engine
from app.storage import default_store

router = APIRouter()


@router.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@router.get("/api/ready")
def ready(response: Response) -> dict[str, object]:
    status: dict[str, object] = {"corpus_db": False, "parsed_db": False, "blob_store": False}
    try:
        with corpus_engine.connect() as c:
            c.execute(text("SELECT 1"))
        status["corpus_db"] = True
    except Exception as e:  # noqa: BLE001
        status["corpus_db_error"] = str(e)
    try:
        with parsed_engine.connect() as c:
            c.execute(text("SELECT 1"))
        status["parsed_db"] = True
    except Exception as e:  # noqa: BLE001
        status["parsed_db_error"] = str(e)
    try:
        import tempfile

        tmp = default_store.put(b"ready-check", source_key="_health", ext="txt")
        default_store.get(tmp)
        status["blob_store"] = True
        del tempfile
    except Exception as e:  # noqa: BLE001
        status["blob_store_error"] = str(e)
    if not all([status["corpus_db"], status["parsed_db"], status["blob_store"]]):
        response.status_code = 503
    return status
