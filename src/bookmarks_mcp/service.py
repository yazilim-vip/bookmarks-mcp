from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from bookmarks_mcp.errors import (
    BookmarkNotFoundError,
    FolderCycleError,
    FolderNotEmptyError,
    FolderNotFoundError,
    ReorderMismatchError,
)
from bookmarks_mcp.models import Bookmark, Folder, Library, normalize_tag
from bookmarks_mcp.storage import Storage


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _descendant_ids(library: Library, folder_id: str) -> set[str]:
    children_by_parent: dict[str, list[str]] = {}
    for f in library.folders:
        children_by_parent.setdefault(f.parent_id or "", []).append(f.id)
    out: set[str] = set()
    stack = list(children_by_parent.get(folder_id, []))
    while stack:
        cur = stack.pop()
        if cur in out:
            continue
        out.add(cur)
        stack.extend(children_by_parent.get(cur, []))
    return out


def _next_position(library: Library, parent_id: str | None) -> int:
    """Next sibling position within ``parent_id`` (folders + bookmarks combined).

    Returns ``max(siblings.position) + 1`` so freshly created / moved items land
    at the end of the parent's children list. Returns 0 for an empty parent.
    """
    highest = -1
    for f in library.folders:
        if f.parent_id == parent_id and f.position > highest:
            highest = f.position
    for b in library.bookmarks:
        if b.folder_id == parent_id and b.position > highest:
            highest = b.position
    return highest + 1


def _siblings_ordered(library: Library, parent_id: str | None) -> list[Folder | Bookmark]:
    """Return direct children (folders + bookmarks) of parent_id in (position, id) order."""
    items: list[Folder | Bookmark] = []
    for f in library.folders:
        if f.parent_id == parent_id:
            items.append(f)
    for b in library.bookmarks:
        if b.folder_id == parent_id:
            items.append(b)
    items.sort(key=lambda it: (it.position, it.id))
    return items


def _insert_and_renumber(
    library: Library,
    parent_id: str | None,
    moving_item: Folder | Bookmark,
    index: int | None,
) -> None:
    """Place ``moving_item`` at ``index`` among parent's children and assign dense 0..N positions.

    ``index=None`` appends at the end. ``index`` is clamped at the upper end; negative
    values are rejected by the caller. The moving item must already be configured with
    its new parent (``folder.parent_id`` / ``bookmark.folder_id``) before calling.
    """
    siblings = [it for it in _siblings_ordered(library, parent_id) if it.id != moving_item.id]
    if index is None or index >= len(siblings):
        siblings.append(moving_item)
    else:
        siblings.insert(index, moving_item)
    for pos, item in enumerate(siblings):
        item.position = pos


def _would_create_cycle(library: Library, folder_id: str, new_parent_id: str | None) -> bool:
    if new_parent_id is None:
        return False
    if new_parent_id == folder_id:
        return True
    by_id = {f.id: f for f in library.folders}
    current = by_id.get(new_parent_id)
    visited: set[str] = set()
    while current is not None and current.id not in visited:
        if current.id == folder_id:
            return True
        visited.add(current.id)
        if current.parent_id is None:
            return False
        current = by_id.get(current.parent_id)
    return False


class BookmarkService:
    """High-level bookmark operations shared by the MCP server and the web UI."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _require_folder(library: Library, folder_id: str) -> Folder:
        folder = next((f for f in library.folders if f.id == folder_id), None)
        if folder is None:
            raise FolderNotFoundError(folder_id)
        return folder

    @staticmethod
    def _require_bookmark(library: Library, bookmark_id: str) -> Bookmark:
        bookmark = next((b for b in library.bookmarks if b.id == bookmark_id), None)
        if bookmark is None:
            raise BookmarkNotFoundError(bookmark_id)
        return bookmark

    # -----------------------------------------------------------------
    # Folders
    # -----------------------------------------------------------------

    def list_folders(self, parent_id: str | None = None) -> list[Folder]:
        library = self.storage.load()
        return [f for f in library.folders if f.parent_id == parent_id]

    def list_all_folders(self) -> list[Folder]:
        return list(self.storage.load().folders)

    def get_folder(self, folder_id: str) -> Folder | None:
        library = self.storage.load()
        return next((f for f in library.folders if f.id == folder_id), None)

    def create_folder(self, name: str, parent_id: str | None = None) -> Folder:
        with self.storage.transaction() as library:
            if parent_id is not None:
                self._require_folder(library, parent_id)
            folder = Folder(
                name=name,
                parent_id=parent_id,
                position=_next_position(library, parent_id),
            )
            library.folders.append(folder)
        return folder

    def rename_folder(self, folder_id: str, name: str) -> Folder:
        with self.storage.transaction() as library:
            folder = self._require_folder(library, folder_id)
            folder.name = name
            folder.updated_at = _now()
        return folder

    def move_folder(self, folder_id: str, parent_id: str | None, index: int | None = None) -> Folder:
        if index is not None and index < 0:
            raise ValueError(f"index must be non-negative, got {index}")
        with self.storage.transaction() as library:
            folder = self._require_folder(library, folder_id)
            if parent_id is not None:
                self._require_folder(library, parent_id)
            if _would_create_cycle(library, folder_id, parent_id):
                raise FolderCycleError(folder_id, parent_id)
            folder.parent_id = parent_id
            _insert_and_renumber(library, parent_id, folder, index)
            folder.updated_at = _now()
        return folder

    def delete_folder(self, folder_id: str, recursive: bool = False) -> int:
        with self.storage.transaction() as library:
            self._require_folder(library, folder_id)
            descendants = _descendant_ids(library, folder_id)
            affected_ids = {folder_id, *descendants}
            has_children = bool(descendants)
            has_bookmarks = any(b.folder_id in affected_ids for b in library.bookmarks)
            if not recursive and (has_children or has_bookmarks):
                raise FolderNotEmptyError(folder_id)
            library.folders = [f for f in library.folders if f.id not in affected_ids]
            library.bookmarks = [b for b in library.bookmarks if b.folder_id not in affected_ids]
        return len(affected_ids)

    # -----------------------------------------------------------------
    # Bookmarks
    # -----------------------------------------------------------------

    def list_bookmarks(
        self,
        folder_id: str | None = None,
        tag: str | None = None,
        query: str | None = None,
        limit: int | None = None,
    ) -> list[Bookmark]:
        library = self.storage.load()
        out = list(library.bookmarks)
        if folder_id is not None:
            out = [b for b in out if b.folder_id == folder_id]
        if tag:
            tag_norm = normalize_tag(tag)
            if tag_norm:
                out = [b for b in out if tag_norm in b.tags]
        if query:
            q = query.lower()
            out = [b for b in out if q in b.title.lower() or q in b.url.lower() or q in (b.description or "").lower()]
        if limit is not None and limit >= 0:
            out = out[:limit]
        return out

    def get_bookmark(self, bookmark_id: str) -> Bookmark | None:
        library = self.storage.load()
        return next((b for b in library.bookmarks if b.id == bookmark_id), None)

    def add_bookmark(
        self,
        url: str,
        title: str,
        folder_id: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
    ) -> Bookmark:
        with self.storage.transaction() as library:
            if folder_id is not None:
                self._require_folder(library, folder_id)
            bookmark = Bookmark(
                url=url,
                title=title,
                folder_id=folder_id,
                tags=tags or [],
                description=description,
                position=_next_position(library, folder_id),
            )
            library.bookmarks.append(bookmark)
        return bookmark

    def update_bookmark(
        self,
        bookmark_id: str,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        url: str | None = None,
    ) -> Bookmark:
        with self.storage.transaction() as library:
            bookmark = self._require_bookmark(library, bookmark_id)
            if title is not None:
                bookmark.title = title
            if description is not None:
                bookmark.description = description
            if tags is not None:
                bookmark.tags = tags
            if url is not None:
                bookmark.url = url
            bookmark.updated_at = _now()
        return bookmark

    def move_bookmark(self, bookmark_id: str, folder_id: str | None, index: int | None = None) -> Bookmark:
        if index is not None and index < 0:
            raise ValueError(f"index must be non-negative, got {index}")
        with self.storage.transaction() as library:
            bookmark = self._require_bookmark(library, bookmark_id)
            if folder_id is not None:
                self._require_folder(library, folder_id)
            bookmark.folder_id = folder_id
            _insert_and_renumber(library, folder_id, bookmark, index)
            bookmark.updated_at = _now()
        return bookmark

    def delete_bookmark(self, bookmark_id: str) -> None:
        with self.storage.transaction() as library:
            self._require_bookmark(library, bookmark_id)
            library.bookmarks = [b for b in library.bookmarks if b.id != bookmark_id]

    # -----------------------------------------------------------------
    # Ordering
    # -----------------------------------------------------------------

    def reorder_children(self, parent_id: str | None, ordered_ids: list[str]) -> int:
        """Reorder ``parent_id``'s direct children (folders + bookmarks combined).

        ``ordered_ids`` must be a permutation of the parent's current direct children.
        Assigns ``position = 0..N-1`` in the given order. Returns the number of
        reordered children. Atomic within a single storage transaction.
        """
        with self.storage.transaction() as library:
            if parent_id is not None:
                self._require_folder(library, parent_id)
            current = _siblings_ordered(library, parent_id)
            current_ids = {it.id for it in current}
            provided_ids = set(ordered_ids)
            if len(ordered_ids) != len(set(ordered_ids)):
                raise ReorderMismatchError(parent_id, "ordered_ids contains duplicates")
            unknown = provided_ids - current_ids
            if unknown:
                raise ReorderMismatchError(
                    parent_id,
                    f"ids not direct children of this parent: {sorted(unknown)}",
                )
            missing = current_ids - provided_ids
            if missing:
                raise ReorderMismatchError(
                    parent_id,
                    f"ordered_ids is missing current children: {sorted(missing)}",
                )
            by_id: dict[str, Folder | Bookmark] = {it.id: it for it in current}
            now = _now()
            for pos, child_id in enumerate(ordered_ids):
                item = by_id[child_id]
                item.position = pos
                item.updated_at = now
        return len(ordered_ids)

    # -----------------------------------------------------------------
    # Tags
    # -----------------------------------------------------------------

    def list_tags(self) -> dict[str, int]:
        library = self.storage.load()
        counter: Counter[str] = Counter()
        for b in library.bookmarks:
            counter.update(b.tags)
        return dict(counter.most_common())

    def rename_tag(self, old: str, new: str) -> int:
        old_norm = normalize_tag(old)
        new_norm = normalize_tag(new)
        if not old_norm or not new_norm:
            return 0
        if old_norm == new_norm:
            return 0
        affected = 0
        with self.storage.transaction() as library:
            for bookmark in library.bookmarks:
                if old_norm in bookmark.tags:
                    updated = [new_norm if t == old_norm else t for t in bookmark.tags]
                    bookmark.tags = updated  # validator dedupes
                    bookmark.updated_at = _now()
                    affected += 1
        return affected

    def delete_tag(self, tag: str) -> int:
        tag_norm = normalize_tag(tag)
        if not tag_norm:
            return 0
        affected = 0
        with self.storage.transaction() as library:
            for bookmark in library.bookmarks:
                if tag_norm in bookmark.tags:
                    bookmark.tags = [t for t in bookmark.tags if t != tag_norm]
                    bookmark.updated_at = _now()
                    affected += 1
        return affected

    # -----------------------------------------------------------------
    # Stats
    # -----------------------------------------------------------------

    def stats(self) -> dict[str, int]:
        library = self.storage.load()
        tags = {t for b in library.bookmarks for t in b.tags}
        return {
            "bookmarks": len(library.bookmarks),
            "folders": len(library.folders),
            "tags": len(tags),
        }
