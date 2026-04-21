# Security Policy

## Reporting a vulnerability

Do **not** file a public issue. Report privately via GitHub's "Report a vulnerability" form on the repository's Security tab, or email `security@yazilim.vip`.

Include:
- Affected version (`bookmarks-mcp --version` or `pyproject.toml` line)
- Backend in use (`json` / `chrome`)
- A minimal reproduction
- Impact you believe is possible

You can expect an initial response within 7 days.

## Scope

In scope:
- Path-traversal or arbitrary-file-write via any input (import files, env vars, MCP tool arguments)
- Code execution triggered by parsing untrusted bookmark data (HTML, JSON)
- Data loss or corruption of the Chrome `Bookmarks` file beyond normal backup coverage
- Authentication bypass on the local web UI (which intentionally binds `127.0.0.1` and has no auth — remote exposure is out of scope; see below)

Out of scope:
- Binding the web UI to a public interface yourself (the README explicitly warns against this)
- Issues requiring a compromised local user account
- Denial of service from malformed input that does not corrupt state
- Third-party dependencies (report upstream; we track via Dependabot)

## Supported versions

Only the latest released `0.x` is supported. We do not backport fixes to older tags.

## Safe-use notes

- The local web UI has **no authentication** — do not expose it beyond `127.0.0.1`.
- The Chrome backend writes to a file Chrome actively manages. Writes are refused while Chrome is running (override: `BOOKMARKS_MCP_CHROME_FORCE=1`). Use the override only if you understand the risk.
- Every Chrome-backend write takes a `Bookmarks.bak.<timestamp>` snapshot, last 10 retained.
