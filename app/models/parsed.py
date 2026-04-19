"""Parsed schema DB models.

These tables are created but expected to be EMPTY in v1 (only NoOpParser runs,
writing noop-status rows). The ontology stub tables are placeholders whose shape
is to be defined by the future parser implementation.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.parsed import ParsedBase


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class ParsedDocument(ParsedBase):
    __tablename__ = "parsed_documents"
    __table_args__ = (
        UniqueConstraint("corpus_version_id", "parser_name", name="uq_version_parser"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    corpus_document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    corpus_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    parser_name: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False)
    parsed_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class ParseRun(ParsedBase):
    __tablename__ = "parse_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    corpus_document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    corpus_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    parser_name: Mapped[str] = mapped_column(String(64), nullable=False)
    enqueued_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[str] = mapped_column(String(16), default="manual")


# --- Ontology stub tables. v1: shape TBD by real parser author. ---


class NormativeStatement(ParsedBase):
    __tablename__ = "normative_statements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class LegalActor(ParsedBase):
    __tablename__ = "legal_actors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class LegalPosition(ParsedBase):
    __tablename__ = "legal_positions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
