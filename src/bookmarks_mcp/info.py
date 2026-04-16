from __future__ import annotations

import sys

from bookmarks_mcp.paths import ENV_DB_PATH, default_db_path
from bookmarks_mcp.service import BookmarkService
from bookmarks_mcp.storage import Storage


def print_info() -> None:
    path = default_db_path()
    print(f"storage path: {path}")
    print(f"exists:       {path.exists()}")
    print(f"override env: ${ENV_DB_PATH}")
    if path.exists():
        stats = BookmarkService(Storage(path)).stats()
        print(f"bookmarks:    {stats['bookmarks']}")
        print(f"folders:      {stats['folders']}")
        print(f"tags:         {stats['tags']}")
    sys.stdout.flush()
