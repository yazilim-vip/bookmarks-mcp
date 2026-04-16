from __future__ import annotations

import pytest

from bookmarks_mcp.errors import (
    BookmarkNotFoundError,
    FolderCycleError,
    FolderNotEmptyError,
    FolderNotFoundError,
)
from bookmarks_mcp.service import BookmarkService


def test_create_and_list_folders(service: BookmarkService):
    root = service.create_folder("Reading")
    child = service.create_folder("AI", parent_id=root.id)

    top_level = service.list_folders(parent_id=None)
    assert [f.id for f in top_level] == [root.id]

    sub = service.list_folders(parent_id=root.id)
    assert [f.id for f in sub] == [child.id]


def test_create_folder_with_unknown_parent_raises(service: BookmarkService):
    with pytest.raises(FolderNotFoundError):
        service.create_folder("Orphan", parent_id="does-not-exist")


def test_rename_folder(service: BookmarkService):
    folder = service.create_folder("Old")
    renamed = service.rename_folder(folder.id, "New")
    assert renamed.name == "New"
    assert renamed.updated_at >= folder.updated_at


def test_move_folder_detects_cycle(service: BookmarkService):
    a = service.create_folder("A")
    b = service.create_folder("B", parent_id=a.id)
    with pytest.raises(FolderCycleError):
        service.move_folder(a.id, b.id)


def test_move_folder_self_parent_rejected(service: BookmarkService):
    a = service.create_folder("A")
    with pytest.raises(FolderCycleError):
        service.move_folder(a.id, a.id)


def test_delete_folder_requires_recursive_when_has_children(service: BookmarkService):
    a = service.create_folder("A")
    service.create_folder("B", parent_id=a.id)
    with pytest.raises(FolderNotEmptyError):
        service.delete_folder(a.id)
    removed = service.delete_folder(a.id, recursive=True)
    assert removed == 2
    assert service.list_all_folders() == []


def test_delete_folder_recursive_removes_contained_bookmarks(service: BookmarkService):
    a = service.create_folder("A")
    b = service.create_folder("B", parent_id=a.id)
    service.add_bookmark(url="https://x.example", title="X", folder_id=b.id)
    service.delete_folder(a.id, recursive=True)
    assert service.list_bookmarks() == []


def test_add_bookmark_with_unknown_folder_raises(service: BookmarkService):
    with pytest.raises(FolderNotFoundError):
        service.add_bookmark(url="https://a.example", title="A", folder_id="nope")


def test_list_bookmarks_filters_by_folder_tag_and_query(service: BookmarkService):
    work = service.create_folder("Work")
    service.add_bookmark(url="https://py.example", title="Python Docs", folder_id=work.id, tags=["python"])
    service.add_bookmark(url="https://go.example", title="Go Docs", folder_id=work.id, tags=["go"])
    service.add_bookmark(url="https://news.example", title="News", tags=["news"])

    assert len(service.list_bookmarks(folder_id=work.id)) == 2
    assert [b.title for b in service.list_bookmarks(tag="python")] == ["Python Docs"]
    assert [b.title for b in service.list_bookmarks(query="docs")] == ["Python Docs", "Go Docs"]


def test_update_bookmark_changes_fields(service: BookmarkService):
    b = service.add_bookmark(url="https://a.example", title="A", tags=["one"])
    updated = service.update_bookmark(b.id, title="A2", tags=["two", "three"])
    assert updated.title == "A2"
    assert updated.tags == ["two", "three"]
    assert updated.updated_at >= b.updated_at


def test_move_bookmark_to_folder(service: BookmarkService):
    folder = service.create_folder("F")
    b = service.add_bookmark(url="https://a.example", title="A")
    moved = service.move_bookmark(b.id, folder.id)
    assert moved.folder_id == folder.id
    back = service.move_bookmark(b.id, None)
    assert back.folder_id is None


def test_delete_bookmark(service: BookmarkService):
    b = service.add_bookmark(url="https://a.example", title="A")
    service.delete_bookmark(b.id)
    with pytest.raises(BookmarkNotFoundError):
        service.delete_bookmark(b.id)


def test_list_tags_counts(service: BookmarkService):
    service.add_bookmark(url="https://a.example", title="A", tags=["python", "web"])
    service.add_bookmark(url="https://b.example", title="B", tags=["python"])
    tags = service.list_tags()
    assert tags == {"python": 2, "web": 1}


def test_rename_tag_merges_on_collision(service: BookmarkService):
    a = service.add_bookmark(url="https://a.example", title="A", tags=["py"])
    b = service.add_bookmark(url="https://b.example", title="B", tags=["py", "python"])
    affected = service.rename_tag("py", "python")
    assert affected == 2
    assert service.get_bookmark(a.id).tags == ["python"]
    assert service.get_bookmark(b.id).tags == ["python"]


def test_delete_tag_removes_from_all_bookmarks(service: BookmarkService):
    a = service.add_bookmark(url="https://a.example", title="A", tags=["keep", "drop"])
    service.add_bookmark(url="https://b.example", title="B", tags=["drop"])
    affected = service.delete_tag("drop")
    assert affected == 2
    assert service.get_bookmark(a.id).tags == ["keep"]


def test_stats(service: BookmarkService):
    f = service.create_folder("F")
    service.add_bookmark(url="https://a.example", title="A", folder_id=f.id, tags=["x", "y"])
    service.add_bookmark(url="https://b.example", title="B", tags=["y"])
    assert service.stats() == {"bookmarks": 2, "folders": 1, "tags": 2}
