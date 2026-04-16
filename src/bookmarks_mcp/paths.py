from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "bookmarks-mcp"
ENV_DB_PATH = "BOOKMARKS_MCP_DB"


def default_db_path() -> Path:
    override = os.environ.get(ENV_DB_PATH)
    if override:
        return Path(override).expanduser().resolve()
    return Path(user_data_dir(APP_NAME, appauthor=False)) / "bookmarks.json"
