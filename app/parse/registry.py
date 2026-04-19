from __future__ import annotations

from app.parse.interface import Parser
from app.parse.noop import NoOpParser

_REGISTRY: dict[str, type[Parser]] = {}


def register_parser(cls: type[Parser]) -> type[Parser]:
    _REGISTRY[cls.name] = cls
    return cls


def get_parser(name: str) -> Parser:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown parser: {name}. Registered: {list(_REGISTRY)}")
    return _REGISTRY[name]()


def default_parser_name() -> str:
    return "noop"


register_parser(NoOpParser)
