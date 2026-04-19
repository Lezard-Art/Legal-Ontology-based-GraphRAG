from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class CorpusBase(DeclarativeBase):
    pass


corpus_engine = create_engine(
    settings.database_url_corpus,
    future=True,
    connect_args={"check_same_thread": False}
    if settings.database_url_corpus.startswith("sqlite")
    else {},
)
CorpusSession = sessionmaker(bind=corpus_engine, autoflush=False, expire_on_commit=False)


def init_corpus() -> None:
    from app.models import corpus  # noqa: F401  (register models)

    CorpusBase.metadata.create_all(corpus_engine)
