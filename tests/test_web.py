from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bookmarks_mcp.service import BookmarkService
from bookmarks_mcp.web import app
from bookmarks_mcp.web import get_service as web_get_service


@pytest.fixture
def client(service: BookmarkService):
    app.dependency_overrides[web_get_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_index_renders_empty_state(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert "No bookmarks here yet" in r.text
    assert "All bookmarks" in r.text


def test_index_lists_folders_and_bookmarks(client: TestClient, service: BookmarkService):
    folder = service.create_folder("Reading")
    service.add_bookmark(
        url="https://docs.python.org",
        title="Python Docs",
        folder_id=folder.id,
        tags=["python", "docs"],
    )
    r = client.get("/")
    assert "Reading" in r.text
    assert "Python Docs" in r.text
    assert "🏷 python" in r.text or ">python<" in r.text


def test_index_filter_by_folder(client: TestClient, service: BookmarkService):
    a = service.create_folder("A")
    b = service.create_folder("B")
    service.add_bookmark(url="https://a.example", title="A-bm", folder_id=a.id)
    service.add_bookmark(url="https://b.example", title="B-bm", folder_id=b.id)
    r = client.get(f"/?folder={a.id}")
    assert "A-bm" in r.text
    assert "B-bm" not in r.text


def test_index_filter_by_tag_and_query(client: TestClient, service: BookmarkService):
    service.add_bookmark(url="https://x.example", title="Cool Article", tags=["news"])
    service.add_bookmark(url="https://y.example", title="Boring Stuff", tags=["news"])
    service.add_bookmark(url="https://z.example", title="Another", tags=["misc"])

    r = client.get("/?tag=news")
    assert "Cool Article" in r.text and "Boring Stuff" in r.text and "Another" not in r.text

    r = client.get("/?q=cool")
    assert "Cool Article" in r.text and "Boring Stuff" not in r.text


def test_create_folder_via_form(client: TestClient, service: BookmarkService):
    r = client.post("/folders", data={"name": "Reading"}, follow_redirects=False)
    assert r.status_code == 303
    folders = service.list_all_folders()
    assert [f.name for f in folders] == ["Reading"]


def test_create_folder_under_parent(client: TestClient, service: BookmarkService):
    parent = service.create_folder("Parent")
    r = client.post(
        "/folders",
        data={"name": "Child", "parent_id": parent.id},
        follow_redirects=False,
    )
    assert r.status_code == 303
    children = service.list_folders(parent_id=parent.id)
    assert [f.name for f in children] == ["Child"]


def test_rename_folder_via_form(client: TestClient, service: BookmarkService):
    f = service.create_folder("Old")
    r = client.post(f"/folders/{f.id}/rename", data={"name": "New"}, follow_redirects=False)
    assert r.status_code == 303
    assert service.get_folder(f.id).name == "New"


def test_move_folder_to_root_via_form(client: TestClient, service: BookmarkService):
    parent = service.create_folder("Parent")
    child = service.create_folder("Child", parent_id=parent.id)
    r = client.post(f"/folders/{child.id}/move", data={"parent_id": ""}, follow_redirects=False)
    assert r.status_code == 303
    assert service.get_folder(child.id).parent_id is None


def test_delete_folder_via_form(client: TestClient, service: BookmarkService):
    f = service.create_folder("Doomed")
    r = client.post(f"/folders/{f.id}/delete", follow_redirects=False)
    assert r.status_code == 303
    assert service.get_folder(f.id) is None


def test_delete_folder_non_recursive_with_children_renders_error(client: TestClient, service: BookmarkService):
    parent = service.create_folder("P")
    service.create_folder("C", parent_id=parent.id)
    r = client.post(f"/folders/{parent.id}/delete", follow_redirects=False)
    assert r.status_code == 400
    assert "not empty" in r.text


def test_rename_and_delete_tag_via_form(client: TestClient, service: BookmarkService):
    service.add_bookmark(url="https://a.example", title="A", tags=["py"])

    r = client.post("/tags/py/rename", data={"new_name": "python"}, follow_redirects=False)
    assert r.status_code == 303
    assert "python" in service.list_tags()

    r = client.post("/tags/python/delete", follow_redirects=False)
    assert r.status_code == 303
    assert service.list_tags() == {}
