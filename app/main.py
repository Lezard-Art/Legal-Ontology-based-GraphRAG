from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import dashboard, documents, health, parse_queue, sources
from app.db.corpus import init_corpus
from app.db.parsed import init_parsed
from app.scheduler.jobs import start as start_scheduler
from app.scheduler.jobs import stop as stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    init_corpus()
    init_parsed()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Legal Corpus Pipeline", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(sources.router)
app.include_router(documents.router)
app.include_router(parse_queue.router)
app.include_router(dashboard.router)
