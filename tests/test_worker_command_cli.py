import argparse
import json
from types import SimpleNamespace

import pytest
import pytest_funcnodes  # noqa: F401


def test_add_worker_parser_supports_command_and_collects_unknown_kwargs():
    from funcnodes.__main__ import add_worker_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_worker_parser(subparsers)

    args, unknown = parser.parse_known_args(
        [
            "worker",
            "--uuid",
            "worker-123",
            "command",
            "-c",
            "get_meta",
            "--nid",
            "node552",
            "--value",
            "34.7",
            "--set_default",
        ]
    )

    assert args.task == "worker"
    assert args.workertask == "command"
    assert args.uuid == "worker-123"
    assert args.command == "get_meta"
    assert unknown == ["--nid", "node552", "--value", "34.7", "--set_default"]


def test_parse_command_kwargs_parses_pairs_and_infers_json_types():
    from funcnodes.__main__ import parse_command_kwargs

    kwargs = parse_command_kwargs(
        [
            "--count",
            "2",
            "--value",
            "34.7",
            "--enabled",
            "true",
            "--data",
            '{"position": [100, 200]}',
            "--items",
            '["a", "b"]',
            "--none",
            "null",
        ]
    )

    assert kwargs["count"] == 2
    assert kwargs["value"] == 34.7
    assert kwargs["enabled"] is True
    assert kwargs["data"] == {"position": [100, 200]}
    assert kwargs["items"] == ["a", "b"]
    assert kwargs["none"] is None


def test_parse_command_kwargs_supports_boolean_flags_without_values():
    from funcnodes.__main__ import parse_command_kwargs

    kwargs = parse_command_kwargs(["--set_default", "--other", "x"])
    assert kwargs == {"set_default": True, "other": "x"}


def test_parse_command_kwargs_falls_back_to_int_for_leading_zero_numbers():
    from funcnodes.__main__ import parse_command_kwargs

    kwargs = parse_command_kwargs(["--value", "001"])
    assert kwargs == {"value": 1}


def test_parse_command_kwargs_rejects_positional_tokens():
    from funcnodes.__main__ import parse_command_kwargs

    with pytest.raises(ValueError, match="Unexpected argument"):
        parse_command_kwargs(["nid", "node552"])


async def test_call_worker_command_returns_result_and_sends_kwargs(monkeypatch):
    import aiohttp
    from aiohttp import WSMsgType

    from funcnodes.__main__ import call_worker_command

    captured: dict = {}

    class _FakeWS:
        async def send_str(self, data: str):
            captured["sent"] = json.loads(data)

        async def receive(self):
            return SimpleNamespace(
                type=WSMsgType.TEXT,
                data=json.dumps({"type": "result", "result": {"ok": True}}),
            )

    class _FakeWSContext:
        async def __aenter__(self):
            return _FakeWS()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeSession:
        def __init__(self, timeout=None):
            self._timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def ws_connect(self, url: str):
            captured["url"] = url
            return _FakeWSContext()

    monkeypatch.setattr(aiohttp, "ClientSession", _FakeSession)

    worker_config = {"uuid": "worker-123", "host": "0.0.0.0", "port": 1234}
    result = await call_worker_command(
        worker_config=worker_config,
        command="get_meta",
        kwargs={"a": 1},
        timeout=5,
    )

    assert captured["url"] == "ws://127.0.0.1:1234"
    assert captured["sent"] == {"type": "cmd", "cmd": "get_meta", "kwargs": {"a": 1}}
    assert result == {"ok": True}


async def test_call_worker_command_raises_on_error_response(monkeypatch):
    import aiohttp
    from aiohttp import WSMsgType

    from funcnodes.__main__ import call_worker_command

    class _FakeWS:
        async def send_str(self, data: str):
            return None

        async def receive(self):
            return SimpleNamespace(
                type=WSMsgType.TEXT,
                data=json.dumps({"type": "error", "error": "boom"}),
            )

    class _FakeWSContext:
        async def __aenter__(self):
            return _FakeWS()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeSession:
        def __init__(self, timeout=None):
            self._timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def ws_connect(self, url: str):
            return _FakeWSContext()

    monkeypatch.setattr(aiohttp, "ClientSession", _FakeSession)

    worker_config = {"uuid": "worker-123", "host": "127.0.0.1", "port": 1234}
    with pytest.raises(RuntimeError, match="boom"):
        await call_worker_command(
            worker_config=worker_config,
            command="get_meta",
            kwargs={},
            timeout=5,
        )


async def test_call_worker_command_requires_port():
    from funcnodes.__main__ import call_worker_command

    with pytest.raises(ValueError, match="no port configured"):
        await call_worker_command(
            worker_config={"uuid": "worker-123", "host": "127.0.0.1"},
            command="get_meta",
            kwargs={},
            timeout=1,
        )
