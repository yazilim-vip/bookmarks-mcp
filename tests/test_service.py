from __future__ import annotations

import pytest

from bookmarks_mcp.errors import (
    BookmarkNotFoundError,
    FolderCycleError,
    FolderNotEmptyError,
    FolderNotFoundError,
    ReorderMismatchError,
)
from bookmarks_mcp.service import BookmarkService


def _ordered_child_ids(service: BookmarkService, parent_id):
    folders = [(f.position, f.id) for f in service.list_folders(parent_id)]
    bookmarks = [(b.position, b.id) for b in service.list_bookmarks(folder_id=parent_id)]
    combined = sorted(folders + bookmarks, key=lambda it: (it[0], it[1]))
    return [cid for _, cid in combined]


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


def test_add_bookmark_appends_at_end_of_non_empty_folder(service: BookmarkService):
    parent = service.create_folder("P")
    a = service.add_bookmark(url="https://a.example", title="A", folder_id=parent.id)
    b = service.add_bookmark(url="https://b.example", title="B", folder_id=parent.id)
    c = service.add_bookmark(url="https://c.example", title="C", folder_id=parent.id)
    positions = [a.position, b.position, c.position]
    assert positions == sorted(positions)
    assert len(set(positions)) == 3


def test_move_bookmark_into_parent_lands_at_end(service: BookmarkService):
    parent = service.create_folder("P")
    a = service.add_bookmark(url="https://a.example", title="A", folder_id=parent.id)
    b = service.add_bookmark(url="https://b.example", title="B", folder_id=parent.id)
    c = service.add_bookmark(url="https://c.example", title="C", folder_id=parent.id)
    x = service.add_bookmark(url="https://x.example", title="X")  # outside

    moved = service.move_bookmark(x.id, parent.id)
    max_sibling_pos = max(a.position, b.position, c.position)
    assert moved.position > max_sibling_pos


def test_move_bookmark_to_other_parent_leaves_remaining_order(service: BookmarkService):
    src = service.create_folder("Src")
    dst = service.create_folder("Dst")
    a = service.add_bookmark(url="https://a.example", title="A", folder_id=src.id)
    b = service.add_bookmark(url="https://b.example", title="B", folder_id=src.id)
    c = service.add_bookmark(url="https://c.example", title="C", folder_id=src.id)
    d = service.add_bookmark(url="https://d.example", title="D", folder_id=dst.id)

    service.move_bookmark(b.id, dst.id)

    # Remaining in src: A, C in original relative order.
    src_items = sorted(
        [bm for bm in service.list_bookmarks(folder_id=src.id)],
        key=lambda bm: (bm.position, bm.id),
    )
    assert [bm.title for bm in src_items] == ["A", "C"]
    assert a.position < c.position  # unchanged

    # B lands at end of dst, after D.
    moved_b = service.get_bookmark(b.id)
    d_refreshed = service.get_bookmark(d.id)
    assert moved_b.position > d_refreshed.position


def test_move_folder_lands_at_end_of_new_parent(service: BookmarkService):
    dst = service.create_folder("Dst")
    child1 = service.create_folder("C1", parent_id=dst.id)
    child2 = service.create_folder("C2", parent_id=dst.id)
    orphan = service.create_folder("Orphan")  # top-level

    moved = service.move_folder(orphan.id, dst.id)
    assert moved.position > max(child1.position, child2.position)


def test_move_bookmark_with_explicit_index(service: BookmarkService):
    parent = service.create_folder("P")
    a = service.add_bookmark(url="https://a.example", title="A", folder_id=parent.id)
    b = service.add_bookmark(url="https://b.example", title="B", folder_id=parent.id)
    c = service.add_bookmark(url="https://c.example", title="C", folder_id=parent.id)
    x = service.add_bookmark(url="https://x.example", title="X")

    # index=0 — first
    service.move_bookmark(x.id, parent.id, index=0)
    assert _ordered_child_ids(service, parent.id) == [x.id, a.id, b.id, c.id]

    # move x out, then back with index=2 — third
    service.move_bookmark(x.id, None)
    service.move_bookmark(x.id, parent.id, index=2)
    assert _ordered_child_ids(service, parent.id) == [a.id, b.id, x.id, c.id]

    # very large index — appended
    service.move_bookmark(x.id, None)
    service.move_bookmark(x.id, parent.id, index=9999)
    assert _ordered_child_ids(service, parent.id) == [a.id, b.id, c.id, x.id]


def test_move_folder_with_explicit_index(service: BookmarkService):
    parent = service.create_folder("P")
    a = service.create_folder("A", parent_id=parent.id)
    b = service.create_folder("B", parent_id=parent.id)
    c = service.create_folder("C", parent_id=parent.id)
    x = service.create_folder("X")

    service.move_folder(x.id, parent.id, index=0)
    assert _ordered_child_ids(service, parent.id) == [x.id, a.id, b.id, c.id]

    service.move_folder(x.id, None)
    service.move_folder(x.id, parent.id, index=2)
    assert _ordered_child_ids(service, parent.id) == [a.id, b.id, x.id, c.id]

    service.move_folder(x.id, None)
    service.move_folder(x.id, parent.id, index=9999)
    assert _ordered_child_ids(service, parent.id) == [a.id, b.id, c.id, x.id]


def test_move_with_negative_index_raises(service: BookmarkService):
    parent = service.create_folder("P")
    b = service.add_bookmark(url="https://a.example", title="A")
    f = service.create_folder("F")
    with pytest.raises(ValueError):
        service.move_bookmark(b.id, parent.id, index=-1)
    with pytest.raises(ValueError):
        service.move_folder(f.id, parent.id, index=-1)


def test_reorder_children_happy_path(service: BookmarkService):
    parent = service.create_folder("P")
    a = service.add_bookmark(url="https://a.example", title="A", folder_id=parent.id)
    b = service.add_bookmark(url="https://b.example", title="B", folder_id=parent.id)
    c = service.add_bookmark(url="https://c.example", title="C", folder_id=parent.id)
    d = service.add_bookmark(url="https://d.example", title="D", folder_id=parent.id)

    service.reorder_children(parent.id, [c.id, a.id, d.id, b.id])
    assert _ordered_child_ids(service, parent.id) == [c.id, a.id, d.id, b.id]


def test_reorder_children_mixes_folders_and_bookmarks(service: BookmarkService):
    parent = service.create_folder("P")
    f1 = service.create_folder("F1", parent_id=parent.id)
    bm1 = service.add_bookmark(url="https://a.example", title="A", folder_id=parent.id)
    f2 = service.create_folder("F2", parent_id=parent.id)
    bm2 = service.add_bookmark(url="https://b.example", title="B", folder_id=parent.id)

    service.reorder_children(parent.id, [bm2.id, f1.id, bm1.id, f2.id])
    assert _ordered_child_ids(service, parent.id) == [bm2.id, f1.id, bm1.id, f2.id]


def test_reorder_children_rejects_missing_id(service: BookmarkService):
    parent = service.create_folder("P")
    a = service.add_bookmark(url="https://a.example", title="A", folder_id=parent.id)
    b = service.add_bookmark(url="https://b.example", title="B", folder_id=parent.id)
    service.add_bookmark(url="https://c.example", title="C", folder_id=parent.id)
    with pytest.raises(ReorderMismatchError):
        service.reorder_children(parent.id, [a.id, b.id])


def test_reorder_children_rejects_unknown_id(service: BookmarkService):
    parent = service.create_folder("P")
    a = service.add_bookmark(url="https://a.example", title="A", folder_id=parent.id)
    b = service.add_bookmark(url="https://b.example", title="B", folder_id=parent.id)
    with pytest.raises(ReorderMismatchError):
        service.reorder_children(parent.id, [a.id, b.id, "not-a-real-id"])


def test_reorder_children_rejects_wrong_parent_id(service: BookmarkService):
    p1 = service.create_folder("P1")
    p2 = service.create_folder("P2")
    a = service.add_bookmark(url="https://a.example", title="A", folder_id=p1.id)
    b = service.add_bookmark(url="https://b.example", title="B", folder_id=p1.id)
    other = service.add_bookmark(url="https://o.example", title="O", folder_id=p2.id)
    with pytest.raises(ReorderMismatchError):
        service.reorder_children(p1.id, [a.id, b.id, other.id])


def test_stats(service: BookmarkService):
    f = service.create_folder("F")
    service.add_bookmark(url="https://a.example", title="A", folder_id=f.id, tags=["x", "y"])
    service.add_bookmark(url="https://b.example", title="B", tags=["y"])
    assert service.stats() == {"bookmarks": 2, "folders": 1, "tags": 2}
