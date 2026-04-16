from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="bookmarks-mcp")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (
        "<!doctype html><html><head><title>bookmarks-mcp</title></head>"
        "<body><h1>bookmarks-mcp</h1><p>Web UI placeholder — routes land in the web UI task.</p>"
        "</body></html>"
    )


def run_web(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)
