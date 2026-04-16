from __future__ import annotations

import socket
import threading
from contextlib import contextmanager

import pytest

from bookmarks_mcp import web_supervisor


@pytest.fixture(autouse=True)
def _reset_supervisor():
    web_supervisor.reset_for_tests()
    yield
    web_supervisor.reset_for_tests()


@contextmanager
def listening_socket(port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(1)

    accept_thread = threading.Thread(
        target=_drain_accept_loop,
        args=(sock,),
        daemon=True,
    )
    accept_thread.start()
    try:
        yield port
    finally:
        sock.close()


def _drain_accept_loop(sock: socket.socket) -> None:
    while True:
        try:
            client, _ = sock.accept()
            client.close()
        except OSError:
            return


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_status_reports_not_running_initially():
    web_supervisor._port = _free_port()
    state = web_supervisor.status()
    assert state == {"supervised": False, "running": False, "url": None, "pid": None}


def test_open_ui_returns_external_status_when_port_already_bound():
    port = _free_port()
    with listening_socket(port):
        result = web_supervisor.open_ui(port=port, open_in_browser=False)
    assert result["status"] == "port_in_use_externally"
    assert result["url"] == f"http://127.0.0.1:{port}"


def test_open_ui_spawns_subprocess_and_close_terminates_it(monkeypatch):
    spawn_calls: list[int] = []

    class FakePopen:
        def __init__(self, port: int) -> None:
            self.pid = 99999
            self.port = port
            self._returncode: int | None = None

        def poll(self) -> int | None:
            return self._returncode

        def terminate(self) -> None:
            self._returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            return 0

        def kill(self) -> None:
            self._returncode = -9

    def fake_spawn(port: int) -> FakePopen:
        spawn_calls.append(port)
        return FakePopen(port)

    monkeypatch.setattr(web_supervisor, "_spawn", fake_spawn)
    monkeypatch.setattr(web_supervisor, "_wait_until_ready", lambda port, timeout=5.0: True)
    monkeypatch.setattr(web_supervisor, "_port_in_use", lambda port: False)
    monkeypatch.setattr(web_supervisor.webbrowser, "open", lambda url: None)

    port = _free_port()
    first = web_supervisor.open_ui(port=port, open_in_browser=False)
    assert first["status"] == "started"
    assert first["url"] == f"http://127.0.0.1:{port}"
    assert spawn_calls == [port]

    # Calling again should reuse the supervised process, not spawn a second one.
    second = web_supervisor.open_ui(port=port, open_in_browser=False)
    assert second["status"] == "already_running"
    assert spawn_calls == [port]

    state = web_supervisor.status()
    assert state["supervised"] is True
    assert state["running"] is True

    assert web_supervisor.close_ui() == "stopped"
    assert web_supervisor.close_ui() == "not_running"


def test_open_ui_reports_when_subprocess_does_not_become_ready(monkeypatch):
    class DeadPopen:
        pid = 12345

        def poll(self) -> int | None:
            return None

        def terminate(self) -> None: ...

        def wait(self, timeout: float | None = None) -> int:
            return 0

        def kill(self) -> None: ...

    monkeypatch.setattr(web_supervisor, "_spawn", lambda port: DeadPopen())
    monkeypatch.setattr(web_supervisor, "_wait_until_ready", lambda port, timeout=5.0: False)
    monkeypatch.setattr(web_supervisor, "_port_in_use", lambda port: False)

    port = _free_port()
    result = web_supervisor.open_ui(port=port, open_in_browser=False)
    assert result["status"] == "started_but_not_responding"
    assert "hint" in result
