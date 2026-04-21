from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bookmarks_mcp.errors import BookmarksError
from bookmarks_mcp.models import Folder
from bookmarks_mcp.service import BookmarkService
from bookmarks_mcp.storage import create_storage

app = FastAPI(title="bookmarks-mcp")

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

_service: BookmarkService | None = None


def get_service() -> BookmarkService:
    global _service
    if _service is None:
        _service = BookmarkService(create_storage())
    return _service


@app.exception_handler(BookmarksError)
def _handle_bookmark_error(request: Request, exc: BookmarksError) -> HTMLResponse:
    return HTMLResponse(
        content=(
            "<!doctype html><html><body style='font-family:sans-serif;padding:24px;'>"
            f"<h1>Error</h1><p>{exc}</p><p><a href='/'>← Back</a></p></body></html>"
        ),
        status_code=400,
    )


def _back(folder_id: str | None) -> RedirectResponse:
    target = f"/?folder={folder_id}" if folder_id else "/"
    return RedirectResponse(url=target, status_code=303)


# -------------------------------------------------------------------------
# Index
# -------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    folder: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    service: BookmarkService = Depends(get_service),
) -> HTMLResponse:
    all_folders = service.list_all_folders()
    children_by_parent: dict[str | None, list[Folder]] = defaultdict(list)
    folders_by_id: dict[str, Folder] = {}
    for f in all_folders:
        children_by_parent[f.parent_id].append(f)
        folders_by_id[f.id] = f
    bookmarks = service.list_bookmarks(folder_id=folder, tag=tag, query=q, limit=500)
    tags = service.list_tags()
    selected_folder = folders_by_id.get(folder) if folder else None
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "folders": all_folders,
            "folders_by_id": folders_by_id,
            "children_by_parent": children_by_parent,
            "bookmarks": bookmarks,
            "tags": tags,
            "selected_folder": selected_folder,
            "selected_tag": tag,
            "query": q,
        },
    )


# -------------------------------------------------------------------------
# Folder mutations
# -------------------------------------------------------------------------


@app.post("/folders", response_class=RedirectResponse)
def create_folder(
    name: str = Form(...),
    parent_id: str = Form(""),
    service: BookmarkService = Depends(get_service),
) -> RedirectResponse:
    parent = parent_id or None
    service.create_folder(name=name, parent_id=parent)
    return _back(parent)


@app.post("/folders/{folder_id}/rename", response_class=RedirectResponse)
def rename_folder(
    folder_id: str,
    name: str = Form(...),
    service: BookmarkService = Depends(get_service),
) -> RedirectResponse:
    service.rename_folder(folder_id, name)
    return _back(folder_id)


@app.post("/folders/{folder_id}/move", response_class=RedirectResponse)
def move_folder(
    folder_id: str,
    parent_id: str = Form(""),
    service: BookmarkService = Depends(get_service),
) -> RedirectResponse:
    parent = parent_id or None
    service.move_folder(folder_id, parent)
    return _back(folder_id)


@app.post("/folders/{folder_id}/delete", response_class=RedirectResponse)
def delete_folder(
    folder_id: str,
    recursive: str | None = Form(None),
    service: BookmarkService = Depends(get_service),
) -> RedirectResponse:
    service.delete_folder(folder_id, recursive=bool(recursive))
    return _back(None)


# -------------------------------------------------------------------------
# Tag mutations
# -------------------------------------------------------------------------


@app.post("/tags/{tag}/rename", response_class=RedirectResponse)
def rename_tag(
    tag: str,
    new_name: str = Form(...),
    service: BookmarkService = Depends(get_service),
) -> RedirectResponse:
    service.rename_tag(tag, new_name)
    return _back(None)


@app.post("/tags/{tag}/delete", response_class=RedirectResponse)
def delete_tag(
    tag: str,
    service: BookmarkService = Depends(get_service),
) -> RedirectResponse:
    service.delete_tag(tag)
    return _back(None)


def run_web(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)
