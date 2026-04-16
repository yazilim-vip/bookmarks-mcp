from __future__ import annotations

from pathlib import Path

from bookmarks_mcp.models import Library


class Storage:
    """JSON-on-disk storage with atomic writes. Implementation lands in the storage task."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Library:
        raise NotImplementedError("Storage.load — implemented in the storage task")

    def save(self, library: Library) -> None:
        raise NotImplementedError("Storage.save — implemented in the storage task")
