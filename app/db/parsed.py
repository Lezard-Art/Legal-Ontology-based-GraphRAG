from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class ParsedBase(DeclarativeBase):
    pass


parsed_engine = create_engine(
    settings.database_url_parsed,
    future=True,
    connect_args={"check_same_thread": False}
    if settings.database_url_parsed.startswith("sqlite")
    else {},
)
ParsedSession = sessionmaker(bind=parsed_engine, autoflush=False, expire_on_commit=False)


def init_parsed() -> None:
    from app.models import parsed  # noqa: F401

    ParsedBase.metadata.create_all(parsed_engine)
