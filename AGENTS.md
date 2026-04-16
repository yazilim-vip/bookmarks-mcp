# Bookmarks MCP

## Identity

MCP server + local web UI for personal bookmark management. Folders, tags, portable JSON storage. Designed for single-user laptop use — data lives as a single JSON file that syncs trivially via Dropbox/iCloud/Syncthing.

**Tech Stack:** Python 3.11+, FastMCP, FastAPI, Uvicorn, Pydantic, Jinja2, BeautifulSoup4, uv

## Module Map

| Module | Path | Purpose |
|--------|------|---------|
| cli | `src/bookmarks_mcp/cli.py` | Subcommand dispatcher (mcp / web / import / export / info) |
| models | `src/bookmarks_mcp/models.py` | Pydantic models: `Bookmark`, `Folder`, `Library` |
| storage | `src/bookmarks_mcp/storage.py` | JSON-on-disk persistence with atomic writes |
| paths | `src/bookmarks_mcp/paths.py` | XDG-compliant default storage path resolution |
| server | `src/bookmarks_mcp/server.py` | FastMCP server and tool definitions |
| web | `src/bookmarks_mcp/web.py` | FastAPI web UI |
| importers | `src/bookmarks_mcp/importers/` | Netscape HTML + JSON import/export |
| info | `src/bookmarks_mcp/info.py` | `info` subcommand — prints storage path |

## Build & Run

```bash
# Install dependencies
uv sync --group dev

# Run MCP server (stdio)
uv run bookmarks-mcp

# Run Web UI (defaults to 127.0.0.1:8765)
uv run bookmarks-mcp web

# Show storage path and status
uv run bookmarks-mcp info

# Run directly from GitHub (no clone)
uvx --from git+https://github.com/yazilim-vip/bookmarks-mcp bookmarks-mcp

# Lint + format check
uv run ruff check .
uv run ruff format --check .

# Build distributable
uv build
```

## Key Paths

| Path | Purpose |
|------|---------|
| `src/bookmarks_mcp/` | Package source |
| `pyproject.toml` | Project metadata, dependencies, ruff config |
| `.github/workflows/ci.yml` | CI: lint, build, version check, GitHub release |

## Project Rules

- **Cross-platform** — no platform-specific code; data path via `platformdirs`
- **Version bump required** — CI blocks PRs that don't bump `version` in `pyproject.toml`
- **Folders are a strict tree** — each bookmark has at most one `folder_id`; tags are cross-cutting metadata
- **Storage is JSON-on-disk** — atomic writes (temp + rename); never SQLite (portability over raw speed)
- **Web UI binds localhost by default** — no authentication; not intended for remote exposure
- **MCP stdio protocol uses stdout** — never `print()` to stdout from server code; use `sys.stderr` for logs
- **Portability is a first-class feature** — Netscape HTML import/export must round-trip with major browsers

## Dependencies

| Dependency | Relationship |
|-----------|-------------|
| FastMCP | MCP server framework |
| FastAPI + Uvicorn | Local web UI |
| Pydantic | Typed data models and JSON (de)serialization |
| Jinja2 | Web UI templating |
| BeautifulSoup4 | Netscape HTML bookmark format parsing |
| platformdirs | Cross-platform XDG data directory resolution |
| uv | Package management and execution |
