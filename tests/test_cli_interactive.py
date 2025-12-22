import io
import sys

import pytest

pytestmark = pytest.mark.cli


class QueueIO:
    def __init__(self, asks=None, confirms=None, ints=None):
        self._asks = iter(asks or [])
        self._confirms = iter(confirms or [])
        self._ints = iter(ints or [])

    def ask(self, *args, **kwargs):
        return next(self._asks)

    def confirm(self, *args, **kwargs):
        return next(self._confirms)

    def ask_int(self, *args, **kwargs):
        return next(self._ints)


def test_main_launches_interactive_when_no_subcommand(monkeypatch):
    from funcnodes.cli import main as main_mod

    called: dict = {}

    def fake_run_interactive(args=None):
        called["args"] = args

    monkeypatch.setattr(main_mod, "run_interactive_cli", fake_run_interactive)
    monkeypatch.setenv("USE_SUBPROCESS_MONITOR", "0")
    monkeypatch.setattr(sys, "argv", ["funcnodes"])

    main_mod.main()

    assert "args" in called


def test_main_launches_interactive_for_cli_subcommand(monkeypatch):
    from funcnodes.cli import main as main_mod

    called: dict = {}

    def fake_run_interactive(args=None):
        called["args"] = args

    monkeypatch.setattr(main_mod, "run_interactive_cli", fake_run_interactive)
    monkeypatch.setenv("USE_SUBPROCESS_MONITOR", "0")
    monkeypatch.setattr(sys, "argv", ["funcnodes", "cli"])

    main_mod.main()

    assert "args" in called


def test_interactive_runserver_dispatches(monkeypatch):
    from funcnodes.cli import interactive as interactive_mod

    captured: dict = {}

    def fake_task_run_server(args):
        captured["args"] = args

    monkeypatch.setattr(interactive_mod, "task_run_server", fake_task_run_server)

    io_queue = QueueIO(
        asks=[
            "1",  # main menu -> runserver
            "127.0.0.1",  # server host
            "worker.local",  # worker host
            "0",  # main menu -> exit
        ],
        confirms=[
            True,  # open browser
            False,  # start worker manager
            True,  # worker ssl
        ],
        ints=[
            9001,  # server port
            9200,  # worker port
        ],
    )

    console = interactive_mod.Console(file=io.StringIO(), force_terminal=False)
    interactive_mod.run_interactive_cli(io=io_queue, console=console)

    args = captured["args"]
    assert args.host == "127.0.0.1"
    assert args.port == 9001
    assert args.no_browser is True
    assert args.no_manager is False
    assert args.worker_host == "worker.local"
    assert args.worker_port == 9200
    assert args.worker_ssl is True
    assert args.worker_manager_host is None
    assert args.worker_manager_port is None
    assert args.worker_manager_ssl is False
