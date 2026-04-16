from __future__ import annotations

from pathlib import Path

import pytest

from bookmarks_mcp.service import BookmarkService
from bookmarks_mcp.storage import Storage


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "bookmarks.json")


@pytest.fixture
def service(storage: Storage) -> BookmarkService:
    return BookmarkService(storage)
