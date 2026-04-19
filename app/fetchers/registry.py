"""Fetcher registry — mirrors app/parse/registry.py.

All concrete Fetcher subclasses self-register via @register_fetcher when their
module is imported.  Import app.fetchers (the package) to trigger all of them.
"""
from __future__ import annotations

from app.fetchers.base import Fetcher

_REGISTRY: dict[str, type[Fetcher]] = {}


def register_fetcher(cls: type[Fetcher]) -> type[Fetcher]:
    _REGISTRY[cls.source_key] = cls
    return cls


def get_fetcher_class(source_key: str) -> type[Fetcher]:
    if source_key not in _REGISTRY:
        raise KeyError(
            f"No fetcher registered for source_key={source_key!r}. "
            f"Available: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[source_key]


def registered_keys() -> list[str]:
    return sorted(_REGISTRY)
