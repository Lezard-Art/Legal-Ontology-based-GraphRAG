"""BlobStore ABC + local-filesystem implementation.

Content-addressable: put(bytes) returns a path derived from sha256, so
re-puts of identical bytes collapse to the same path (idempotent).
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from app.config import settings


class BlobStore(ABC):
    @abstractmethod
    def put(self, data: bytes, *, source_key: str, ext: str) -> str: ...

    @abstractmethod
    def get(self, path: str) -> bytes: ...


class LocalFSBlobStore(BlobStore):
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or settings.blob_store_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes, *, source_key: str, ext: str) -> str:
        sha = hashlib.sha256(data).hexdigest()
        now = datetime.utcnow()
        rel = Path(source_key) / f"{now:%Y}" / f"{now:%m}" / f"{sha}.{ext.lstrip('.')}"
        full = self.root / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        if not full.exists():
            full.write_bytes(data)
        return str(rel)

    def get(self, path: str) -> bytes:
        return (self.root / path).read_bytes()


default_store: BlobStore = LocalFSBlobStore()
