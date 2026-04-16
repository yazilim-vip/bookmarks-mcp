from __future__ import annotations

import sys

from bookmarks_mcp.paths import ENV_DB_PATH, default_db_path


def print_info() -> None:
    path = default_db_path()
    print(f"storage path: {path}")
    print(f"exists:       {path.exists()}")
    print(f"override env: ${ENV_DB_PATH}")
    sys.stdout.flush()
