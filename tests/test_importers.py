from __future__ import annotations

from pathlib import Path

from bookmarks_mcp.importers import export_file, import_file, json_io, merge, netscape
from bookmarks_mcp.models import Bookmark, Folder, Library
from bookmarks_mcp.service import BookmarkService
from bookmarks_mcp.storage import Storage

CHROME_SAMPLE = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<!-- This is an automatically generated file. -->
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><H3 ADD_DATE="1700000000" LAST_MODIFIED="1700000100">Reading</H3>
    <DL><p>
        <DT><A HREF="https://docs.python.org" ADD_DATE="1700000000" TAGS="python,docs">Python Docs</A>
        <DD>The official Python documentation.
        <DT><H3 ADD_DATE="1700000000">AI</H3>
        <DL><p>
            <DT><A HREF="https://anthropic.com" ADD_DATE="1700000000">Anthropic</A>
        </DL><p>
    </DL><p>
    <DT><A HREF="https://example.com" ADD_DATE="1700000000">Example</A>
</DL><p>
"""


def test_netscape_parse_chrome_sample():
    library = netscape.parse(CHROME_SAMPLE)
    folder_names = [f.name for f in library.folders]
    assert "Reading" in folder_names
    assert "AI" in folder_names

    bookmark_titles = [b.title for b in library.bookmarks]
    assert bookmark_titles == ["Python Docs", "Anthropic", "Example"]

    python_docs = next(b for b in library.bookmarks if b.title == "Python Docs")
    assert python_docs.tags == ["python", "docs"]
    assert python_docs.description == "The official Python documentation."

    reading = next(f for f in library.folders if f.name == "Reading")
    ai = next(f for f in library.folders if f.name == "AI")
    assert ai.parent_id == reading.id

    anthropic = next(b for b in library.bookmarks if b.title == "Anthropic")
    assert anthropic.folder_id == ai.id

    example = next(b for b in library.bookmarks if b.title == "Example")
    assert example.folder_id is None


def test_netscape_roundtrip_preserves_structure():
    library = netscape.parse(CHROME_SAMPLE)
    serialized = netscape.serialize(library)
    reparsed = netscape.parse(serialized)

    assert {f.name for f in reparsed.folders} == {f.name for f in library.folders}
    assert {b.title for b in reparsed.bookmarks} == {b.title for b in library.bookmarks}
    assert {tuple(b.tags) for b in reparsed.bookmarks} == {tuple(b.tags) for b in library.bookmarks}


def test_netscape_serialize_escapes_html_entities():
    lib = Library(
        folders=[Folder(name="<script>")],
        bookmarks=[Bookmark(url="https://x.example?q=a&b=c", title="Title <b>")],
    )
    out = netscape.serialize(lib)
    assert "&lt;script&gt;" in out
    assert "&amp;b=c" in out
    assert "Title &lt;b&gt;" in out


def test_json_roundtrip():
    lib = Library(
        folders=[Folder(name="Work")],
        bookmarks=[Bookmark(url="https://a.example", title="A", tags=["x"])],
    )
    text = json_io.serialize(lib)
    restored = json_io.parse(text)
    assert restored.folders[0].name == "Work"
    assert restored.bookmarks[0].title == "A"
    assert restored.bookmarks[0].tags == ["x"]


def test_merge_dedupes_by_url():
    target = Library(bookmarks=[Bookmark(url="https://a.example", title="A")])
    source = Library(
        bookmarks=[
            Bookmark(url="https://a.example", title="A duplicate"),
            Bookmark(url="https://b.example", title="B"),
        ]
    )
    result = merge(target, source)
    assert result == {"folders_added": 0, "bookmarks_added": 1}
    assert {str(b.url) for b in target.bookmarks} == {"https://a.example", "https://b.example"}


def test_import_file_then_export_html(tmp_path: Path):
    src = tmp_path / "in.html"
    src.write_text(CHROME_SAMPLE, encoding="utf-8")
    db = tmp_path / "db.json"
    storage = Storage(db)

    result = import_file(src, "html", storage=storage)
    assert result["bookmarks_added"] == 3
    assert result["folders_added"] == 2

    out = tmp_path / "out.html"
    export_file(out, "html", storage=storage)
    reparsed = netscape.parse(out.read_text(encoding="utf-8"))
    assert {b.title for b in reparsed.bookmarks} == {"Python Docs", "Anthropic", "Example"}


def test_import_twice_dedupes(tmp_path: Path):
    src = tmp_path / "in.html"
    src.write_text(CHROME_SAMPLE, encoding="utf-8")
    storage = Storage(tmp_path / "db.json")

    first = import_file(src, "html", storage=storage)
    second = import_file(src, "html", storage=storage)

    assert first["bookmarks_added"] == 3
    assert second["bookmarks_added"] == 0  # all URLs already known


def test_service_can_query_imported_data(tmp_path: Path):
    src = tmp_path / "in.html"
    src.write_text(CHROME_SAMPLE, encoding="utf-8")
    storage = Storage(tmp_path / "db.json")
    import_file(src, "html", storage=storage)

    service = BookmarkService(storage)
    tagged = service.list_bookmarks(tag="python")
    assert [b.title for b in tagged] == ["Python Docs"]
