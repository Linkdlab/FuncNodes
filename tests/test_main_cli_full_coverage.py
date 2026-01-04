# mainly to make sure the cli api does not change by accident
import argparse
import json
import runpy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import pytest_funcnodes  # noqa: F401

pytestmark = pytest.mark.cli


@pytest.fixture()
def worker_dir() -> Path:
    assert pytest_funcnodes.get_in_test(), "Not in test mode"
    from funcnodes.worker.worker_manager import WorkerManager

    manager = WorkerManager(debug=False)
    path = Path(manager.worker_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture()
def make_worker_config(worker_dir: Path):
    def _make(**overrides):
        cfg = {
            "uuid": overrides.pop("uuid", "worker-coverage"),
            "name": overrides.pop("name", "coverage"),
            "type": overrides.pop("type", "WSWorker"),
            "env_path": overrides.pop("env_path", None),
        }
        cfg.update(overrides)
        worker_file = worker_dir / f"worker_{cfg['uuid']}.json"
        worker_file.write_text(json.dumps(cfg), encoding="utf-8")
        return cfg

    return _make


@pytest_funcnodes.funcnodes_test
def test_task_standalone_register_calls_register(monkeypatch):
    from funcnodes.cli.tasks import task_standalone

    called = {}
    module = ModuleType("funcnodes.runner.register")

    def register_fnw():
        called["ok"] = True

    module.register_fnw = register_fnw
    monkeypatch.setitem(sys.modules, "funcnodes.runner.register", module)

    args = SimpleNamespace(register=True)
    task_standalone(args)

    assert called["ok"] is True


@pytest_funcnodes.funcnodes_test
def test_task_standalone_missing_file_raises(tmp_path: Path):
    from funcnodes.cli.tasks import task_standalone

    missing = tmp_path / "missing.fnw"
    args = SimpleNamespace(
        register=False,
        fnw_file=str(missing),
        config_dir=None,
        ui_port=None,
        host="127.0.0.1",
        worker_port=None,
        open_browser=True,
        debug=False,
    )

    with pytest.raises(FileNotFoundError):
        task_standalone(args)


@pytest_funcnodes.funcnodes_test
def test_task_standalone_runs_server_and_shutdown(monkeypatch, tmp_path: Path):
    from funcnodes.cli.tasks import task_standalone

    called: dict = {}
    launcher_holder: dict = {}

    class FakeLauncher:
        def __init__(
            self,
            fnw_path,
            config_dir,
            host,
            ui_port,
            worker_port,
            open_browser,
            debug,
            on_worker_shutdown,
        ):
            launcher_holder["instance"] = self
            self.shutdown_calls = 0

        def ensure_worker(self, import_fnw=True):
            called["ensure_worker"] = import_fnw
            return 5555

        def run_forever(self):
            called["run_forever"] = True

        def shutdown(self):
            self.shutdown_calls += 1

    standalone_module = ModuleType("funcnodes.runner.standalone")
    standalone_module.StandaloneLauncher = FakeLauncher
    standalone_module.pick_free_port = lambda host: 8500
    monkeypatch.setitem(sys.modules, "funcnodes.runner.standalone", standalone_module)

    server_module = ModuleType("funcnodes_react_flow")

    def run_server(**kwargs):
        called["server_kwargs"] = kwargs
        register_shutdown_handler = kwargs.get("register_shutdown_handler")
        if register_shutdown_handler:

            def handler(delay):
                called["shutdown_delay"] = delay

            register_shutdown_handler(handler)

    server_module.run_server = run_server
    monkeypatch.setitem(sys.modules, "funcnodes_react_flow", server_module)

    fnw_path = tmp_path / "example.fnw"
    fnw_path.write_text("data", encoding="utf-8")

    args = SimpleNamespace(
        register=False,
        fnw_file=str(fnw_path),
        config_dir=None,
        ui_port=None,
        host="127.0.0.1",
        worker_port=0,
        open_browser=True,
        debug=True,
    )

    task_standalone(args)

    launcher = launcher_holder["instance"]
    assert called["ensure_worker"] is True
    assert called["server_kwargs"]["port"] == 8500
    assert called["server_kwargs"]["worker_port"] == 5555
    assert called["shutdown_delay"] == 0.5
    assert launcher.shutdown_calls >= 1


@pytest_funcnodes.funcnodes_test
def test_task_standalone_shutdown_without_handler(monkeypatch, tmp_path: Path):
    from funcnodes.cli.tasks import task_standalone

    launcher_holder: dict = {}

    class FakeLauncher:
        def __init__(
            self,
            fnw_path,
            config_dir,
            host,
            ui_port,
            worker_port,
            open_browser,
            debug,
            on_worker_shutdown,
        ):
            launcher_holder["instance"] = self
            self.shutdown_calls = 0

        def ensure_worker(self, import_fnw=True):
            return 5556

        def run_forever(self):
            return None

        def shutdown(self):
            self.shutdown_calls += 1

    standalone_module = ModuleType("funcnodes.runner.standalone")
    standalone_module.StandaloneLauncher = FakeLauncher
    standalone_module.pick_free_port = lambda host: 8501
    monkeypatch.setitem(sys.modules, "funcnodes.runner.standalone", standalone_module)

    server_module = ModuleType("funcnodes_react_flow")

    def run_server(**kwargs):
        return None

    server_module.run_server = run_server
    monkeypatch.setitem(sys.modules, "funcnodes_react_flow", server_module)

    fnw_path = tmp_path / "nohandler.fnw"
    fnw_path.write_text("data", encoding="utf-8")

    args = SimpleNamespace(
        register=False,
        fnw_file=str(fnw_path),
        config_dir=None,
        ui_port=None,
        host="127.0.0.1",
        worker_port=0,
        open_browser=True,
        debug=True,
    )

    task_standalone(args)

    launcher = launcher_holder["instance"]
    assert launcher.shutdown_calls >= 1


@pytest_funcnodes.funcnodes_test
def test_task_standalone_keyboard_interrupt_triggers_shutdown(
    monkeypatch, tmp_path: Path
):
    from funcnodes.cli.tasks import task_standalone

    launcher_holder: dict = {}

    class FakeLauncher:
        def __init__(
            self,
            fnw_path,
            config_dir,
            host,
            ui_port,
            worker_port,
            open_browser,
            debug,
            on_worker_shutdown,
        ):
            launcher_holder["instance"] = self
            self.shutdown_calls = 0

        def ensure_worker(self, import_fnw=True):
            return 5557

        def run_forever(self):
            return None

        def shutdown(self):
            self.shutdown_calls += 1

    standalone_module = ModuleType("funcnodes.runner.standalone")
    standalone_module.StandaloneLauncher = FakeLauncher
    standalone_module.pick_free_port = lambda host: 8502
    monkeypatch.setitem(sys.modules, "funcnodes.runner.standalone", standalone_module)

    server_module = ModuleType("funcnodes_react_flow")

    def run_server(**kwargs):
        raise KeyboardInterrupt()

    server_module.run_server = run_server
    monkeypatch.setitem(sys.modules, "funcnodes_react_flow", server_module)

    fnw_path = tmp_path / "interrupt.fnw"
    fnw_path.write_text("data", encoding="utf-8")

    args = SimpleNamespace(
        register=False,
        fnw_file=str(fnw_path),
        config_dir=None,
        ui_port=None,
        host="127.0.0.1",
        worker_port=0,
        open_browser=True,
        debug=True,
    )

    task_standalone(args)

    launcher = launcher_holder["instance"]
    assert launcher.shutdown_calls >= 1


@pytest_funcnodes.funcnodes_test
def test_start_new_worker_create_only(monkeypatch):
    from funcnodes.cli import worker as worker_mod

    async def fake_new_worker(
        self, name=None, uuid=None, workertype="WSWorker", **kwargs
    ):
        return {"uuid": uuid or "fake-uuid", "name": name, "type": workertype}

    monkeypatch.setattr(
        worker_mod.fn.worker.worker_manager.WorkerManager, "new_worker", fake_new_worker
    )

    result = worker_mod.start_new_worker(
        name="cli-new-worker", in_venv=False, create_only=True
    )
    assert result is None


@pytest_funcnodes.funcnodes_test
def test_start_new_worker_calls_start_existing(monkeypatch):
    from funcnodes.cli import worker as worker_mod

    called: dict = {}

    async def fake_new_worker(
        self, name=None, uuid=None, workertype="WSWorker", **kwargs
    ):
        return {"uuid": uuid or "fake-uuid-2", "name": name, "type": workertype}

    def fake_start_existing_worker(**kwargs):
        called["kwargs"] = kwargs
        return "started"

    monkeypatch.setattr(
        worker_mod.fn.worker.worker_manager.WorkerManager, "new_worker", fake_new_worker
    )
    monkeypatch.setattr(worker_mod, "start_existing_worker", fake_start_existing_worker)

    result = worker_mod.start_new_worker(
        name="cli-new-worker-2",
        in_venv=False,
        create_only=False,
        profile=True,
    )

    assert result == "started"
    assert called["kwargs"]["profile"] is True


@pytest_funcnodes.funcnodes_test
def test_start_existing_worker_uses_virtual_env_and_subprocess(
    monkeypatch, tmp_path: Path, make_worker_config
):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(
        uuid="worker-subprocess",
        env_path="env",
        update_on_startup={
            "funcnodes": True,
            "funcnodes-core": True,
            "funcnodes-worker": True,
        },
    )

    python_path = tmp_path / "python"
    python_path.write_text("#!/usr/bin/env python", encoding="utf-8")
    installs = []

    class FakeEnv:
        python_exe = python_path

        def install_package(self, name, upgrade=False):
            installs.append((name, upgrade))

    monkeypatch.setattr(
        worker_mod.venvmngr.UVVenvManager,
        "get_virtual_env",
        lambda path: FakeEnv(),
    )

    called: dict = {}

    def fake_run(cmd):
        called["cmd"] = cmd

    monkeypatch.setattr(worker_mod.subprocess, "run", fake_run)

    result = worker_mod.start_existing_worker(
        uuid=cfg["uuid"],
        name=None,
        workertype="WSWorker",
        debug=True,
        profile=True,
    )

    assert result is None
    assert called["cmd"][0] == str(python_path)
    assert "-m" in called["cmd"]
    assert ("funcnodes", True) in installs
    assert ("funcnodes-core", True) in installs
    assert ("funcnodes-worker", True) in installs


@pytest_funcnodes.funcnodes_test
def test_start_existing_worker_skips_updates_when_disabled(
    monkeypatch, tmp_path: Path, make_worker_config
):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(
        uuid="worker-no-update",
        env_path="env",
        update_on_startup={"funcnodes": False, "funcnodes-core": False},
    )

    python_path = tmp_path / "python"
    python_path.write_text("#!/usr/bin/env python", encoding="utf-8")
    installs = []

    class FakeEnv:
        python_exe = python_path

        def install_package(self, name, upgrade=False):
            installs.append((name, upgrade))

    monkeypatch.setattr(
        worker_mod.venvmngr.UVVenvManager,
        "get_virtual_env",
        lambda path: FakeEnv(),
    )

    called: dict = {}

    def fake_run(cmd):
        called["cmd"] = cmd

    monkeypatch.setattr(worker_mod.subprocess, "run", fake_run)

    worker_mod.start_existing_worker(
        uuid=cfg["uuid"],
        name=None,
        workertype="WSWorker",
        debug=False,
        profile=False,
    )

    assert called["cmd"][0] == str(python_path)
    assert installs == []


@pytest_funcnodes.funcnodes_test
def test_start_existing_worker_raises_when_python_missing(
    monkeypatch, tmp_path: Path, make_worker_config
):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(uuid="worker-missing", env_path="env")

    class FakeEnv:
        python_exe = tmp_path / "missing"

        def install_package(self, name, upgrade=False):
            return None

    monkeypatch.setattr(
        worker_mod.venvmngr.UVVenvManager,
        "get_virtual_env",
        lambda path: FakeEnv(),
    )

    with pytest.raises(Exception, match="Python executable not found"):
        worker_mod.start_existing_worker(
            uuid=cfg["uuid"],
            name=None,
            workertype="WSWorker",
            debug=False,
            profile=False,
        )


@pytest_funcnodes.funcnodes_test
def test_start_existing_worker_runs_worker_class(
    monkeypatch, tmp_path: Path, make_worker_config
):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(uuid="worker-direct", env_path=None, type="DummyWorker")

    class DummyWorker:
        ran = False

        def __init__(self, uuid, debug=False):
            self.uuid = uuid
            self.debug = debug

        def run_forever(self):
            DummyWorker.ran = True

    monkeypatch.setattr(worker_mod.fn.worker, "DummyWorker", DummyWorker, raising=False)
    monkeypatch.setattr(worker_mod.fn.logging, "set_logging_dir", lambda path: None)
    monkeypatch.setattr(
        worker_mod, "worker_json_get_data_path", lambda cfg: str(tmp_path)
    )

    worker_mod.start_existing_worker(
        uuid=cfg["uuid"],
        name=None,
        workertype=None,
        debug=False,
        profile=False,
    )

    assert DummyWorker.ran is True


@pytest_funcnodes.funcnodes_test
def test_start_existing_worker_runs_worker_class_with_explicit_type(
    monkeypatch, tmp_path: Path, make_worker_config
):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(uuid="worker-direct-explicit", env_path=None, type="Other")

    class DummyWorker:
        ran = False

        def __init__(self, uuid, debug=False):
            self.uuid = uuid
            self.debug = debug

        def run_forever(self):
            DummyWorker.ran = True

    monkeypatch.setattr(worker_mod.fn.worker, "DummyWorker", DummyWorker, raising=False)
    monkeypatch.setattr(worker_mod.fn.logging, "set_logging_dir", lambda path: None)
    monkeypatch.setattr(
        worker_mod, "worker_json_get_data_path", lambda cfg: str(tmp_path)
    )

    worker_mod.start_existing_worker(
        uuid=cfg["uuid"],
        name=None,
        workertype="DummyWorker",
        debug=False,
        profile=False,
    )

    assert DummyWorker.ran is True


@pytest_funcnodes.funcnodes_test
def test_stop_worker_invokes_manager(monkeypatch, make_worker_config):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(uuid="worker-stop")
    called: dict = {}

    async def fake_stop(self, uuid):
        called["uuid"] = uuid

    monkeypatch.setattr(
        worker_mod.fn.worker.worker_manager.WorkerManager,
        "stop_worker",
        fake_stop,
    )

    worker_mod.stop_worker(
        uuid=cfg["uuid"], name=None, workertype="WSWorker", debug=False
    )
    assert called["uuid"] == cfg["uuid"]


@pytest_funcnodes.funcnodes_test
def test_get_worker_conf_with_matching_uuid_and_name(make_worker_config):
    from funcnodes.cli.worker import _get_worker_conf

    cfg = make_worker_config(uuid="worker-match", name="match")
    result = _get_worker_conf(
        uuid=cfg["uuid"],
        name=cfg["name"],
        workertype="WSWorker",
        debug=False,
    )

    assert result["uuid"] == cfg["uuid"]


# @pytest_funcnodes.funcnodes_test
# def test_listen_worker_handles_removed_log(monkeypatch, tmp_path: Path, make_worker_config):
#     from funcnodes import __main__ as main_mod

#     cfg = make_worker_config(uuid="worker-listen-removed")
#     log_dir = tmp_path / "logs"
#     log_dir.mkdir()
#     log_file = log_dir / "worker.log"
#     log_file.write_text("line1\n", encoding="utf-8")

#     monkeypatch.setattr(main_mod, "worker_json_get_data_path", lambda cfg: str(log_dir))

#     out_lines: list[str] = []

#     def out(line):
#         out_lines.append(line)

#     def fake_sleep(duration):
#         if duration == 0.5:
#             if log_file.exists():
#                 log_file.unlink()
#             return
#         if duration == 5:
#             raise StopIteration()

#     monkeypatch.setattr(main_mod.time, "sleep", fake_sleep)

#     with pytest.raises(StopIteration):
#         main_mod.listen_worker(
#             uuid=cfg["uuid"],
#             name=None,
#             workertype="WSWorker",
#             debug=False,
#             out=out,
#         )

#     assert "line1" in "".join(out_lines)


@pytest_funcnodes.funcnodes_test
def test_listen_worker_handles_log_rotation(
    monkeypatch, tmp_path: Path, make_worker_config
):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(uuid="worker-listen-rotate")
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "worker.log"
    log_file.write_text("line1\nline2\n", encoding="utf-8")

    monkeypatch.setattr(
        worker_mod, "worker_json_get_data_path", lambda cfg: str(log_dir)
    )

    out_lines: list[str] = []

    def out(line):
        out_lines.append(line)

    def fake_sleep(duration):
        if duration == 0.5:
            log_file.write_text("", encoding="utf-8")
            return
        if duration == 5:
            raise StopIteration()

    monkeypatch.setattr(worker_mod.time, "sleep", fake_sleep)

    with pytest.raises(StopIteration):
        worker_mod.listen_worker(
            uuid=cfg["uuid"],
            name=None,
            workertype="WSWorker",
            debug=False,
            out=out,
        )

    assert "line1" in "".join(out_lines)


@pytest_funcnodes.funcnodes_test
def test_listen_worker_skips_when_log_missing(
    monkeypatch, tmp_path: Path, make_worker_config
):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(uuid="worker-listen-missing")
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    monkeypatch.setattr(
        worker_mod, "worker_json_get_data_path", lambda cfg: str(log_dir)
    )

    def fake_sleep(duration):
        if duration == 5:
            raise StopIteration()

    monkeypatch.setattr(worker_mod.time, "sleep", fake_sleep)

    with pytest.raises(StopIteration):
        worker_mod.listen_worker(
            uuid=cfg["uuid"],
            name=None,
            workertype="WSWorker",
            debug=False,
        )


@pytest_funcnodes.funcnodes_test
def test_listen_worker_reads_new_lines_and_updates_size(
    monkeypatch, tmp_path: Path, make_worker_config
):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(uuid="worker-listen-newline")
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "worker.log"
    log_file.write_text("line1\n", encoding="utf-8")

    monkeypatch.setattr(
        worker_mod, "worker_json_get_data_path", lambda cfg: str(log_dir)
    )

    out_lines: list[str] = []
    state = {"appended": False}

    def out(line):
        out_lines.append(line)

    def fake_sleep(duration):
        if duration == 0.5 and not state["appended"]:
            with open(log_file, "a", encoding="utf-8") as handle:
                handle.write("line2\n")
            state["appended"] = True
            return
        raise StopIteration()

    monkeypatch.setattr(worker_mod.time, "sleep", fake_sleep)

    with pytest.raises(StopIteration):
        worker_mod.listen_worker(
            uuid=cfg["uuid"],
            name=None,
            workertype="WSWorker",
            debug=False,
            out=out,
        )

    assert "line2" in "".join(out_lines)


def test_parse_command_value_handles_false_none_float_string():
    from funcnodes.cli.utils import _parse_command_value

    assert _parse_command_value("false") is False
    assert _parse_command_value("TRUE") is True
    assert _parse_command_value("none") is None
    assert _parse_command_value("3.5") == 3.5
    assert _parse_command_value("hello") == "hello"


def test_parse_command_kwargs_returns_empty_for_none():
    from funcnodes.cli.utils import parse_command_kwargs

    assert parse_command_kwargs(None) == {}


def test_parse_command_kwargs_rejects_empty_key():
    from funcnodes.cli.utils import parse_command_kwargs

    class Token:
        def startswith(self, prefix):
            return True

        def __eq__(self, other):
            return False

        def __getitem__(self, item):
            return ""

    with pytest.raises(ValueError, match="Unexpected argument: --"):
        parse_command_kwargs([Token()])


async def test_call_worker_command_requires_ws_worker():
    from funcnodes.cli.worker import call_worker_command

    with pytest.raises(ValueError, match="not a WebSocket worker"):
        await call_worker_command(
            worker_config={"uuid": "worker-1", "type": "Other", "port": 1},
            command="ping",
            kwargs={},
            timeout=1,
        )


async def test_call_worker_command_times_out_after_non_text(monkeypatch):
    import aiohttp
    from aiohttp import WSMsgType

    from funcnodes.cli import worker as worker_mod

    messages = [
        SimpleNamespace(type=WSMsgType.BINARY, data=b""),
        SimpleNamespace(type=WSMsgType.TEXT, data="not json"),
    ]

    class FakeWS:
        async def send_str(self, data):
            return None

        async def receive(self):
            if messages:
                return messages.pop(0)
            return SimpleNamespace(type=WSMsgType.TEXT, data="{}")

    class FakeWSContext:
        async def __aenter__(self):
            return FakeWS()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def __init__(self, timeout=None):
            self._timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def ws_connect(self, url: str):
            return FakeWSContext()

    monkeypatch.setattr(aiohttp, "ClientSession", FakeSession)

    times = [0.0, 0.0, 0.05, 0.1, 0.15, 0.25]

    def fake_time():
        return times.pop(0) if times else 0.3

    monkeypatch.setattr(worker_mod.time, "time", fake_time)

    with pytest.raises(RuntimeError, match="Timeout waiting for result"):
        await worker_mod.call_worker_command(
            worker_config={"uuid": "worker-1", "host": "::", "port": 1234},
            command="ping",
            kwargs={},
            timeout=0.2,
        )


@pytest_funcnodes.funcnodes_test
def test_worker_command_task_prints_json(monkeypatch, make_worker_config, capsys):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(uuid="worker-cmd-json")

    async def fake_call_worker_command(**kwargs):
        return {"ok": True}

    monkeypatch.setattr(worker_mod, "call_worker_command", fake_call_worker_command)

    worker_mod.worker_command_task(
        command="ping",
        uuid=cfg["uuid"],
        name=None,
        workertype="WSWorker",
        debug=False,
    )

    captured = capsys.readouterr().out
    assert "ok" in captured


@pytest_funcnodes.funcnodes_test
def test_worker_command_task_prints_scalar(monkeypatch, make_worker_config, capsys):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(uuid="worker-cmd-scalar")

    async def fake_call_worker_command(**kwargs):
        return "done"

    monkeypatch.setattr(worker_mod, "call_worker_command", fake_call_worker_command)

    worker_mod.worker_command_task(
        command="ping",
        uuid=cfg["uuid"],
        name=None,
        workertype="WSWorker",
        debug=False,
    )

    captured = capsys.readouterr().out
    assert "done" in captured


@pytest_funcnodes.funcnodes_test
@pytest.mark.parametrize(
    ("workertask", "target_name"),
    [
        ("start", "start_existing_worker"),
        ("stop", "stop_worker"),
        ("new", "start_new_worker"),
        ("list", "list_workers"),
        ("listen", "listen_worker"),
        ("activate", "activate_worker_env"),
        ("py", "py_in_worker_env"),
        ("command", "worker_command_task"),
        ("modules", "worker_modules_task"),
    ],
)
def test_task_worker_dispatches(monkeypatch, workertask, target_name):
    from funcnodes.cli import tasks as tasks_mod

    called: dict = {}

    def stub(*args, **kwargs):
        called["name"] = target_name
        called["kwargs"] = kwargs
        return target_name

    monkeypatch.setattr(tasks_mod, target_name, stub)

    args = SimpleNamespace(
        workertask=workertask,
        uuid="worker-arg",
        name="worker-name",
        workertype="WSWorker",
        debug=False,
        profile=False,
        in_venv=False,
        create_only=False,
        full=False,
        command="ping",
        kwargs=["--a", "1"],
        moduletask="list",
    )

    result = tasks_mod.task_worker(args)
    assert called["name"] == target_name
    assert result == target_name


@pytest_funcnodes.funcnodes_test
def test_start_worker_manager_invokes_module(monkeypatch):
    from funcnodes.cli import tasks as tasks_mod

    called: dict = {}

    def fake_start_worker_manager(host=None, port=None, debug=False):
        called["args"] = (host, port, debug)

    monkeypatch.setattr(
        tasks_mod.fn.worker.worker_manager,
        "start_worker_manager",
        fake_start_worker_manager,
    )

    args = SimpleNamespace(host="127.0.0.1", port=9000, debug=True)
    tasks_mod.start_worker_manager(args)

    assert called["args"] == ("127.0.0.1", 9000, True)


@pytest_funcnodes.funcnodes_test
def test_get_worker_venv_returns_virtual_env(monkeypatch, make_worker_config):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(uuid="worker-env", env_path="/tmp/env")
    fake_env = object()

    monkeypatch.setattr(
        worker_mod.venvmngr.UVVenvManager, "get_virtual_env", lambda path: fake_env
    )

    assert worker_mod.get_worker_venv(cfg) is fake_env


@pytest_funcnodes.funcnodes_test
def test_activate_worker_env_requires_subprocess(monkeypatch, make_worker_config):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(uuid="worker-no-subprocess", env_path="/tmp/env")
    args = SimpleNamespace(
        uuid=cfg["uuid"], name=None, workertype="WSWorker", debug=False
    )

    monkeypatch.setattr(worker_mod, "subprocess", None)

    with pytest.raises(Exception, match="subprocess support"):
        worker_mod.activate_worker_env(args)


@pytest_funcnodes.funcnodes_test
def test_activate_worker_env_raises_when_env_missing(
    tmp_path: Path, make_worker_config
):
    from funcnodes.cli.worker import activate_worker_env

    cfg = make_worker_config(uuid="worker-missing-env", env_path=str(tmp_path / "env"))
    args = SimpleNamespace(
        uuid=cfg["uuid"], name=None, workertype="WSWorker", debug=False
    )

    with pytest.raises(Exception, match="Environment not found"):
        activate_worker_env(args)


@pytest_funcnodes.funcnodes_test
def test_activate_worker_env_windows_branch(
    monkeypatch, tmp_path: Path, make_worker_config
):
    from funcnodes.cli import worker as worker_mod

    env_path = tmp_path / "env-win"
    env_path.mkdir()
    cfg = make_worker_config(uuid="worker-win", env_path=str(env_path))
    args = SimpleNamespace(
        uuid=cfg["uuid"], name=None, workertype="WSWorker", debug=False
    )

    called: dict = {}

    def fake_run(cmd, shell=None, executable=None):
        called["cmd"] = cmd
        called["shell"] = shell
        called["executable"] = executable

    monkeypatch.setattr(worker_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(worker_mod.sys, "platform", "win32", raising=False)

    worker_mod.activate_worker_env(args)

    assert called["shell"] is True
    assert called["executable"] is None
    assert "activate.bat" in called["cmd"][0]


@pytest_funcnodes.funcnodes_test
def test_activate_worker_env_unix_branch(
    monkeypatch, tmp_path: Path, make_worker_config
):
    from funcnodes.cli import worker as worker_mod

    env_path = tmp_path / "env-unix"
    env_path.mkdir()
    cfg = make_worker_config(uuid="worker-unix", env_path=str(env_path))
    args = SimpleNamespace(
        uuid=cfg["uuid"], name=None, workertype="WSWorker", debug=False
    )

    called: dict = {}

    def fake_run(cmd, shell=None, executable=None):
        called["cmd"] = cmd
        called["shell"] = shell
        called["executable"] = executable

    monkeypatch.setattr(worker_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(worker_mod.sys, "platform", "linux", raising=False)
    monkeypatch.setattr(worker_mod.shutil, "which", lambda name: "/bin/bash")

    worker_mod.activate_worker_env(args)

    assert called["shell"] is True
    assert called["executable"] == "/bin/bash"
    assert "source" in called["cmd"]


@pytest_funcnodes.funcnodes_test
def test_py_in_worker_env_without_double_dash(monkeypatch, make_worker_config):
    from funcnodes.cli import worker as worker_mod

    cfg = make_worker_config(uuid="worker-py", env_path=None)
    called: dict = {}

    monkeypatch.setattr(
        worker_mod.subprocess, "run", lambda cmd: called.setdefault("cmd", cmd)
    )

    args = SimpleNamespace(
        uuid=cfg["uuid"],
        name=None,
        workertype="WSWorker",
        debug=False,
        command=["-c", "print('ok')"],
    )

    worker_mod.py_in_worker_env(args)

    assert called["cmd"][0] == sys.executable
    assert called["cmd"][1:] == ["-c", "print('ok')"]


def test_validate_standalone_args_skips_non_standalone():
    from funcnodes.cli.parser import validate_standalone_args

    parser = argparse.ArgumentParser()
    args = SimpleNamespace(task="runserver")
    validate_standalone_args(parser, args)


@pytest_funcnodes.funcnodes_test
@pytest.mark.parametrize(
    ("task", "target_name"),
    [
        ("runserver", "task_run_server"),
        ("standalone", "task_standalone"),
        ("worker", "task_worker"),
        ("startworkermanager", "start_worker_manager"),
        ("modules", "task_modules"),
    ],
)
def test_submain_dispatches(monkeypatch, task, target_name):
    from funcnodes.cli import main as main_mod

    called: dict = {}

    def stub(args):
        called["task"] = task

    monkeypatch.setattr(main_mod, target_name, stub)
    main_mod._submain(SimpleNamespace(task=task))

    assert called["task"] == task


def test_submain_raises_unknown_task():
    from funcnodes.cli.main import _submain

    with pytest.raises(Exception, match="Unknown task"):
        _submain(SimpleNamespace(task="unknown"))


def test_main_collects_unknown_worker_command_args(monkeypatch):
    from funcnodes.cli import main as main_mod

    captured: dict = {}

    def fake_submain(args):
        captured["args"] = args

    monkeypatch.setattr(main_mod, "_submain", fake_submain)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "funcnodes",
            "worker",
            "command",
            "-c",
            "get_meta",
            "--nid",
            "node1",
            "--v",
            "3",
        ],
    )
    monkeypatch.setenv("USE_SUBPROCESS_MONITOR", "0")

    main_mod.main()

    assert captured["args"].kwargs == ["--nid", "node1", "--v", "3"]


def test_main_errors_on_unknown_args(monkeypatch):
    from funcnodes.cli import main as main_mod

    monkeypatch.setattr(sys, "argv", ["funcnodes", "runserver", "--bogus"])

    with pytest.raises(SystemExit):
        main_mod.main()


def test_main_profile_warns_when_yappi_missing(monkeypatch, tmp_path: Path):
    from funcnodes.cli import main as main_mod

    captured: dict = {}
    warned: dict = {}

    monkeypatch.setattr(main_mod, "yappi", None)
    monkeypatch.setattr(
        main_mod.fn.config, "reload", lambda path: captured.setdefault("reload", path)
    )
    monkeypatch.setattr(
        main_mod.fn.FUNCNODES_LOGGER,
        "setLevel",
        lambda level: captured.setdefault("level", level),
    )
    monkeypatch.setattr(
        main_mod, "_submain", lambda args: captured.setdefault("submain", args)
    )
    monkeypatch.setattr(
        main_mod.warnings, "warn", lambda msg: warned.setdefault("msg", msg)
    )
    monkeypatch.setenv("USE_SUBPROCESS_MONITOR", "0")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "funcnodes",
            "--dir",
            str(tmp_path),
            "--debug",
            "--profile",
            "modules",
            "list",
        ],
    )

    main_mod.main()

    assert str(tmp_path) in captured["reload"]
    assert captured["level"] == "DEBUG"
    assert "profiling is not available" in warned["msg"]


def test_main_profile_with_yappi(monkeypatch):
    from funcnodes.cli import main as main_mod

    class FakeStats:
        def __init__(self, yappi_ref):
            self._yappi = yappi_ref

        def save(self, filename, fmt):
            self._yappi.calls.append(("save", filename, fmt))
            self._yappi.custom_running = False

    class FakeYappi:
        def __init__(self):
            self.custom_running = False
            self.calls = []

        def set_clock_type(self, clock):
            self.calls.append(("clock", clock))

        def start(self):
            self.calls.append(("start", True))

        def stop(self):
            self.calls.append(("stop", True))

        def get_func_stats(self):
            return FakeStats(self)

    class FakeThread:
        def __init__(self, target=None, args=(), daemon=None):
            self._target = target
            self._args = args

        def start(self):
            self._target(*self._args)

    fake_yappi = FakeYappi()
    monkeypatch.setattr(main_mod, "yappi", fake_yappi)
    monkeypatch.setattr(main_mod.threading, "Thread", FakeThread)
    monkeypatch.setattr(main_mod, "_submain", lambda args: None)
    monkeypatch.setattr(main_mod.time, "sleep", lambda interval: None)
    monkeypatch.setenv("USE_SUBPROCESS_MONITOR", "0")
    monkeypatch.setattr(sys, "argv", ["funcnodes", "--profile", "modules", "list"])

    main_mod.main()

    assert ("clock", "WALL") in fake_yappi.calls
    assert ("start", True) in fake_yappi.calls
    assert ("stop", True) in fake_yappi.calls
    assert any(call[0] == "save" for call in fake_yappi.calls)


def test_main_profile_breaks_when_custom_running_stops(monkeypatch):
    from funcnodes.cli import main as main_mod

    class FakeStats:
        def __init__(self, yappi_ref):
            self._yappi = yappi_ref

        def save(self, filename, fmt):
            self._yappi.calls.append(("save", filename, fmt))

    class FakeYappi:
        def __init__(self):
            self.custom_running = False
            self.calls = []

        def set_clock_type(self, clock):
            self.calls.append(("clock", clock))

        def start(self):
            self.calls.append(("start", True))

        def stop(self):
            self.calls.append(("stop", True))

        def get_func_stats(self):
            return FakeStats(self)

    class FakeThread:
        def __init__(self, target=None, args=(), daemon=None):
            self._target = target
            self._args = args

        def start(self):
            self._target(*self._args)

    fake_yappi = FakeYappi()

    def fake_sleep(interval):
        fake_yappi.custom_running = False

    monkeypatch.setattr(main_mod, "yappi", fake_yappi)
    monkeypatch.setattr(main_mod.threading, "Thread", FakeThread)
    monkeypatch.setattr(main_mod, "_submain", lambda args: None)
    monkeypatch.setattr(main_mod.time, "sleep", fake_sleep)
    monkeypatch.setenv("USE_SUBPROCESS_MONITOR", "0")
    monkeypatch.setattr(sys, "argv", ["funcnodes", "--profile", "modules", "list"])

    main_mod.main()


def test_main_subprocess_monitor_success(monkeypatch):
    from funcnodes.cli import main as main_mod

    monitor_holder: dict = {}
    sleep_calls = {"count": 0}

    class FakeMonitor:
        def __init__(self, logger=None):
            self.logger = logger
            self.process_ownership = ["pid"]
            monitor_holder["instance"] = self

        async def run(self):
            return None

        def stop_serve(self):
            self.stopped = True

    async def fake_sleep(delay):
        sleep_calls["count"] += 1
        if sleep_calls["count"] == 3:
            monitor_holder["instance"].process_ownership.clear()
        return None

    async def fake_send_spawn_request(python, argv):
        return {"pid": 123}

    async def fake_subscribe(pid, callback):
        callback({"data": "hello"})
        return None

    fake_module = ModuleType("subprocess_monitor")
    fake_module.SubprocessMonitor = FakeMonitor
    fake_module.send_spawn_request = fake_send_spawn_request
    fake_module.subscribe = fake_subscribe

    monkeypatch.setattr(main_mod, "subprocess_monitor", fake_module)
    monkeypatch.setattr(main_mod.asyncio, "sleep", fake_sleep)
    monkeypatch.setenv("USE_SUBPROCESS_MONITOR", "1")
    monkeypatch.delenv("SUBPROCESS_MONITOR_PID", raising=False)
    monkeypatch.setattr(sys, "argv", ["funcnodes", "runserver"])

    main_mod.main()


def test_main_subprocess_monitor_keyboard_interrupt(monkeypatch):
    from funcnodes.cli import main as main_mod

    monitor_holder: dict = {}

    class FakeMonitor:
        def __init__(self, logger=None):
            self.logger = logger
            self.process_ownership = ["pid"]
            self.stopped = False
            monitor_holder["instance"] = self

        async def run(self):
            return None

        def stop_serve(self):
            self.stopped = True

    async def fake_sleep(delay):
        return None

    async def fake_send_spawn_request(python, argv):
        raise KeyboardInterrupt()

    async def fake_subscribe(pid, callback):
        return None

    fake_module = ModuleType("subprocess_monitor")
    fake_module.SubprocessMonitor = FakeMonitor
    fake_module.send_spawn_request = fake_send_spawn_request
    fake_module.subscribe = fake_subscribe

    monkeypatch.setattr(main_mod, "subprocess_monitor", fake_module)
    monkeypatch.setattr(main_mod.asyncio, "sleep", fake_sleep)
    monkeypatch.setenv("USE_SUBPROCESS_MONITOR", "1")
    monkeypatch.delenv("SUBPROCESS_MONITOR_PID", raising=False)
    monkeypatch.setattr(sys, "argv", ["funcnodes", "runserver"])

    main_mod.main()

    assert monitor_holder["instance"].stopped is True


def test_main_subprocess_monitor_missing_pid_raises(monkeypatch):
    from funcnodes.cli import main as main_mod

    class FakeMonitor:
        def __init__(self, logger=None):
            self.logger = logger
            self.process_ownership = []

        async def run(self):
            return None

        def stop_serve(self):
            return None

    async def fake_sleep(delay):
        return None

    async def fake_send_spawn_request(python, argv):
        return {}

    async def fake_subscribe(pid, callback):
        return None

    fake_module = ModuleType("subprocess_monitor")
    fake_module.SubprocessMonitor = FakeMonitor
    fake_module.send_spawn_request = fake_send_spawn_request
    fake_module.subscribe = fake_subscribe

    monkeypatch.setattr(main_mod, "subprocess_monitor", fake_module)
    monkeypatch.setattr(main_mod.asyncio, "sleep", fake_sleep)
    monkeypatch.setenv("USE_SUBPROCESS_MONITOR", "1")
    monkeypatch.delenv("SUBPROCESS_MONITOR_PID", raising=False)
    monkeypatch.setattr(sys, "argv", ["funcnodes", "runserver"])

    with pytest.raises(Exception, match="Subprocess failed"):
        main_mod.main()


def test_main_module_guard_executes(monkeypatch):
    plugin_module = ModuleType("funcnodes_core.utils.plugins")
    plugin_module.get_installed_modules = lambda: {}
    monkeypatch.setitem(sys.modules, "funcnodes_core.utils.plugins", plugin_module)
    monkeypatch.setenv("USE_SUBPROCESS_MONITOR", "0")
    monkeypatch.setattr(sys, "argv", ["funcnodes", "modules", "list"])

    runpy.run_module("funcnodes.__main__", run_name="__main__")
