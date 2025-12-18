import os
import sys
import time
import webbrowser


def test_open_browser_uses_webbrowser_when_success(monkeypatch):
    from funcnodes.runner._simple_server import _open_browser

    monkeypatch.setattr(time, "sleep", lambda _: None)

    opened: dict[str, str] = {}

    def fake_open(url: str):
        opened["url"] = url
        return True

    monkeypatch.setattr(webbrowser, "open", fake_open)

    # If fallback would be used, we'd see this.
    monkeypatch.setattr(
        os, "startfile", lambda url: opened.setdefault("startfile", url), raising=False
    )

    _open_browser(port=8123, host="localhost", delay=0)
    assert opened["url"] == "http://localhost:8123"
    assert "startfile" not in opened


def test_open_browser_windows_falls_back_to_startfile(monkeypatch):
    from funcnodes.runner._simple_server import _open_browser

    monkeypatch.setattr(time, "sleep", lambda _: None)

    def fake_open(_: str):
        raise RuntimeError("webbrowser.open failed")

    monkeypatch.setattr(webbrowser, "open", fake_open)
    monkeypatch.setattr(sys, "platform", "win32")

    called: dict[str, str] = {}

    def fake_startfile(url: str):
        called["url"] = url

    monkeypatch.setattr(os, "startfile", fake_startfile, raising=False)

    _open_browser(port=8123, host="localhost", delay=0)
    assert called["url"] == "http://localhost:8123"
