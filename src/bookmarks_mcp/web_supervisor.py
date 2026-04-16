"""Manage a background web UI subprocess started from the MCP server.

Lets the user open the local web UI on demand by asking the agent
("open my bookmarks UI"), without ever leaving the chat. The supervised
process inherits this server's environment (notably ``BOOKMARKS_MCP_DB``)
and is terminated when the MCP server exits.
"""

from __future__ import annotations

import atexit
import socket
import subprocess
import sys
import time
import webbrowser
from typing import Any

DEFAULT_PORT = 8765
_HOST = "127.0.0.1"

_process: subprocess.Popen[bytes] | None = None
_port: int = DEFAULT_PORT


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((_HOST, port)) == 0


def _spawn(port: int) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-m", "bookmarks_mcp", "web", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_until_ready(port: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_in_use(port):
            return True
        time.sleep(0.1)
    return False


def open_ui(port: int = DEFAULT_PORT, open_in_browser: bool = True) -> dict[str, Any]:
    """Start (or reuse) the web UI on ``port`` and return its URL."""
    global _process, _port
    url = f"http://{_HOST}:{port}"

    if _process is not None and _process.poll() is None and _port == port:
        if open_in_browser:
            webbrowser.open(url)
        return {"url": url, "status": "already_running", "pid": _process.pid}

    if _port_in_use(port):
        if open_in_browser:
            webbrowser.open(url)
        return {"url": url, "status": "port_in_use_externally"}

    _process = _spawn(port)
    _port = port
    if not _wait_until_ready(port):
        return {
            "url": url,
            "status": "started_but_not_responding",
            "pid": _process.pid,
            "hint": "subprocess started but isn't accepting connections — try `bookmarks-mcp web` in a terminal",
        }
    if open_in_browser:
        webbrowser.open(url)
    return {"url": url, "status": "started", "pid": _process.pid}


def close_ui() -> str:
    """Terminate the supervised web UI subprocess if it is running."""
    global _process
    if _process is None or _process.poll() is not None:
        _process = None
        return "not_running"
    _process.terminate()
    try:
        _process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        _process.kill()
        _process.wait(timeout=2)
    _process = None
    return "stopped"


def status() -> dict[str, Any]:
    """Report supervised process state plus whether the port is currently bound."""
    if _process is not None and _process.poll() is None:
        return {
            "supervised": True,
            "running": True,
            "url": f"http://{_HOST}:{_port}",
            "pid": _process.pid,
        }
    if _port_in_use(_port):
        return {
            "supervised": False,
            "running": True,
            "url": f"http://{_HOST}:{_port}",
            "pid": None,
        }
    return {"supervised": False, "running": False, "url": None, "pid": None}


def reset_for_tests() -> None:
    """Test hook: forget any tracked subprocess without terminating it."""
    global _process, _port
    _process = None
    _port = DEFAULT_PORT


atexit.register(close_ui)
