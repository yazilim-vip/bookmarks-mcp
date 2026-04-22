from __future__ import annotations

import pytest
from pydantic import ValidationError

from bookmarks_mcp.models import Bookmark, Folder, Library, normalize_tag


def test_normalize_tag_lowercases_and_slugifies():
    assert normalize_tag("Python Web") == "python-web"
    assert normalize_tag("  weird  TAG!!  ") == "weird-tag"
    assert normalize_tag("___") == ""


def test_bookmark_requires_url_with_scheme():
    with pytest.raises(ValidationError):
        Bookmark(url="no-scheme.example", title="x")


def test_bookmark_dedupes_and_normalizes_tags():
    b = Bookmark(url="https://example.com", title="x", tags=["Python", "python", "Web Dev", ""])
    assert b.tags == ["python", "web-dev"]


def test_bookmark_empty_title_rejected():
    with pytest.raises(ValidationError):
        Bookmark(url="https://example.com", title="   ")


def test_folder_defaults_to_new_id_and_timestamps():
    a = Folder(name="Reading")
    b = Folder(name="Reading")
    assert a.id != b.id
    assert a.created_at.tzinfo is not None
    assert a.updated_at >= a.created_at


def test_position_defaults_to_zero():
    b = Bookmark(url="https://example.com", title="x")
    f = Folder(name="Reading")
    assert b.position == 0
    assert f.position == 0


def test_position_sort_with_id_tiebreak():
    # Items with the same position fall back to a stable id ordering.
    a = Folder(id="aaa", name="A")
    b = Bookmark(id="bbb", url="https://b.example", title="B")
    c = Folder(id="ccc", name="C", position=1)
    items: list[Folder | Bookmark] = [c, b, a]
    items.sort(key=lambda it: (it.position, it.id))
    assert [it.id for it in items] == ["aaa", "bbb", "ccc"]


def test_library_roundtrip_json():
    lib = Library(
        folders=[Folder(name="Work")],
        bookmarks=[Bookmark(url="https://a.example", title="A")],
    )
    data = lib.model_dump_json()
    restored = Library.model_validate_json(data)
    assert restored.folders[0].name == "Work"
    assert str(restored.bookmarks[0].url) == "https://a.example"
