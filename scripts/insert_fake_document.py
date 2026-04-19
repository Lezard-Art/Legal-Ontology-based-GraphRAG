"""Insert a fake Source/Document/DocumentVersion for end-to-end NoOp testing.
Used because v1 has no concrete fetchers yet."""
from __future__ import annotations

import hashlib

from app.db.corpus import CorpusSession, init_corpus
from app.db.parsed import init_parsed
from app.models.corpus import Document, DocumentVersion, Source
from app.storage import default_store


def main() -> str:
    init_corpus()
    init_parsed()
    with CorpusSession() as db:
        src = db.query(Source).filter_by(key="_fake").one_or_none()
        if src is None:
            src = Source(key="_fake", jurisdiction="us_federal")
            db.add(src)
            db.commit()
            db.refresh(src)
        content = b"Fake statute: nothing shall be done without cause."
        blob_path = default_store.put(content, source_key=src.key, ext="txt")
        doc = Document(
            source_id=src.id,
            external_id="fake-001",
            title="Fake Test Statute",
            jurisdiction="us_federal",
            doc_type="statute",
        )
        db.add(doc)
        db.flush()
        ver = DocumentVersion(
            document_id=doc.id,
            version_seq=1,
            content_sha256=hashlib.sha256(content).hexdigest(),
            content_length=len(content),
            content_format="txt",
            blob_path=blob_path,
        )
        db.add(ver)
        db.flush()
        doc.current_version_id = ver.id
        db.commit()
        print(f"document_id={doc.id}")
        return doc.id


if __name__ == "__main__":
    main()
