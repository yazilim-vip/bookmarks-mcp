from __future__ import annotations

import sys

from bookmarks_mcp.service import BookmarkService
from bookmarks_mcp.storage import create_storage, describe_backend
from bookmarks_mcp.storage.factory import ENV_BACKEND, ENV_CHROME_PATH, ENV_CHROME_PROFILE


def print_info() -> None:
    info = describe_backend()
    print(f"backend:      {info.name}")
    print(f"target:       {info.target}")
    print(f"exists:       {info.target.exists()}")
    if info.profile:
        print(f"profile:      {info.profile}")
    print(f"tags:         {'supported' if info.supports_tags else 'disabled (chrome backend)'}")
    print(f"env vars:     ${ENV_BACKEND}, ${ENV_CHROME_PROFILE}, ${ENV_CHROME_PATH}")
    if info.target.exists():
        stats = BookmarkService(create_storage()).stats()
        print(f"bookmarks:    {stats['bookmarks']}")
        print(f"folders:      {stats['folders']}")
        if info.supports_tags:
            print(f"tag count:    {stats['tags']}")
    sys.stdout.flush()
