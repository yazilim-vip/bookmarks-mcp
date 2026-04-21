from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from filelock import FileLock

from bookmarks_mcp.models import Library
from bookmarks_mcp.storage.base import Storage


class JsonFileStorage(Storage):
    """JSON-on-disk persistence for the Library document.

    - Atomic writes via tmp-file + fsync + rename.
    - Cross-process write serialization via an advisory file lock.
    - Transaction helper yields a mutable Library and saves on clean exit.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = FileLock(str(self.path) + ".lock")

    def _ensure_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Library:
        self._ensure_parent()
        if not self.path.exists():
            return Library()
        data = self.path.read_text(encoding="utf-8")
        if not data.strip():
            return Library()
        return Library.model_validate_json(data)

    def save(self, library: Library) -> None:
        self._ensure_parent()
        payload = library.model_dump_json(indent=2) + "\n"
        fd, tmp_path = tempfile.mkstemp(
            prefix=".bookmarks-",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            raise

    @contextmanager
    def transaction(self) -> Iterator[Library]:
        with self._lock:
            library = self.load()
            yield library
            self.save(library)
