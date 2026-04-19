"""NoOpParser — the v1 stub. Replace this file (or register a sibling) to plug
in a real parser. Everything else in the pipeline stays the same."""
from __future__ import annotations

from app.parse.interface import DocumentDTO, ParseResult, Parser, VersionDTO


class NoOpParser(Parser):
    name = "noop"
    version = "0.0.1"

    async def parse(
        self, *, document: DocumentDTO, version: VersionDTO, blob: bytes
    ) -> ParseResult:
        return ParseResult(
            status="noop",
            parser_name=self.name,
            parser_version=self.version,
            payload={"bytes": len(blob), "document_id": document.id},
        )
