"""APScheduler wiring.

Two job types:
  1. parse_drain — runs every 5 s, drains the parse queue (always active).
  2. fetch_<source_key> — one cron job per enabled Source that has a cadence_cron
     and a registered fetcher. Created by register_fetch_jobs(), called from
     lifespan() after DB init and fetcher imports.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.parse.worker import drain

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _run_fetch(source_id: str, source_key: str) -> None:
    """Scheduled fetch job — creates its own DB session."""
    from app.db.corpus import CorpusSession
    from app.fetchers.registry import get_fetcher_class
    from app.models.corpus import Source

    with CorpusSession() as db:
        source = db.get(Source, source_id)
        if source is None or not source.enabled:
            return
        fetcher_cls = get_fetcher_class(source_key)
        fetcher = fetcher_cls(source)
        run = await fetcher.run(db, trigger="scheduled")
        logger.info("Scheduled fetch %s finished: %s", source_key, run.stats)


def register_fetch_jobs() -> None:
    """Register one cron job per enabled source with a cadence_cron set.

    Call this after init_corpus() and after importing app.fetchers so that
    the fetcher registry is populated.
    """
    from app.db.corpus import CorpusSession
    from app.fetchers.registry import registered_keys
    from app.models.corpus import Source

    available = set(registered_keys())
    with CorpusSession() as db:
        sources = db.query(Source).filter(Source.enabled.is_(True)).all()
        for src in sources:
            if not src.cadence_cron or src.key not in available:
                continue
            job_id = f"fetch_{src.key}"
            scheduler.add_job(
                _run_fetch,
                trigger=CronTrigger.from_crontab(src.cadence_cron),
                args=[src.id, src.key],
                id=job_id,
                replace_existing=True,
            )
            logger.info("Registered fetch job %s with cron %r", job_id, src.cadence_cron)


def start() -> None:
    if scheduler.running:
        return
    scheduler.add_job(drain, "interval", seconds=5, id="parse_drain", replace_existing=True)
    scheduler.start()


def stop() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
