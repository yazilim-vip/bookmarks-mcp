"""Netscape Bookmark File parser/serializer.

Round-trips with the bookmark export format used by Chrome, Firefox, Safari,
Edge, Pinboard and other tools. The format is technically malformed HTML —
DT and DD elements are intentionally not closed — so we depend on the html.parser
backend to be tolerant.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from html import escape

from bs4 import BeautifulSoup, Tag
from pydantic import ValidationError

from bookmarks_mcp.models import Bookmark, Folder, Library


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def parse(html: str) -> Library:
    """Parse a Netscape Bookmark File and return a fresh Library."""
    soup = BeautifulSoup(html, "lxml")
    library = Library()
    root = soup.find("dl")
    if root is None:
        return library
    _walk(root, parent_id=None, library=library)
    return library


def _walk(dl: Tag, parent_id: str | None, library: Library) -> None:
    children = [c for c in dl.children if isinstance(c, Tag)]
    i = 0
    while i < len(children):
        node = children[i]
        name = (node.name or "").lower()

        if name != "dt":
            i += 1
            continue

        h3 = node.find("h3", recursive=False)
        if h3 is not None:
            folder = Folder(
                name=h3.get_text(strip=True) or "Untitled folder",
                parent_id=parent_id,
                created_at=_parse_timestamp(h3.get("add_date")) or _now(),
                updated_at=_parse_timestamp(h3.get("last_modified")) or _now(),
            )
            library.folders.append(folder)
            sibling = children[i + 1] if i + 1 < len(children) else None
            if sibling is not None and (sibling.name or "").lower() == "dl":
                _walk(sibling, parent_id=folder.id, library=library)
                i += 2
            else:
                i += 1
            continue

        a = node.find("a", recursive=False)
        if a is None:
            i += 1
            continue

        href = a.get("href")
        if not href:
            i += 1
            continue

        tags_attr = a.get("tags") or ""
        tags = [t.strip() for t in tags_attr.split(",") if t.strip()]
        try:
            bookmark = Bookmark(
                url=href,
                title=a.get_text(strip=True) or href,
                folder_id=parent_id,
                tags=tags,
                created_at=_parse_timestamp(a.get("add_date")) or _now(),
                updated_at=_parse_timestamp(a.get("last_modified")) or _now(),
            )
        except ValidationError:
            i += 1
            continue

        library.bookmarks.append(bookmark)
        sibling = children[i + 1] if i + 1 < len(children) else None
        if sibling is not None and (sibling.name or "").lower() == "dd":
            description = sibling.get_text(strip=True)
            if description:
                bookmark.description = description
            i += 2
        else:
            i += 1


def serialize(library: Library) -> str:
    """Render a Library as a Netscape Bookmark File compatible with browsers."""
    by_parent: dict[str | None, list[Folder]] = defaultdict(list)
    for f in library.folders:
        by_parent[f.parent_id].append(f)
    by_folder: dict[str | None, list[Bookmark]] = defaultdict(list)
    for b in library.bookmarks:
        by_folder[b.folder_id].append(b)

    lines: list[str] = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        "<!-- This is an automatically generated file. -->",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
        "<DL><p>",
    ]
    _emit(lines, None, by_parent, by_folder, indent=4)
    lines.append("</DL><p>")
    return "\n".join(lines) + "\n"


def _emit(
    lines: list[str],
    parent_id: str | None,
    by_parent: dict[str | None, list[Folder]],
    by_folder: dict[str | None, list[Bookmark]],
    indent: int,
) -> None:
    pad = " " * indent
    for folder in by_parent.get(parent_id, []):
        created = int(folder.created_at.timestamp())
        modified = int(folder.updated_at.timestamp())
        lines.append(f'{pad}<DT><H3 ADD_DATE="{created}" LAST_MODIFIED="{modified}">{escape(folder.name)}</H3>')
        lines.append(f"{pad}<DL><p>")
        _emit(lines, folder.id, by_parent, by_folder, indent + 4)
        lines.append(f"{pad}</DL><p>")
    for bookmark in by_folder.get(parent_id, []):
        created = int(bookmark.created_at.timestamp())
        modified = int(bookmark.updated_at.timestamp())
        attrs = f'HREF="{escape(str(bookmark.url), quote=True)}" ADD_DATE="{created}" LAST_MODIFIED="{modified}"'
        if bookmark.tags:
            attrs += f' TAGS="{escape(",".join(bookmark.tags), quote=True)}"'
        lines.append(f"{pad}<DT><A {attrs}>{escape(bookmark.title)}</A>")
        if bookmark.description:
            lines.append(f"{pad}<DD>{escape(bookmark.description)}")
