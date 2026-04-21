# Contributing

Thanks for your interest in improving `bookmarks-mcp`.

## Development setup

Requires Python 3.11+ and [`uv`](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone git@github.com:yazilim-vip/bookmarks-mcp.git
cd bookmarks-mcp
uv sync --group dev
```

## Running things locally

```bash
uv run bookmarks-mcp          # MCP stdio server
uv run bookmarks-mcp web      # Web UI at http://127.0.0.1:8765
uv run bookmarks-mcp info     # Show active backend + storage path
```

## Before opening a PR

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

All three must pass — CI gates on the same checks.

## Required: bump the version

Every PR must bump `version` in `pyproject.toml` higher than `main`. CI blocks the merge otherwise. Use [SemVer](https://semver.org/):

- **patch** (`0.7.0 → 0.7.1`): docs, tests, internal refactors with no behavior change
- **minor** (`0.7.0 → 0.8.0`): new features, new backends, new env vars — backward compatible
- **major** (`0.x.y → 1.0.0`): breaking changes to CLI, MCP tool signatures, or env var contracts

On merge to `main`, the CI workflow tags `vX.Y.Z` and publishes a GitHub Release automatically.

## Working on backends

Storage is pluggable via the `Storage` ABC at `src/bookmarks_mcp/storage/base.py`. New backends:

1. Implement `load`, `save`, `transaction` in a new module under `src/bookmarks_mcp/storage/`
2. Register it in `storage/factory.py` with a new `BACKEND_<NAME>` constant
3. Document the env vars in `README.md` and `AGENTS.md`
4. Add tests under `tests/test_<name>_storage.py`

Non-negotiables for any backend that writes to external state (like Chrome):

- Back up before writing
- Detect and refuse unsafe conditions (e.g., the owning process running)
- Preserve unknown fields on round-trip

## Filing issues

Include: OS, Python version, backend (`json` / `chrome`), redacted relevant env vars, and a minimal reproduction. For Chrome-backend issues, also include the profile name and (if safe to share) a trimmed excerpt of the `Bookmarks` JSON.

## Code style

- Ruff is the only style authority — no hand-rolled formatting debates
- Prefer small, focused modules over deep class hierarchies
- Write tests for behavior, not implementation details
- No SQLite, no servers-beyond-FastAPI, no platform-specific code outside of dedicated modules (see `storage/chrome.py` for the exception pattern)
