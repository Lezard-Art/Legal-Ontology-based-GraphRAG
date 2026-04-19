from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.fetchers as _fetchers  # noqa: F401 — triggers @register_fetcher decorators
from app.api import dashboard, documents, health, parse_queue, sources
from app.db.corpus import init_corpus
from app.db.parsed import init_parsed
from app.scheduler.jobs import register_fetch_jobs
from app.scheduler.jobs import start as start_scheduler
from app.scheduler.jobs import stop as stop_scheduler

# Suppress the unused-import warning — _fetchers is imported for side-effects only.
_ = _fetchers


@asynccontextmanager
async def lifespan(application: FastAPI):  # type: ignore[no-untyped-def]
    init_corpus()
    init_parsed()
    start_scheduler()
    register_fetch_jobs()
    yield
    stop_scheduler()


app = FastAPI(title="Legal Corpus Pipeline", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(sources.router)
app.include_router(documents.router)
app.include_router(parse_queue.router)
app.include_router(dashboard.router)
