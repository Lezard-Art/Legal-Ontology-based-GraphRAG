"""Fetcher base class (the integration seam for future data-gathering agents).

No concrete fetchers are implemented in v1. Subclasses should override
`discover()` and `fetch_one()`. The base class handles storage, idempotent
upsert of Document/DocumentVersion, and FetchRun accounting.
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.corpus import Document, DocumentVersion, FetchRun, Source
from app.storage import BlobStore, default_store


@dataclass
class DocRef:
    external_id: str
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchedDoc:
    content: bytes
    content_format: str  # 'xml' | 'html' | 'json' | 'pdf' | 'txt'
    title: str
    doc_type: str  # 'statute' | 'regulation' | 'rule' | 'opinion' | 'notice' | 'other'
    citation: str | None = None
    effective_date: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_headers: dict[str, Any] = field(default_factory=dict)


class Fetcher(ABC):
    """Base class. Subclasses live in app/fetchers/{source}.py — none in v1."""

    source_key: str

    def __init__(self, source: Source, store: BlobStore | None = None) -> None:
        self.source = source
        self.store = store or default_store

    @abstractmethod
    async def discover(self) -> list[DocRef]:
        """Return the set of doc refs currently available from this source."""

    @abstractmethod
    async def fetch_one(self, ref: DocRef) -> FetchedDoc:
        """Fetch a single document's full content."""

    async def run(self, db: Session, trigger: str = "manual") -> FetchRun:
        run = FetchRun(source_id=self.source.id, trigger=trigger, status="running")
        db.add(run)
        db.commit()
        db.refresh(run)
        stats = {"discovered": 0, "new": 0, "updated": 0, "unchanged": 0, "failed": 0}
        try:
            refs = await self.discover()
            stats["discovered"] = len(refs)
            for ref in refs:
                try:
                    fetched = await self.fetch_one(ref)
                    self._persist(db, ref, fetched, run.id, stats)
                except Exception:  # noqa: BLE001
                    stats["failed"] += 1
            run.status = "ok"
        except Exception as e:  # noqa: BLE001
            run.status = "error"
            run.error = str(e)
        run.finished_at = datetime.utcnow()
        run.stats = stats
        db.commit()
        return run

    def _persist(
        self,
        db: Session,
        ref: DocRef,
        fetched: FetchedDoc,
        fetch_run_id: str,
        stats: dict[str, int],
    ) -> None:
        sha = hashlib.sha256(fetched.content).hexdigest()
        blob_path = self.store.put(
            fetched.content, source_key=self.source.key, ext=fetched.content_format
        )
        doc = (
            db.query(Document)
            .filter_by(source_id=self.source.id, external_id=ref.external_id)
            .one_or_none()
        )
        is_new_doc = doc is None
        if doc is None:
            doc = Document(
                source_id=self.source.id,
                external_id=ref.external_id,
                title=fetched.title,
                jurisdiction=self.source.jurisdiction,
                doc_type=fetched.doc_type,
                citation=fetched.citation,
                effective_date=fetched.effective_date,
                url=ref.url,
                doc_metadata=fetched.metadata,
            )
            db.add(doc)
            db.flush()
        existing = (
            db.query(DocumentVersion)
            .filter_by(document_id=doc.id, content_sha256=sha)
            .one_or_none()
        )
        if existing is not None:
            stats["unchanged"] += 1
            return
        seq = (
            db.query(DocumentVersion).filter_by(document_id=doc.id).count() + 1
        )
        version = DocumentVersion(
            document_id=doc.id,
            version_seq=seq,
            content_sha256=sha,
            content_length=len(fetched.content),
            content_format=fetched.content_format,
            blob_path=blob_path,
            fetch_run_id=fetch_run_id,
            raw_headers=fetched.raw_headers,
        )
        db.add(version)
        db.flush()
        doc.current_version_id = version.id
        db.commit()
        stats["new" if is_new_doc else "updated"] += 1
