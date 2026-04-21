# bookmarks-mcp

> MCP server + local web UI for personal bookmark management. Folders, tags, portable JSON storage — or drive your real Google Chrome bookmarks directly. Zero binary installs, runs with `uv`.

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

The minimal flow needs **no second command** — once the MCP is installed, just ask the agent to open the UI:

> *open my bookmarks UI*

The agent calls the `open_web_ui` tool, which spawns the FastAPI server as a background subprocess (sharing the same JSON file as the MCP) and opens `http://127.0.0.1:8765` in your browser. Tools to manage it: `open_web_ui`, `close_web_ui`, `web_ui_status`. The subprocess auto-stops when the MCP server exits.

If you'd rather start it yourself in a terminal:

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

Select a backend with `BOOKMARKS_MCP_BACKEND`. Defaults to `json`.

### `json` backend (default)

Single JSON file, human-readable and git-diffable. Default location follows the XDG Base Directory spec:

- Linux: `~/.local/share/bookmarks-mcp/bookmarks.json`
- macOS: `~/Library/Application Support/bookmarks-mcp/bookmarks.json`
- Windows: `%LOCALAPPDATA%\bookmarks-mcp\bookmarks.json`

Override with `BOOKMARKS_MCP_DB=/path/to/file.json`.

### `chrome` backend

Reads and writes the `Bookmarks` JSON file that Google Chrome (and other Chromium browsers) maintain per profile.

```bash
export BOOKMARKS_MCP_BACKEND=chrome
export BOOKMARKS_MCP_CHROME_PROFILE=Default   # or "Profile 1", etc.
# Optional: fully override the path
export BOOKMARKS_MCP_CHROME_PATH=/custom/path/to/Bookmarks
```

Defaults per OS:

- macOS: `~/Library/Application Support/Google/Chrome/<profile>/Bookmarks`
- Linux: `~/.config/google-chrome/<profile>/Bookmarks`
- Windows: `%LOCALAPPDATA%\Google\Chrome\User Data\<profile>\Bookmarks`

Caveats:

- **Close Chrome before any write.** The server refuses writes while Chrome is running. Override with `BOOKMARKS_MCP_CHROME_FORCE=1` (not recommended — Chrome can overwrite your changes).
- **Tags are disabled** — Chrome has no tag concept. Tag-related tools still exist but will be no-ops on the Chrome backend.
- **Backups**: every write produces a `Bookmarks.bak.<timestamp>` next to the live file; the last 10 are kept.
- **Netscape HTML import/export still work** — use them if you'd rather batch-edit offline.

## Tech Stack

- **Python** ≥ 3.11
- **FastMCP** — MCP server framework
- **FastAPI + Uvicorn** — local web UI
- **Pydantic** — data models
- **Jinja2** — web templates
- **BeautifulSoup4** — Netscape HTML parsing
- **uv** — Fast Python package manager and runner
