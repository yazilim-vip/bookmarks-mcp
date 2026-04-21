from __future__ import annotations

from bookmarks_mcp.storage.base import Storage
from bookmarks_mcp.storage.factory import create_storage, describe_backend
from bookmarks_mcp.storage.json_file import JsonFileStorage

__all__ = [
    "JsonFileStorage",
    "Storage",
    "create_storage",
    "describe_backend",
]
