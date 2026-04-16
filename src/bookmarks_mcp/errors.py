from __future__ import annotations


class BookmarksError(Exception):
    """Base class for domain errors raised by the service layer."""


class FolderNotFoundError(BookmarksError):
    def __init__(self, folder_id: str) -> None:
        super().__init__(f"folder not found: {folder_id}")
        self.folder_id = folder_id


class BookmarkNotFoundError(BookmarksError):
    def __init__(self, bookmark_id: str) -> None:
        super().__init__(f"bookmark not found: {bookmark_id}")
        self.bookmark_id = bookmark_id


class FolderCycleError(BookmarksError):
    def __init__(self, folder_id: str, parent_id: str | None) -> None:
        super().__init__(f"moving folder {folder_id} under {parent_id} would create a cycle")
        self.folder_id = folder_id
        self.parent_id = parent_id


class FolderNotEmptyError(BookmarksError):
    def __init__(self, folder_id: str) -> None:
        super().__init__(f"folder {folder_id} is not empty; pass recursive=true to delete contents")
        self.folder_id = folder_id


class TagNotFoundError(BookmarksError):
    def __init__(self, tag: str) -> None:
        super().__init__(f"tag not found: {tag}")
        self.tag = tag
