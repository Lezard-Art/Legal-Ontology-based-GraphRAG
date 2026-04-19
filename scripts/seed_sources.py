"""Seed the 6 expected Source rows. All `enabled=False` because no concrete
fetcher is implemented yet."""
from __future__ import annotations

from app.db.corpus import CorpusSession, init_corpus
from app.db.parsed import init_parsed
from app.models.corpus import Source

SOURCES = [
    {"key": "usc", "jurisdiction": "us_federal"},
    {"key": "ecfr", "jurisdiction": "us_federal"},
    {"key": "federal_register", "jurisdiction": "us_federal"},
    {"key": "courtlistener", "jurisdiction": "us_federal"},
    {"key": "ny_senate", "jurisdiction": "ny_state"},
    {"key": "nycrr", "jurisdiction": "ny_state", "licensing_status": "blocked"},
]


def main() -> None:
    init_corpus()
    init_parsed()
    with CorpusSession() as db:
        for spec in SOURCES:
            if db.query(Source).filter_by(key=spec["key"]).one_or_none() is None:
                db.add(Source(**spec))
        db.commit()
        print(f"Sources: {[s.key for s in db.query(Source).all()]}")


if __name__ == "__main__":
    main()
