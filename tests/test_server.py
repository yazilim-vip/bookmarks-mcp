from __future__ import annotations

import asyncio

import pytest

from bookmarks_mcp.server import mcp, set_service
from bookmarks_mcp.service import BookmarkService


@pytest.fixture(autouse=True)
def _inject_service(service: BookmarkService):
    set_service(service)
    yield
    set_service(None)


def _tool_names() -> set[str]:
    tools = asyncio.run(mcp.list_tools())
    return {t.name for t in tools}


def test_expected_tools_are_registered():
    expected = {
        "list_folders",
        "list_all_folders",
        "get_folder",
        "create_folder",
        "rename_folder",
        "move_folder",
        "delete_folder",
        "list_bookmarks",
        "get_bookmark",
        "add_bookmark",
        "update_bookmark",
        "move_bookmark",
        "delete_bookmark",
        "list_tags",
        "rename_tag",
        "delete_tag",
        "stats",
    }
    assert expected.issubset(_tool_names())


def test_tools_invoke_against_injected_service(service: BookmarkService):
    from bookmarks_mcp import server

    folder = server.create_folder("Reading")
    assert folder["name"] == "Reading"

    bookmark = server.add_bookmark(
        url="https://docs.python.org",
        title="Python Docs",
        folder_id=folder["id"],
        tags=["Python", "docs"],
    )
    assert bookmark["tags"] == ["python", "docs"]

    listed = server.list_bookmarks(folder_id=folder["id"])
    assert [b["id"] for b in listed] == [bookmark["id"]]

    server.update_bookmark(bookmark["id"], description="The official docs")
    assert server.get_bookmark(bookmark["id"])["description"] == "The official docs"

    server.delete_bookmark(bookmark["id"])
    assert server.list_bookmarks(folder_id=folder["id"]) == []

    server.delete_folder(folder["id"])
    assert server.list_folders(parent_id=None) == []
