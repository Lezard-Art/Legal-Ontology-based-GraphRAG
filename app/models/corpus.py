"""Raw corpus DB models.

Stores Sources, their fetch runs, Documents, DocumentVersions, and the parse
queue. The parse queue lives here (not in the parsed DB) because it is
operational state for the pipeline, not domain data.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.corpus import CorpusBase


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class Source(CorpusBase):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(32), nullable=False)  # us_federal | ny_state
    fetcher_class: Mapped[str | None] = mapped_column(String(256), nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cadence_cron: Mapped[str | None] = mapped_column(String(64), nullable=True)
    licensing_status: Mapped[str] = mapped_column(String(32), default="ok", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class FetchRun(CorpusBase):
    __tablename__ = "fetch_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[str] = mapped_column(String(16), default="manual", nullable=False)


class Document(CorpusBase):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_source_extid"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(256), nullable=False)
    citation: Mapped[str | None] = mapped_column(String(256), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(32), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    current_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(CorpusBase):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "content_sha256", name="uq_doc_sha"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    version_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_length: Mapped[int] = mapped_column(Integer, nullable=False)
    content_format: Mapped[str] = mapped_column(String(16), nullable=False)
    blob_path: Mapped[str] = mapped_column(Text, nullable=False)
    fetch_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("fetch_runs.id"), nullable=True
    )
    raw_headers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    document: Mapped[Document] = relationship(back_populates="versions")


class ParseQueue(CorpusBase):
    """Operational parse queue. Lives in corpus DB because it is pipeline state."""

    __tablename__ = "parse_queue"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    corpus_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    corpus_document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    parser_name: Mapped[str] = mapped_column(String(64), nullable=False, default="noop")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    enqueued_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
