"""Seed the expected Source rows.

All sources are created with enabled=False — a human must flip enabled=True
(and set cadence_cron if desired) before the scheduler will run them.
Sources that require an API key must also have the key set in .env.
"""
from __future__ import annotations

from app.db.corpus import CorpusSession, init_corpus
from app.db.parsed import init_parsed
from app.models.corpus import Source

SOURCES = [
    {
        "key": "usc",
        "jurisdiction": "us_federal",
        "fetcher_class": "app.fetchers.uscode.USCodeFetcher",
        "cadence_cron": "0 2 * * 0",  # Weekly, Sunday 02:00 UTC
    },
    {
        "key": "ecfr",
        "jurisdiction": "us_federal",
        "fetcher_class": "app.fetchers.ecfr.ECFRFetcher",
        "cadence_cron": "0 3 * * 0",  # Weekly, Sunday 03:00 UTC
    },
    {
        "key": "federal_register",
        "jurisdiction": "us_federal",
        "fetcher_class": "app.fetchers.federal_register.FederalRegisterFetcher",
        "cadence_cron": "0 6 * * *",  # Daily 06:00 UTC
    },
    {
        "key": "congress",
        "jurisdiction": "us_federal",
        "fetcher_class": "app.fetchers.congress.CongressFetcher",
        "cadence_cron": "0 4 * * *",  # Daily 04:00 UTC
    },
    {
        "key": "courtlistener",
        "jurisdiction": "us_federal",
        "fetcher_class": "app.fetchers.courtlistener.CourtListenerFetcher",
        "cadence_cron": "0 5 * * *",  # Daily 05:00 UTC
    },
    {
        "key": "ny_senate",
        "jurisdiction": "ny_state",
        "fetcher_class": "app.fetchers.ny_senate.NYSenateFetcher",
        "cadence_cron": "0 4 * * 0",  # Weekly, Sunday 04:00 UTC
    },
    {
        "key": "nycrr",
        "jurisdiction": "ny_state",
        "fetcher_class": "app.fetchers.nycrr.NYCRRFetcher",
        "licensing_status": "blocked",
        # No cadence_cron — must not be scheduled until licensing is resolved.
    },
]


def main() -> None:
    init_corpus()
    init_parsed()
    with CorpusSession() as db:
        for spec in SOURCES:
            existing = db.query(Source).filter_by(key=spec["key"]).one_or_none()
            if existing is None:
                db.add(Source(**spec))
            else:
                # Upsert fetcher_class and cadence_cron if they were blank.
                if not existing.fetcher_class and spec.get("fetcher_class"):
                    existing.fetcher_class = spec["fetcher_class"]
                if not existing.cadence_cron and spec.get("cadence_cron"):
                    existing.cadence_cron = spec["cadence_cron"]
        db.commit()
        keys = [s.key for s in db.query(Source).all()]
        print(f"Sources seeded: {keys}")


if __name__ == "__main__":
    main()
