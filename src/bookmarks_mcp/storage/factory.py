from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from bookmarks_mcp.paths import default_db_path
from bookmarks_mcp.storage.base import Storage
from bookmarks_mcp.storage.json_file import JsonFileStorage

ENV_BACKEND = "BOOKMARKS_MCP_BACKEND"
ENV_CHROME_PROFILE = "BOOKMARKS_MCP_CHROME_PROFILE"
ENV_CHROME_PATH = "BOOKMARKS_MCP_CHROME_PATH"

BACKEND_JSON = "json"
BACKEND_CHROME = "chrome"

SUPPORTED_BACKENDS = (BACKEND_JSON, BACKEND_CHROME)


@dataclass(frozen=True)
class BackendInfo:
    name: str
    target: Path
    profile: str | None = None
    supports_tags: bool = True


def _resolve_backend() -> str:
    raw = os.environ.get(ENV_BACKEND, BACKEND_JSON).strip().lower()
    if raw not in SUPPORTED_BACKENDS:
        supported = ", ".join(SUPPORTED_BACKENDS)
        raise ValueError(f"Unknown {ENV_BACKEND}={raw!r}. Supported backends: {supported}")
    return raw


def describe_backend() -> BackendInfo:
    """Resolve the active backend and its target path, without constructing it."""
    backend = _resolve_backend()
    if backend == BACKEND_CHROME:
        from bookmarks_mcp.storage.chrome import resolve_chrome_paths

        paths = resolve_chrome_paths(
            override=os.environ.get(ENV_CHROME_PATH),
            profile=os.environ.get(ENV_CHROME_PROFILE),
        )
        return BackendInfo(
            name=BACKEND_CHROME,
            target=paths.bookmarks_file,
            profile=paths.profile,
            supports_tags=False,
        )
    return BackendInfo(name=BACKEND_JSON, target=default_db_path())


def create_storage() -> Storage:
    """Return the Storage implementation selected by environment variables."""
    info = describe_backend()
    if info.name == BACKEND_CHROME:
        from bookmarks_mcp.storage.chrome import ChromeStorage

        return ChromeStorage(info.target)
    return JsonFileStorage(info.target)
