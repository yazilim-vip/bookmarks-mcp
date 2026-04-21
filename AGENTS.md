# Bookmarks MCP

## Identity

MCP server for personal bookmark management. Drives Google Chrome's live `Bookmarks` file or a portable JSON store. Single-user, laptop-local, agent-first — no web UI, no auth, no server.

**Tech Stack:** Python 3.11+, FastMCP, Pydantic, BeautifulSoup4 + lxml, uv

## Module Map

| Module | Path | Purpose |
|--------|------|---------|
| cli | `src/bookmarks_mcp/cli.py` | Subcommand dispatcher (mcp / import / export / info) |
| models | `src/bookmarks_mcp/models.py` | Pydantic models: `Bookmark`, `Folder`, `Library` |
| storage | `src/bookmarks_mcp/storage/` | Pluggable storage: `base.Storage` (ABC), `json_file.JsonFileStorage`, `chrome.ChromeStorage`, `factory.create_storage` |
| paths | `src/bookmarks_mcp/paths.py` | XDG-compliant default storage path resolution (json backend) |
| server | `src/bookmarks_mcp/server.py` | FastMCP server and tool definitions |
| importers | `src/bookmarks_mcp/importers/` | Netscape HTML + JSON import/export |
| info | `src/bookmarks_mcp/info.py` | `info` subcommand — prints active backend + storage path |

## Build & Run

```bash
# Install dependencies
uv sync --group dev

# Run MCP server (stdio)
uv run bookmarks-mcp

# Show active backend + storage path
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
- **Storage is pluggable** — all production callers construct storage via `create_storage()` (reads `BOOKMARKS_MCP_BACKEND`: `json` | `chrome`). Tests use `JsonFileStorage(path)` directly
- **JSON backend** — atomic writes (temp + rename); never SQLite (portability over raw speed)
- **Chrome backend** — reads/writes Chrome's `Bookmarks` file; preserves unknown fields via raw-tree cache (`meta_info`, `sync_transaction_version`, etc.); tags disabled; refuses writes while Chrome is running (override `BOOKMARKS_MCP_CHROME_FORCE=1`); backs up to `Bookmarks.bak.<ts>` (keeps last 10)
- **No web UI** — removed in 0.8.0. Chrome's `chrome://bookmarks` fills that niche for the Chrome backend; the JSON backend relies on direct file editing or the MCP tools
- **MCP stdio protocol uses stdout** — never `print()` to stdout from server code; use `sys.stderr` for logs
- **Portability is a first-class feature** — Netscape HTML import/export must round-trip with major browsers

## Dependencies

| Dependency | Relationship |
|-----------|-------------|
| FastMCP | MCP server framework |
| Pydantic | Typed data models and JSON (de)serialization |
| BeautifulSoup4 + lxml | Netscape HTML bookmark format parsing |
| platformdirs | Cross-platform XDG data directory resolution |
| uv | Package management and execution |
