"""Parser seam — the contract between the pipeline and any future parser.

To plug in a real parser: implement `Parser.parse()` and register it.
**Nothing else in the pipeline should need to change.**
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal


@dataclass
class DocumentDTO:
    id: str
    source_id: str
    title: str
    doc_type: str
    jurisdiction: str
    citation: str | None = None


@dataclass
class VersionDTO:
    id: str
    document_id: str
    version_seq: int
    content_format: str
    content_sha256: str
    blob_path: str


@dataclass
class ParseResult:
    status: Literal["ok", "error", "noop"]
    parser_name: str
    parser_version: str
    payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class Parser(ABC):
    name: ClassVar[str]
    version: ClassVar[str]

    @abstractmethod
    async def parse(
        self, *, document: DocumentDTO, version: VersionDTO, blob: bytes
    ) -> ParseResult: ...
