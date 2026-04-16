from __future__ import annotations

from bookmarks_mcp.models import Library


def parse(text: str) -> Library:
    return Library.model_validate_json(text)


def serialize(library: Library) -> str:
    return library.model_dump_json(indent=2) + "\n"
