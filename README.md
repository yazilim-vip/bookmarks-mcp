# bookmarks-mcp

> MCP server + local web UI for personal bookmark management. Folders, tags, portable JSON storage, zero binary installs — runs with `uv`.

## Prerequisites

- Python 3.11+
- `uv` installed ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

## Install

**No clone needed** — run directly from GitHub:

**Claude Code CLI:**

```bash
claude mcp add bookmarks -- uvx --from git+https://github.com/yazilim-vip/bookmarks-mcp bookmarks-mcp
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "bookmarks": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/yazilim-vip/bookmarks-mcp",
        "bookmarks-mcp"
      ]
    }
  }
}
```

### Web UI

```bash
uvx --from git+https://github.com/yazilim-vip/bookmarks-mcp bookmarks-mcp web
# → http://127.0.0.1:8765
```

### Import / Export

```bash
# Netscape HTML (round-trips with Chrome/Firefox/Safari/Edge)
bookmarks-mcp import bookmarks.html --format html
bookmarks-mcp export bookmarks.html --format html

# Full-fidelity JSON
bookmarks-mcp export backup.json --format json
bookmarks-mcp import backup.json --format json
```

### Local development

```bash
git clone git@github.com:yazilim-vip/bookmarks-mcp.git
cd bookmarks-mcp
uv sync --group dev
uv run bookmarks-mcp          # MCP stdio server
uv run bookmarks-mcp web      # Web UI
uv run bookmarks-mcp info     # Show storage path
```

## Storage

Single JSON file, human-readable and git-diffable. Default location follows the XDG Base Directory spec:

- Linux: `~/.local/share/bookmarks-mcp/bookmarks.json`
- macOS: `~/Library/Application Support/bookmarks-mcp/bookmarks.json`
- Windows: `%LOCALAPPDATA%\bookmarks-mcp\bookmarks.json`

Override with `BOOKMARKS_MCP_DB=/path/to/file.json`.

## Tech Stack

- **Python** ≥ 3.11
- **FastMCP** — MCP server framework
- **FastAPI + Uvicorn** — local web UI
- **Pydantic** — data models
- **Jinja2** — web templates
- **BeautifulSoup4** — Netscape HTML parsing
- **uv** — Fast Python package manager and runner
