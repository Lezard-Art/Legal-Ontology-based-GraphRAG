"""APScheduler wiring. In v1 no concrete fetchers are implemented, so the
scheduler registers no jobs — the wiring exists so M12 can flip a source's
`enabled=true` and `cadence_cron` and have it start running automatically
once a concrete Fetcher subclass is added."""
from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.parse.worker import drain

scheduler = AsyncIOScheduler()


def start() -> None:
    if scheduler.running:
        return
    # Background parse-queue drainer: runs every 5 seconds.
    scheduler.add_job(drain, "interval", seconds=5, id="parse_drain", replace_existing=True)
    scheduler.start()


def stop() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
