from __future__ import annotations

from pathlib import Path

from bookmarks_mcp.importers import json_io, netscape
from bookmarks_mcp.models import Library
from bookmarks_mcp.storage import Storage, create_storage

_FORMATS = {"html", "json"}


def _parse(text: str, fmt: str) -> Library:
    if fmt == "html":
        return netscape.parse(text)
    if fmt == "json":
        return json_io.parse(text)
    raise ValueError(f"unknown format: {fmt!r} (expected one of {sorted(_FORMATS)})")


def _serialize(library: Library, fmt: str) -> str:
    if fmt == "html":
        return netscape.serialize(library)
    if fmt == "json":
        return json_io.serialize(library)
    raise ValueError(f"unknown format: {fmt!r} (expected one of {sorted(_FORMATS)})")


def merge(target: Library, source: Library, dedupe: bool = True) -> dict[str, int]:
    """Append source folders and bookmarks into target.

    With ``dedupe=True`` (the default) bookmarks whose URL already exists in
    ``target`` are skipped. Folders are always appended — UUID collisions are
    statistically impossible.
    """
    existing_urls = {str(b.url) for b in target.bookmarks} if dedupe else set()
    folders_added = 0
    bookmarks_added = 0
    for folder in source.folders:
        target.folders.append(folder)
        folders_added += 1
    for bookmark in source.bookmarks:
        url = str(bookmark.url)
        if dedupe and url in existing_urls:
            continue
        target.bookmarks.append(bookmark)
        existing_urls.add(url)
        bookmarks_added += 1
    return {"folders_added": folders_added, "bookmarks_added": bookmarks_added}


def import_file(path: str | Path, fmt: str, storage: Storage | None = None) -> dict[str, int]:
    storage = storage or create_storage()
    text = Path(path).read_text(encoding="utf-8")
    incoming = _parse(text, fmt)
    with storage.transaction() as library:
        result = merge(library, incoming)
    return result


def export_file(path: str | Path, fmt: str, storage: Storage | None = None) -> dict[str, int]:
    storage = storage or create_storage()
    library = storage.load()
    text = _serialize(library, fmt)
    Path(path).write_text(text, encoding="utf-8")
    return {
        "folders_exported": len(library.folders),
        "bookmarks_exported": len(library.bookmarks),
    }


def run_import(file: str, fmt: str) -> None:
    result = import_file(file, fmt)
    print(
        f"imported {result['bookmarks_added']} bookmark(s) and {result['folders_added']} folder(s) from {file} ({fmt})"
    )


def run_export(file: str, fmt: str) -> None:
    result = export_file(file, fmt)
    print(
        f"exported {result['bookmarks_exported']} bookmark(s) and "
        f"{result['folders_exported']} folder(s) to {file} ({fmt})"
    )
