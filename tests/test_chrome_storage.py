from __future__ import annotations

import json
from pathlib import Path

import pytest

from bookmarks_mcp.models import Bookmark
from bookmarks_mcp.storage.chrome import (
    ChromeBookmarksNotFoundError,
    ChromeRunningError,
    ChromeStorage,
    _webkit_to_dt,
    resolve_chrome_paths,
)

CHROME_FIXTURE: dict = {
    "checksum": "deadbeef",
    "version": 1,
    "roots": {
        "bookmark_bar": {
            "children": [
                {
                    "date_added": "13300000000000000",
                    "guid": "aaaa0001-0000-4000-a000-000000000001",
                    "id": "10",
                    "name": "Anthropic",
                    "type": "url",
                    "url": "https://www.anthropic.com",
                    "meta_info": {"power_bookmark_meta": "{}"},
                },
                {
                    "children": [
                        {
                            "date_added": "13300000000000001",
                            "guid": "aaaa0002-0000-4000-a000-000000000002",
                            "id": "11",
                            "name": "Python Docs",
                            "type": "url",
                            "url": "https://docs.python.org",
                        }
                    ],
                    "date_added": "13300000000000000",
                    "date_modified": "13300000000000000",
                    "guid": "aaaa0003-0000-4000-a000-000000000003",
                    "id": "12",
                    "name": "Reading",
                    "type": "folder",
                    "sync_transaction_version": "1",
                },
            ],
            "date_added": "13300000000000000",
            "date_modified": "13300000000000000",
            "guid": "00000000-0000-4000-A000-000000000002",
            "id": "1",
            "name": "Bookmarks bar",
            "type": "folder",
        },
        "other": {
            "children": [],
            "date_added": "13300000000000000",
            "date_modified": "0",
            "guid": "00000000-0000-4000-A000-000000000003",
            "id": "2",
            "name": "Other bookmarks",
            "type": "folder",
        },
        "synced": {
            "children": [],
            "date_added": "13300000000000000",
            "date_modified": "0",
            "guid": "00000000-0000-4000-A000-000000000004",
            "id": "3",
            "name": "Mobile bookmarks",
            "type": "folder",
        },
    },
}


@pytest.fixture
def force_not_running(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOKMARKS_MCP_CHROME_FORCE", "1")


@pytest.fixture
def fixture_file(tmp_path: Path) -> Path:
    p = tmp_path / "Bookmarks"
    p.write_text(json.dumps(CHROME_FIXTURE), encoding="utf-8")
    return p


def test_load_parses_fixture(fixture_file: Path):
    store = ChromeStorage(fixture_file)
    lib = store.load()

    folder_names = {f.name for f in lib.folders}
    assert "Bookmarks bar" in folder_names
    assert "Reading" in folder_names
    assert "Other bookmarks" in folder_names
    assert "Mobile bookmarks" in folder_names

    titles = {b.title for b in lib.bookmarks}
    assert titles == {"Anthropic", "Python Docs"}

    anthropic = next(b for b in lib.bookmarks if b.title == "Anthropic")
    assert str(anthropic.url) == "https://www.anthropic.com"
    assert anthropic.tags == []  # Chrome has no tags


def test_load_missing_file_raises(tmp_path: Path):
    with pytest.raises(ChromeBookmarksNotFoundError):
        ChromeStorage(tmp_path / "nope").load()


def test_save_refuses_when_chrome_running(fixture_file: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BOOKMARKS_MCP_CHROME_FORCE", "0")
    monkeypatch.setattr("bookmarks_mcp.storage.chrome._chrome_running", lambda: True)
    store = ChromeStorage(fixture_file)
    store.load()
    with pytest.raises(ChromeRunningError):
        store.save(store.load())


def test_save_creates_backup_and_preserves_extras(fixture_file: Path, force_not_running: None):
    store = ChromeStorage(fixture_file)
    lib = store.load()
    # Mutate: add a new bookmark under "Reading"
    reading = next(f for f in lib.folders if f.name == "Reading")
    lib.bookmarks.append(Bookmark(url="https://example.com", title="New", folder_id=reading.id))
    store.save(lib)

    # Backup was created
    backups = list(fixture_file.parent.glob("Bookmarks.bak.*"))
    assert len(backups) == 1

    # Reload and verify
    raw = json.loads(fixture_file.read_text())
    assert "checksum" not in raw  # scrubbed
    reading_node = next(c for c in raw["roots"]["bookmark_bar"]["children"] if c.get("name") == "Reading")
    assert reading_node["sync_transaction_version"] == "1"  # preserved
    child_titles = {c["name"] for c in reading_node["children"]}
    assert child_titles == {"Python Docs", "New"}

    # Anthropic's meta_info preserved
    anthropic_node = next(c for c in raw["roots"]["bookmark_bar"]["children"] if c.get("name") == "Anthropic")
    assert anthropic_node["meta_info"] == {"power_bookmark_meta": "{}"}


def test_orphan_bookmark_routes_to_other(fixture_file: Path, force_not_running: None):
    store = ChromeStorage(fixture_file)
    lib = store.load()
    lib.bookmarks.append(Bookmark(url="https://orphan.example", title="Orphan", folder_id=None))
    store.save(lib)

    raw = json.loads(fixture_file.read_text())
    other_children = raw["roots"]["other"]["children"]
    assert any(c["name"] == "Orphan" for c in other_children)


def test_transaction_roundtrip(fixture_file: Path, force_not_running: None):
    store = ChromeStorage(fixture_file)
    with store.transaction() as lib:
        reading = next(f for f in lib.folders if f.name == "Reading")
        lib.bookmarks.append(Bookmark(url="https://tx.example", title="TxAdd", folder_id=reading.id))

    reloaded = ChromeStorage(fixture_file).load()
    assert any(b.title == "TxAdd" for b in reloaded.bookmarks)


def test_resolve_paths_uses_override(tmp_path: Path):
    p = tmp_path / "custom" / "Bookmarks"
    paths = resolve_chrome_paths(override=str(p))
    assert paths.bookmarks_file == p.expanduser().resolve()


def test_resolve_paths_defaults_to_default_profile():
    paths = resolve_chrome_paths()
    assert paths.profile == "Default"
    assert paths.bookmarks_file.name == "Bookmarks"
    assert paths.bookmarks_file.parent.name == "Default"


def test_webkit_epoch_conversion():
    # 13300000000000000 μs since 1601 ≈ 2022-03-03
    dt = _webkit_to_dt("13300000000000000")
    assert dt.year == 2022
