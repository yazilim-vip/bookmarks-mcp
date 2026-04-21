from __future__ import annotations

from pathlib import Path

from bookmarks_mcp.models import Bookmark, Library
from bookmarks_mcp.storage import JsonFileStorage as Storage


def test_load_returns_empty_library_when_file_missing(tmp_path: Path):
    s = Storage(tmp_path / "nested" / "does-not-exist.json")
    lib = s.load()
    assert lib.bookmarks == []
    assert lib.folders == []


def test_save_then_load_roundtrip(tmp_path: Path):
    s = Storage(tmp_path / "db.json")
    lib = Library(bookmarks=[Bookmark(url="https://a.example", title="A")])
    s.save(lib)
    restored = s.load()
    assert len(restored.bookmarks) == 1
    assert restored.bookmarks[0].title == "A"


def test_save_uses_atomic_rename(tmp_path: Path):
    s = Storage(tmp_path / "db.json")
    s.save(Library())
    leftover_tmps = list(tmp_path.glob(".bookmarks-*.tmp"))
    assert leftover_tmps == []


def test_transaction_persists_changes(tmp_path: Path):
    s = Storage(tmp_path / "db.json")
    with s.transaction() as lib:
        lib.bookmarks.append(Bookmark(url="https://b.example", title="B"))
    reloaded = s.load()
    assert reloaded.bookmarks[0].title == "B"


def test_transaction_skips_save_on_exception(tmp_path: Path):
    s = Storage(tmp_path / "db.json")
    s.save(Library())
    try:
        with s.transaction() as lib:
            lib.bookmarks.append(Bookmark(url="https://c.example", title="C"))
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert s.load().bookmarks == []
