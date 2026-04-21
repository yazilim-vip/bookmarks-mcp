"""Chrome Bookmarks file backend.

Reads and writes the `Bookmarks` JSON file that Chromium-based browsers maintain
per profile (macOS default: `~/Library/Application Support/Google/Chrome/Default/Bookmarks`).

Chrome's on-disk format is preserved verbatim for unknown fields via an internal
raw-tree cache populated on `load()` and reused on `save()`. Bookmark ids are
Chrome `guid` values; timestamps are translated to/from WebKit microseconds.

Writes refuse to run while Chrome is running (can be forced with
BOOKMARKS_MCP_CHROME_FORCE=1) and always take a timestamped `.bak.<iso>` backup.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from filelock import FileLock

from bookmarks_mcp.models import Bookmark, Folder, Library
from bookmarks_mcp.storage.base import Storage

_WEBKIT_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)
_ROOT_KEYS = ("bookmark_bar", "other", "synced")
_ENV_FORCE = "BOOKMARKS_MCP_CHROME_FORCE"
_BACKUP_KEEP = 10


@dataclass(frozen=True)
class ChromePaths:
    bookmarks_file: Path
    profile: str


class ChromeBookmarksNotFoundError(FileNotFoundError):
    pass


class ChromeRunningError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Path / profile resolution
# ---------------------------------------------------------------------------


def _user_data_dir() -> Path:
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        return home / "Library" / "Application Support" / "Google" / "Chrome"
    if system == "Windows":
        local = os.environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        return Path(local) / "Google" / "Chrome" / "User Data"
    return home / ".config" / "google-chrome"


def resolve_chrome_paths(override: str | None = None, profile: str | None = None) -> ChromePaths:
    if override:
        p = Path(override).expanduser().resolve()
        return ChromePaths(bookmarks_file=p, profile=profile or p.parent.name)
    prof = profile or "Default"
    return ChromePaths(
        bookmarks_file=_user_data_dir() / prof / "Bookmarks",
        profile=prof,
    )


# ---------------------------------------------------------------------------
# Timestamp conversion
# ---------------------------------------------------------------------------


def _webkit_to_dt(raw: str | int | None) -> datetime:
    if raw in (None, "", "0"):
        return datetime.now(timezone.utc)
    try:
        return _WEBKIT_EPOCH + timedelta(microseconds=int(raw))
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def _dt_to_webkit(dt: datetime | None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = dt - _WEBKIT_EPOCH
    return str(int(delta.total_seconds() * 1_000_000))


# ---------------------------------------------------------------------------
# Chrome detection
# ---------------------------------------------------------------------------


def _chrome_running() -> bool:
    if os.environ.get(_ENV_FORCE) == "1":
        return False
    try:
        system = platform.system()
        if system == "Darwin" or system == "Linux":
            res = subprocess.run(
                ["pgrep", "-if", "google chrome|chromium"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return res.returncode == 0 and bool(res.stdout.strip())
        if system == "Windows":
            res = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            return "chrome.exe" in res.stdout.lower()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return False


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


class ChromeStorage(Storage):
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = FileLock(str(self.path) + ".bookmarks-mcp.lock")
        # Populated on load(); used by save() to preserve unknown fields and
        # the per-root container structure.
        self._raw: dict[str, Any] | None = None
        self._raw_by_guid: dict[str, dict[str, Any]] = {}

    # -- load ---------------------------------------------------------------

    def load(self) -> Library:
        if not self.path.exists():
            raise ChromeBookmarksNotFoundError(
                f"Chrome Bookmarks file not found: {self.path}. "
                "Check BOOKMARKS_MCP_CHROME_PROFILE or BOOKMARKS_MCP_CHROME_PATH."
            )
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._raw = raw
        self._raw_by_guid = {}
        library = Library()
        roots = raw.get("roots", {})
        for key in _ROOT_KEYS:
            node = roots.get(key)
            if not node:
                continue
            self._ingest_root(library, node)
        return library

    def _ingest_root(self, library: Library, node: dict[str, Any]) -> None:
        guid = node.get("guid") or node.get("id") or f"chrome-root-{node.get('name', 'root')}"
        self._raw_by_guid[guid] = node
        library.folders.append(
            Folder(
                id=guid,
                name=node.get("name") or "root",
                parent_id=None,
                created_at=_webkit_to_dt(node.get("date_added")),
                updated_at=_webkit_to_dt(node.get("date_modified") or node.get("date_added")),
            )
        )
        for child in node.get("children", []) or []:
            self._ingest_child(library, child, parent_guid=guid)

    def _ingest_child(self, library: Library, node: dict[str, Any], parent_guid: str) -> None:
        guid = node.get("guid") or node.get("id")
        if not guid:
            return  # malformed, skip
        self._raw_by_guid[guid] = node
        ntype = node.get("type")
        if ntype == "folder":
            library.folders.append(
                Folder(
                    id=guid,
                    name=node.get("name") or "",
                    parent_id=parent_guid,
                    created_at=_webkit_to_dt(node.get("date_added")),
                    updated_at=_webkit_to_dt(node.get("date_modified") or node.get("date_added")),
                )
            )
            for child in node.get("children", []) or []:
                self._ingest_child(library, child, parent_guid=guid)
        elif ntype == "url":
            url = node.get("url") or ""
            if "://" not in url:
                return  # pydantic validator would reject it
            library.bookmarks.append(
                Bookmark(
                    id=guid,
                    url=url,
                    title=node.get("name") or url,
                    folder_id=parent_guid,
                    tags=[],  # Chrome has no tags
                    created_at=_webkit_to_dt(node.get("date_added")),
                    updated_at=_webkit_to_dt(node.get("date_last_used") or node.get("date_added")),
                )
            )

    # -- save ---------------------------------------------------------------

    def save(self, library: Library) -> None:
        if _chrome_running():
            raise ChromeRunningError(
                "Google Chrome is running. Close it before writing, or set "
                f"{_ENV_FORCE}=1 to override (not recommended)."
            )
        if self._raw is None:
            # Populate raw cache if save() is called without a prior load().
            if self.path.exists():
                self.load()
            else:
                raise ChromeBookmarksNotFoundError(
                    f"Chrome Bookmarks file not found: {self.path}. "
                    "ChromeStorage cannot create a Bookmarks file from scratch."
                )

        assert self._raw is not None
        self._backup()
        new_raw = self._rebuild_raw(library)
        payload = json.dumps(new_raw, indent=3, ensure_ascii=False) + "\n"
        self._atomic_write(payload)
        self._raw = new_raw

    def _backup(self) -> None:
        if not self.path.exists():
            return
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = self.path.with_name(f"{self.path.name}.bak.{ts}")
        backup.write_bytes(self.path.read_bytes())
        # Prune to last N backups
        pattern = f"{self.path.name}.bak.*"
        backups = sorted(self.path.parent.glob(pattern))
        for old in backups[:-_BACKUP_KEEP]:
            try:
                old.unlink()
            except OSError:
                pass

    def _atomic_write(self, payload: str) -> None:
        fd, tmp_path = tempfile.mkstemp(
            prefix=".bookmarks-mcp-",
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

    def _rebuild_raw(self, library: Library) -> dict[str, Any]:
        assert self._raw is not None
        folders_by_id = {f.id: f for f in library.folders}
        children_by_parent: dict[str | None, list[Any]] = {}
        for f in library.folders:
            children_by_parent.setdefault(f.parent_id, []).append(f)
        for b in library.bookmarks:
            children_by_parent.setdefault(b.folder_id, []).append(b)

        # Start from a deep copy of the original raw tree, then update each
        # root's children array in place. Unknown top-level keys are preserved.
        new_raw = _deep_copy(self._raw)
        # Scrub checksum — Chrome regenerates it.
        new_raw.pop("checksum", None)
        roots = new_raw.setdefault("roots", {})

        # Identify which top-level Library folders map to which Chrome root.
        # Match by guid first (preserves identity across reads/writes), then
        # fall back to name match. Anything without a root falls into "other".
        root_folder_by_key: dict[str, Folder | None] = {k: None for k in _ROOT_KEYS}
        raw_roots_by_guid: dict[str, str] = {}
        for key in _ROOT_KEYS:
            node = roots.get(key)
            if node and node.get("guid"):
                raw_roots_by_guid[node["guid"]] = key

        top_level_folders = [f for f in library.folders if f.parent_id is None]
        for f in top_level_folders:
            key = raw_roots_by_guid.get(f.id)
            if key is None:
                # Name fallback
                name = (f.name or "").lower()
                if "bookmark" in name and "bar" in name:
                    key = "bookmark_bar"
                elif "mobile" in name or "sync" in name:
                    key = "synced"
                else:
                    key = "other"
            if root_folder_by_key[key] is None:
                root_folder_by_key[key] = f

        orphan_bookmarks = [b for b in library.bookmarks if b.folder_id is None]

        for key in _ROOT_KEYS:
            root_node = roots.get(key)
            if not root_node:
                continue
            root_folder = root_folder_by_key[key]
            root_node["type"] = "folder"
            if root_folder is not None:
                root_node["name"] = root_folder.name
                root_node["date_modified"] = _dt_to_webkit(root_folder.updated_at)
                children_source = children_by_parent.get(root_folder.id, [])
            else:
                children_source = []
            if key == "other" and orphan_bookmarks:
                children_source = list(children_source) + orphan_bookmarks
            root_node["children"] = [
                self._node_for(child, children_by_parent, folders_by_id) for child in children_source
            ]

        return new_raw

    def _node_for(
        self,
        item: Folder | Bookmark,
        children_by_parent: dict[str | None, list[Any]],
        folders_by_id: dict[str, Folder],
    ) -> dict[str, Any]:
        raw = _deep_copy(self._raw_by_guid.get(item.id, {}))
        if isinstance(item, Folder):
            raw["type"] = "folder"
            raw["id"] = raw.get("id") or item.id
            raw["guid"] = raw.get("guid") or item.id
            raw["name"] = item.name
            raw["date_added"] = raw.get("date_added") or _dt_to_webkit(item.created_at)
            raw["date_modified"] = _dt_to_webkit(item.updated_at)
            raw["children"] = [
                self._node_for(c, children_by_parent, folders_by_id) for c in children_by_parent.get(item.id, [])
            ]
            return raw
        # Bookmark
        raw["type"] = "url"
        raw["id"] = raw.get("id") or item.id
        raw["guid"] = raw.get("guid") or item.id
        raw["name"] = item.title
        raw["url"] = str(item.url)
        raw["date_added"] = raw.get("date_added") or _dt_to_webkit(item.created_at)
        if item.updated_at:
            raw["date_last_used"] = _dt_to_webkit(item.updated_at)
        return raw

    # -- transaction --------------------------------------------------------

    @contextmanager
    def transaction(self) -> Iterator[Library]:
        with self._lock:
            library = self.load()
            yield library
            self.save(library)


def _deep_copy(obj: Any) -> Any:
    # json round-trip is faster than copy.deepcopy for JSON-shaped data.
    return json.loads(json.dumps(obj)) if obj else ({} if isinstance(obj, dict) else obj)


def _stderr(msg: str) -> None:
    print(msg, file=sys.stderr)
