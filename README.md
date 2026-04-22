# bookmarks-mcp

[![CI](https://github.com/yazilim-vip/bookmarks-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/yazilim-vip/bookmarks-mcp/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/yazilim-vip/bookmarks-mcp)](https://github.com/yazilim-vip/bookmarks-mcp/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> MCP server for personal bookmark management. Drive your live **Google Chrome** bookmarks from any MCP client, or use a portable JSON store. Folders, tags, zero binary installs — runs with `uv`.

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

## Quickstart — Chrome backend

**Fully quit Chrome (`Cmd+Q` on macOS) before any write.** Closing the window is not enough — the server refuses writes while Chrome is running. Run `bookmarks-mcp info` any time to see **which file** the server is actually editing:

```bash
BOOKMARKS_MCP_BACKEND=chrome uvx --from git+https://github.com/yazilim-vip/bookmarks-mcp bookmarks-mcp info
# backend:      chrome
# target:       /Users/you/Library/Application Support/Google/Chrome/Default/Bookmarks
# exists:       True
# profile:      Default
# bookmarks:    42
# folders:      9
```

### Claude Code CLI

```bash
claude mcp add bookmarks \
  -e BOOKMARKS_MCP_BACKEND=chrome \
  -e BOOKMARKS_MCP_CHROME_PROFILE=Default \
  -- uvx --from git+https://github.com/yazilim-vip/bookmarks-mcp bookmarks-mcp
```

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "bookmarks": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/yazilim-vip/bookmarks-mcp", "bookmarks-mcp"],
      "env": {
        "BOOKMARKS_MCP_BACKEND": "chrome",
        "BOOKMARKS_MCP_CHROME_PROFILE": "Default"
      }
    }
  }
}
```

## Quickstart — JSON backend (default)

Self-contained bookmark store, independent of any browser. Useful for portable/syncable personal libraries and for agent workflows that shouldn't touch your live Chrome data.

```bash
claude mcp add bookmarks -- uvx --from git+https://github.com/yazilim-vip/bookmarks-mcp bookmarks-mcp
```

## Backends

Select with `BOOKMARKS_MCP_BACKEND` (default `json`).

### `chrome`

Reads and writes the `Bookmarks` JSON file that Google Chrome and other Chromium browsers maintain per profile.

| Env var | Default | Purpose |
|---|---|---|
| `BOOKMARKS_MCP_BACKEND` | `json` | Set to `chrome` to select this backend |
| `BOOKMARKS_MCP_CHROME_PROFILE` | `Default` | Profile directory name (e.g. `Profile 1`) |
| `BOOKMARKS_MCP_CHROME_PATH` | — | Fully override the path to the `Bookmarks` file |
| `BOOKMARKS_MCP_CHROME_FORCE` | — | Set to `1` to allow writes while Chrome is running (not recommended) |

Default path per OS:

- macOS: `~/Library/Application Support/Google/Chrome/<profile>/Bookmarks`
- Linux: `~/.config/google-chrome/<profile>/Bookmarks`
- Windows: `%LOCALAPPDATA%\Google\Chrome\User Data\<profile>\Bookmarks`

### Custom Chrome install / other Chromium browsers

If your `Bookmarks` file lives somewhere non-standard (portable Chrome, Chromium, Brave, Edge, Arc, Vivaldi, or a sync-shared directory), point the server at it explicitly with `BOOKMARKS_MCP_CHROME_PATH`. This overrides **both** the default user-data dir **and** the profile name:

```bash
# Brave on macOS
BOOKMARKS_MCP_CHROME_PATH="$HOME/Library/Application Support/BraveSoftware/Brave-Browser/Default/Bookmarks" \
BOOKMARKS_MCP_BACKEND=chrome \
  uvx --from git+https://github.com/yazilim-vip/bookmarks-mcp bookmarks-mcp info
```

```json
{
  "mcpServers": {
    "bookmarks": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/yazilim-vip/bookmarks-mcp", "bookmarks-mcp"],
      "env": {
        "BOOKMARKS_MCP_BACKEND": "chrome",
        "BOOKMARKS_MCP_CHROME_PATH": "/absolute/path/to/Bookmarks"
      }
    }
  }
}
```

Any Chromium-based browser works — the `Bookmarks` file format is shared. Confirm with `bookmarks-mcp info` that the `target:` line points at the file you expect before relying on it.

Behavior:

- **Close Chrome before writes.** The server refuses writes while Chrome runs.
- **Backups.** Every write snapshots to `Bookmarks.bak.<ISO8601>` next to the live file; last 10 are kept.
- **Tags are disabled.** Chrome has no tag concept. The `list_tags` / `rename_tag` / `delete_tag` tools exist but are no-ops in this mode.
- **Unknown fields preserved.** Chrome-specific state (`meta_info`, `sync_transaction_version`, guids) survives round-trips.

### `json`

Single JSON file, human-readable and git-diffable. Default location follows the XDG Base Directory spec:

- Linux: `~/.local/share/bookmarks-mcp/bookmarks.json`
- macOS: `~/Library/Application Support/bookmarks-mcp/bookmarks.json`
- Windows: `%LOCALAPPDATA%\bookmarks-mcp\bookmarks.json`

Override with `BOOKMARKS_MCP_DB=/path/to/file.json`.

## Import / Export

Netscape HTML — round-trips with Chrome/Firefox/Safari/Edge — and full-fidelity JSON backups work against whichever backend is active:

```bash
bookmarks-mcp import bookmarks.html --format html
bookmarks-mcp export bookmarks.html --format html

bookmarks-mcp export backup.json --format json
bookmarks-mcp import backup.json --format json
```

## Local development

```bash
git clone git@github.com:yazilim-vip/bookmarks-mcp.git
cd bookmarks-mcp
uv sync --group dev
uv run bookmarks-mcp          # MCP stdio server
uv run bookmarks-mcp info     # Show active backend + storage path
uv run pytest
uv run ruff check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the PR version-bump rule and backend-authoring checklist.

## Tech Stack

- **Python** ≥ 3.11
- **FastMCP** — MCP server framework
- **Pydantic** — typed data models
- **BeautifulSoup4 + lxml** — Netscape HTML parsing
- **uv** — package manager and runner

## License

[MIT](LICENSE)
