from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from bookmarks_mcp.service import BookmarkService
from bookmarks_mcp.storage import create_storage

mcp: FastMCP = FastMCP("bookmarks-mcp")

_service: BookmarkService | None = None


def get_service() -> BookmarkService:
    global _service
    if _service is None:
        _service = BookmarkService(create_storage())
    return _service


def set_service(service: BookmarkService | None) -> None:
    """Test hook: replace (or clear with `None`) the cached service instance."""
    global _service
    _service = service


def _dump(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json")


# ---------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------


@mcp.tool
def list_folders(parent_id: str | None = None) -> list[dict[str, Any]]:
    """List folders directly under the given parent. Pass parent_id=None for root-level folders."""
    return [_dump(f) for f in get_service().list_folders(parent_id)]


@mcp.tool
def list_all_folders() -> list[dict[str, Any]]:
    """Return every folder in the library, regardless of nesting level."""
    return [_dump(f) for f in get_service().list_all_folders()]


@mcp.tool
def get_folder(folder_id: str) -> dict[str, Any] | None:
    """Fetch a single folder by id, or None if it does not exist."""
    folder = get_service().get_folder(folder_id)
    return _dump(folder) if folder else None


@mcp.tool
def create_folder(name: str, parent_id: str | None = None) -> dict[str, Any]:
    """Create a new folder. Omit parent_id to create at root level."""
    return _dump(get_service().create_folder(name, parent_id))


@mcp.tool
def rename_folder(folder_id: str, name: str) -> dict[str, Any]:
    """Rename a folder."""
    return _dump(get_service().rename_folder(folder_id, name))


@mcp.tool
def move_folder(folder_id: str, parent_id: str | None, index: int | None = None) -> dict[str, Any]:
    """Move a folder under a new parent. Pass parent_id=None to move to root. Cycles are rejected.

    Optional index inserts the folder at a specific slot among the new parent's children
    (folders + bookmarks combined, sorted by position). index=0 is first; index >= sibling
    count or index=None appends at the end. Negative values raise ValueError.
    """
    return _dump(get_service().move_folder(folder_id, parent_id, index))


@mcp.tool
def delete_folder(folder_id: str, recursive: bool = False) -> str:
    """Delete a folder. Set recursive=True to also remove subfolders and contained bookmarks."""
    removed = get_service().delete_folder(folder_id, recursive)
    return f"deleted {removed} folder(s)"


# ---------------------------------------------------------------------
# Bookmarks
# ---------------------------------------------------------------------


@mcp.tool
def list_bookmarks(
    folder_id: str | None = None,
    tag: str | None = None,
    query: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List bookmarks. Optional filters: folder_id (exact match), tag (slugified), query (substring search)."""
    return [_dump(b) for b in get_service().list_bookmarks(folder_id, tag, query, limit)]


@mcp.tool
def get_bookmark(bookmark_id: str) -> dict[str, Any] | None:
    """Fetch a single bookmark by id, or None if it does not exist."""
    bookmark = get_service().get_bookmark(bookmark_id)
    return _dump(bookmark) if bookmark else None


@mcp.tool
def add_bookmark(
    url: str,
    title: str,
    folder_id: str | None = None,
    tags: list[str] | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Add a new bookmark. Tags are slugified (lowercase, dash-separated) and deduped."""
    return _dump(get_service().add_bookmark(url, title, folder_id, tags, description))


@mcp.tool
def update_bookmark(
    bookmark_id: str,
    title: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """Update fields on a bookmark. Only fields you pass are changed; pass tags=[] to clear all tags."""
    return _dump(get_service().update_bookmark(bookmark_id, title, description, tags, url))


@mcp.tool
def move_bookmark(bookmark_id: str, folder_id: str | None, index: int | None = None) -> dict[str, Any]:
    """Move a bookmark to a different folder. Pass folder_id=None to move to root.

    Optional index inserts the bookmark at a specific slot among the new parent's children
    (folders + bookmarks combined, sorted by position). index=0 is first; index >= sibling
    count or index=None appends at the end. Negative values raise ValueError.
    """
    return _dump(get_service().move_bookmark(bookmark_id, folder_id, index))


@mcp.tool
def delete_bookmark(bookmark_id: str) -> str:
    """Delete a bookmark by id."""
    get_service().delete_bookmark(bookmark_id)
    return f"deleted bookmark {bookmark_id}"


# ---------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------


@mcp.tool
def list_tags() -> dict[str, int]:
    """List every tag with the number of bookmarks that use it."""
    return get_service().list_tags()


@mcp.tool
def rename_tag(old: str, new: str) -> str:
    """Rename a tag across all bookmarks. If the new tag already exists on a bookmark, the duplicate is dropped."""
    affected = get_service().rename_tag(old, new)
    return f"renamed tag on {affected} bookmark(s)"


@mcp.tool
def delete_tag(tag: str) -> str:
    """Remove a tag from every bookmark that has it."""
    affected = get_service().delete_tag(tag)
    return f"removed tag from {affected} bookmark(s)"


# ---------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------


@mcp.tool
def reorder_children(parent_id: str | None, ordered_ids: list[str]) -> str:
    """Reorder the direct children (folders + bookmarks) of a parent.

    ``ordered_ids`` must be a permutation of the parent's current direct children —
    every existing child must appear exactly once; unknown ids or ids belonging to
    another parent are rejected. Assigns position = 0..N-1 in the given order.

    Pass parent_id=None to target the root level. Note on the Chrome backend: the root
    level contains the three Chrome root folders (Bookmarks Bar, Other, Mobile) as
    peers; pass one of those folder ids (not None) to reorder inside one of them.
    """
    count = get_service().reorder_children(parent_id, ordered_ids)
    return f"reordered {count} child(ren)"


# ---------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------


@mcp.tool
def stats() -> dict[str, int]:
    """Return total counts of bookmarks, folders, and tags."""
    return get_service().stats()


def run_mcp() -> None:
    mcp.run()
