# Import all concrete fetchers to trigger their @register_fetcher decorators.
# The order does not matter; all end up in app.fetchers.registry._REGISTRY.
from app.fetchers import (  # noqa: F401
    congress,
    courtlistener,
    ecfr,
    federal_register,
    ny_senate,
    nycrr,
    uscode,
)
from app.fetchers.base import DocRef, FetchedDoc, Fetcher

__all__ = ["DocRef", "FetchedDoc", "Fetcher"]
