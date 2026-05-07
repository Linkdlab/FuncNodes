import argparse
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import pytest_funcnodes  # noqa: F401

pytestmark = pytest.mark.cli


@pytest.fixture()
def worker_config() -> dict:
    assert pytest_funcnodes.get_in_test(), "Not in test mode"
    from funcnodes.worker.worker_manager import WorkerManager

    assert pytest_funcnodes.get_in_test(), "Not in test mode"

    manager = WorkerManager(debug=False)
    worker_dir = Path(manager.worker_dir)
    worker_dir.mkdir(parents=True, exist_ok=True)

    cfg = {
        "uuid": "worker-123",
        "name": "primary",
        "type": "WSWorker",
        "env_path": None,
    }
    worker_file = worker_dir / f"worker_{cfg['uuid']}.json"
    worker_file.write_text(json.dumps(cfg), encoding="utf-8")
    return cfg


@pytest_funcnodes.funcnodes_test
def test_task_run_server_calls_react_flow(monkeypatch):
    from funcnodes.__main__ import task_run_server

    captured: dict = {}
    module = ModuleType("funcnodes_react_flow")

    def run_server(**kwargs):
        captured.update(kwargs)

    module.run_server = run_server
    monkeypatch.setitem(sys.modules, "funcnodes_react_flow", module)

    args = SimpleNamespace(
        frontend="react_flow",
        port=9001,
        host="127.0.0.1",
        no_browser=False,
        worker_manager_host="manager.local",
        worker_manager_port=9100,
        worker_manager_ssl=True,
        no_manager=False,
        worker_host="worker.local",
        worker_port=9200,
        worker_ssl=True,
        debug=True,
    )

    task_run_server(args)

    assert captured["port"] == 9001
    assert captured["host"] == "127.0.0.1"
    assert captured["open_browser"] is False
    assert captured["worker_manager_host"] == "manager.local"
    assert captured["worker_manager_port"] == 9100
    assert captured["worker_manager_ssl"] is True
    assert captured["start_worker_manager"] is False
    assert captured["has_worker_manager"] is False
    assert captured["worker_host"] == "worker.local"
    assert captured["worker_port"] == 9200
    assert captured["worker_ssl"] is True
    assert captured["debug"] is True


@pytest_funcnodes.funcnodes_test
def test_task_run_server_attaches_to_running_worker(monkeypatch, worker_config):
    from funcnodes.__main__ import task_run_server
    from funcnodes.worker import worker_manager as worker_manager_mod

    worker_config["host"] = "existing.local"
    worker_config["port"] = 9399
    worker_dir = Path(worker_manager_mod.WorkerManager(debug=False).worker_dir)
    worker_file = worker_dir / f"worker_{worker_config['uuid']}.json"
    worker_file.write_text(json.dumps(worker_config), encoding="utf-8")

    captured: dict = {}
    module = ModuleType("funcnodes_react_flow")

    def run_server(**kwargs):
        captured.update(kwargs)

    async def fake_check_worker(config):
        return config["uuid"], True

    def fail_start_worker(config, debug=False):  # pragma: no cover - assertion guard
        raise AssertionError("running worker must not be started")

    async def fail_stop_worker(self, workerid, websocket=None):
        raise AssertionError("attached worker must not be stopped")

    module.run_server = run_server
    monkeypatch.setitem(sys.modules, "funcnodes_react_flow", module)
    monkeypatch.setattr(worker_manager_mod, "check_worker", fake_check_worker)
    monkeypatch.setattr(worker_manager_mod, "start_worker", fail_start_worker)
    monkeypatch.setattr(
        worker_manager_mod.WorkerManager,
        "stop_worker",
        fail_stop_worker,
    )

    args = SimpleNamespace(
        frontend="react_flow",
        port=9001,
        host="127.0.0.1",
        no_browser=False,
        worker_manager_host=None,
        worker_manager_port=None,
        worker_manager_ssl=False,
        no_manager=False,
        worker_host="localhost",
        worker_port=9200,
        worker_ssl=False,
        worker_uuid=worker_config["uuid"],
        debug=True,
    )

    task_run_server(args)

    assert captured["has_worker_manager"] is False
    assert captured["start_worker_manager"] is False
    assert captured["worker_host"] == "existing.local"
    assert captured["worker_port"] == 9399


@pytest_funcnodes.funcnodes_test
def test_task_run_server_starts_and_stops_stopped_worker(monkeypatch, worker_config):
    from funcnodes.__main__ import task_run_server
    from funcnodes.worker import worker_manager as worker_manager_mod

    captured: dict = {}
    started: list[dict] = []
    stopped: list[str] = []
    module = ModuleType("funcnodes_react_flow")

    def run_server(**kwargs):
        captured.update(kwargs)

    async def fake_check_worker(config):
        return config["uuid"], bool(started)

    def fake_start_worker(config, debug=False):
        started.append(dict(config))

    async def fake_stop_worker(self, workerid, websocket=None):
        stopped.append(workerid)

    module.run_server = run_server
    monkeypatch.setitem(sys.modules, "funcnodes_react_flow", module)
    monkeypatch.setattr(worker_manager_mod, "check_worker", fake_check_worker)
    monkeypatch.setattr(worker_manager_mod, "start_worker", fake_start_worker)
    monkeypatch.setattr(
        worker_manager_mod.WorkerManager,
        "stop_worker",
        fake_stop_worker,
    )

    args = SimpleNamespace(
        frontend="react_flow",
        port=9001,
        host="127.0.0.1",
        no_browser=False,
        worker_manager_host=None,
        worker_manager_port=None,
        worker_manager_ssl=False,
        no_manager=False,
        worker_host="requested.local",
        worker_port=9200,
        worker_ssl=True,
        worker_uuid=worker_config["uuid"],
        debug=True,
    )

    task_run_server(args)

    assert started[0]["host"] == "requested.local"
    assert started[0]["port"] == 9200
    assert "register_shutdown_handler" in captured
    assert captured["worker_host"] == "requested.local"
    assert captured["worker_port"] == 9200
    assert captured["worker_ssl"] is True
    assert stopped == [worker_config["uuid"]]


@pytest_funcnodes.funcnodes_test
def test_task_run_server_preserves_worker_bind_host_for_public_host_override(
    monkeypatch, worker_config
):
    from funcnodes.__main__ import task_run_server
    from funcnodes.worker import worker_manager as worker_manager_mod

    worker_config["host"] = "0.0.0.0"
    worker_dir = Path(worker_manager_mod.WorkerManager(debug=False).worker_dir)
    worker_file = worker_dir / f"worker_{worker_config['uuid']}.json"
    worker_file.write_text(json.dumps(worker_config), encoding="utf-8")

    captured: dict = {}
    started: list[dict] = []
    stopped: list[str] = []
    module = ModuleType("funcnodes_react_flow")

    def run_server(**kwargs):
        captured.update(kwargs)

    async def fake_check_worker(config):
        return config["uuid"], bool(started)

    def fake_start_worker(config, debug=False):
        started.append(dict(config))

    async def fake_stop_worker(self, workerid, websocket=None):
        stopped.append(workerid)

    module.run_server = run_server
    monkeypatch.setitem(sys.modules, "funcnodes_react_flow", module)
    monkeypatch.setattr(worker_manager_mod, "check_worker", fake_check_worker)
    monkeypatch.setattr(worker_manager_mod, "start_worker", fake_start_worker)
    monkeypatch.setattr(
        worker_manager_mod.WorkerManager,
        "stop_worker",
        fake_stop_worker,
    )

    args = SimpleNamespace(
        frontend="react_flow",
        port=9001,
        host="127.0.0.1",
        no_browser=False,
        worker_manager_host=None,
        worker_manager_port=None,
        worker_manager_ssl=False,
        no_manager=False,
        worker_host="worker.example.com",
        worker_port=9200,
        worker_ssl=False,
        worker_uuid=worker_config["uuid"],
        debug=True,
    )

    task_run_server(args)

    assert started[0]["host"] == "0.0.0.0"
    assert captured["worker_host"] == "worker.example.com"
    assert stopped == [worker_config["uuid"]]


@pytest_funcnodes.funcnodes_test
def test_task_run_server_stops_worker_when_startup_check_fails(
    monkeypatch, worker_config
):
    from funcnodes.cli import tasks as tasks_mod
    from funcnodes.worker import worker_manager as worker_manager_mod

    started: list[dict] = []
    stopped: list[str] = []

    async def fake_check_worker(config):
        return config["uuid"], False

    def fake_start_worker(config, debug=False):
        started.append(dict(config))

    async def fake_stop_worker(self, workerid, websocket=None):
        stopped.append(workerid)

    ticks = iter([0, 31])

    monkeypatch.setattr(worker_manager_mod, "check_worker", fake_check_worker)
    monkeypatch.setattr(worker_manager_mod, "start_worker", fake_start_worker)
    monkeypatch.setattr(
        worker_manager_mod.WorkerManager,
        "stop_worker",
        fake_stop_worker,
    )
    monkeypatch.setattr(tasks_mod.time, "time", lambda: next(ticks))
    monkeypatch.setattr(tasks_mod.time, "sleep", lambda delay: None)

    args = SimpleNamespace(
        frontend="react_flow",
        no_manager=False,
        worker_host="localhost",
        worker_port=9200,
        worker_ssl=False,
        worker_uuid=worker_config["uuid"],
        debug=True,
    )

    with pytest.raises(TimeoutError, match="did not become reachable"):
        tasks_mod.task_run_server(args)

    assert started
    assert stopped == [worker_config["uuid"]]


@pytest_funcnodes.funcnodes_test
def test_task_run_server_worker_uuid_requires_no_manager(worker_config):
    from funcnodes.__main__ import task_run_server

    args = SimpleNamespace(
        frontend="react_flow",
        no_manager=True,
        worker_uuid=worker_config["uuid"],
    )

    with pytest.raises(ValueError, match="--worker-uuid requires --no-manager"):
        task_run_server(args)


@pytest_funcnodes.funcnodes_test
def test_task_run_server_unknown_worker_uuid_raises():
    from funcnodes.__main__ import task_run_server

    args = SimpleNamespace(
        frontend="react_flow",
        no_manager=False,
        worker_uuid="missing-worker",
        debug=False,
    )

    with pytest.raises(ValueError, match="No worker found"):
        task_run_server(args)


@pytest_funcnodes.funcnodes_test
def test_task_run_server_rejects_unknown_frontend():
    from funcnodes.__main__ import task_run_server

    args = SimpleNamespace(frontend="unknown")
    with pytest.raises(Exception, match="Unknown frontend"):
        task_run_server(args)


@pytest_funcnodes.funcnodes_test
def test_add_runserver_parser_parses_flags():
    from funcnodes.__main__ import add_runserver_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_runserver_parser(subparsers)

    args = parser.parse_args(
        [
            "runserver",
            "--host",
            "0.0.0.0",
            "--port",
            "9002",
            "--no-browser",
            "--no-manager",
            "--worker_manager_host",
            "manager",
            "--worker_manager_port",
            "9101",
            "--worker_manager_ssl",
            "--worker_host",
            "worker",
            "--worker_port",
            "9201",
            "--worker-uuid",
            "worker-123",
            "--worker_ssl",
        ]
    )

    assert args.task == "runserver"
    assert args.host == "0.0.0.0"
    assert args.port == 9002
    assert args.no_browser is False
    assert args.no_manager is False
    assert args.worker_manager_host == "manager"
    assert args.worker_manager_port == 9101
    assert args.worker_manager_ssl is True
    assert args.worker_host == "worker"
    assert args.worker_port == 9201
    assert args.worker_uuid == "worker-123"
    assert args.worker_ssl is True


@pytest_funcnodes.funcnodes_test
def test_validate_standalone_args_register_sets_long_running_false():
    from funcnodes.__main__ import add_standalone_parser, validate_standalone_args

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_standalone_parser(subparsers)

    args = parser.parse_args(["standalone", "--register"])
    assert args.long_running is True

    validate_standalone_args(parser, args)
    assert args.long_running is False


@pytest_funcnodes.funcnodes_test
def test_parse_command_kwargs_supports_equals_and_double_dash():
    from funcnodes.__main__ import parse_command_kwargs

    kwargs = parse_command_kwargs(["--count=3", "--", "--flag", "true"])
    assert kwargs == {"count": 3, "flag": True}


@pytest_funcnodes.funcnodes_test
def test_list_workers_prints_uuid_and_name(worker_config, capsys):
    from funcnodes.__main__ import list_workers

    args = SimpleNamespace(debug=False, full=False)
    list_workers(args)

    captured = capsys.readouterr().out
    assert worker_config["uuid"] in captured
    assert worker_config["name"] in captured


@pytest_funcnodes.funcnodes_test
def test_list_workers_full_prints_config(worker_config, capsys):
    from funcnodes.__main__ import list_workers

    args = SimpleNamespace(debug=False, full=True)
    list_workers(args)

    captured = capsys.readouterr().out
    assert worker_config["uuid"] in captured
    assert worker_config["name"] in captured


@pytest_funcnodes.funcnodes_test
def test_task_worker_list_dispatches(worker_config, capsys):
    from funcnodes.__main__ import task_worker

    args = SimpleNamespace(
        workertask="list",
        debug=False,
        full=False,
        uuid=None,
        name=None,
        workertype="WSWorker",
    )
    task_worker(args)

    captured = capsys.readouterr().out
    assert worker_config["uuid"] in captured


@pytest_funcnodes.funcnodes_test
def test_task_worker_raises_on_unknown_task():
    from funcnodes.__main__ import task_worker

    args = SimpleNamespace(
        workertask="unknown",
        debug=False,
        full=False,
        uuid=None,
        name=None,
        workertype="WSWorker",
    )

    with pytest.raises(Exception, match="Unknown workertask"):
        task_worker(args)


@pytest_funcnodes.funcnodes_test
def test_task_modules_list_uses_plugin_registry(monkeypatch, capsys):
    from funcnodes.__main__ import task_modules
    from funcnodes_core.utils import plugins

    monkeypatch.setattr(plugins, "get_installed_modules", lambda: {"demo": {"v": 1}})

    args = SimpleNamespace(moduletask="list")
    task_modules(args)

    captured = capsys.readouterr().out
    assert "demo" in captured


@pytest_funcnodes.funcnodes_test
def test_task_modules_raises_on_unknown_task():
    from funcnodes.__main__ import task_modules

    args = SimpleNamespace(moduletask="unknown")
    with pytest.raises(Exception, match="Unknown moduletask"):
        task_modules(args)


@pytest_funcnodes.funcnodes_test
def test_add_worker_manager_parser_parses_args():
    from funcnodes.__main__ import add_worker_manager_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_worker_manager_parser(subparsers)

    args = parser.parse_args(
        ["startworkermanager", "--host", "127.0.0.1", "--port", "9102"]
    )

    assert args.task == "startworkermanager"
    assert args.host == "127.0.0.1"
    assert args.port == 9102
    assert args.long_running is True


@pytest_funcnodes.funcnodes_test
def test_add_worker_parser_parses_new_autostart_flag():
    from funcnodes.__main__ import add_worker_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_worker_parser(subparsers)

    args = parser.parse_args(["worker", "new", "--autostart"])

    assert args.task == "worker"
    assert args.workertask == "new"
    assert args.autostart_policy == "unless-stopped"


@pytest_funcnodes.funcnodes_test
def test_add_worker_parser_parses_new_autostart_policy():
    from funcnodes.__main__ import add_worker_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_worker_parser(subparsers)

    args = parser.parse_args(["worker", "new", "--autostart-policy", "always"])

    assert args.task == "worker"
    assert args.workertask == "new"
    assert args.autostart_policy == "always"


@pytest_funcnodes.funcnodes_test
def test_add_worker_parser_parses_new_worker_host_and_port():
    from funcnodes.__main__ import add_worker_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_worker_parser(subparsers)

    args = parser.parse_args(
        [
            "worker",
            "--uuid",
            "worker-docker",
            "--name",
            "docker",
            "new",
            "--host",
            "0.0.0.0",
            "--port",
            "9382",
        ]
    )

    assert args.task == "worker"
    assert args.workertask == "new"
    assert args.uuid == "worker-docker"
    assert args.name == "docker"
    assert args.host == "0.0.0.0"
    assert args.port == 9382


@pytest_funcnodes.funcnodes_test
def test_task_worker_new_passes_host_and_port(monkeypatch):
    from funcnodes.cli import tasks as tasks_mod
    from funcnodes.__main__ import task_worker

    captured: dict = {}

    def fake_start_new_worker(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(tasks_mod, "start_new_worker", fake_start_new_worker)

    args = SimpleNamespace(
        workertask="new",
        uuid="worker-docker",
        name="docker",
        workertype="WSWorker",
        debug=False,
        in_venv=False,
        create_only=True,
        profile=False,
        autostart_policy="never",
        host="0.0.0.0",
        port=9382,
    )

    task_worker(args)

    assert captured["uuid"] == "worker-docker"
    assert captured["name"] == "docker"
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9382
    assert captured["in_venv"] is False
    assert captured["create_only"] is True


@pytest_funcnodes.funcnodes_test
def test_add_worker_parser_rejects_autostart_flag_and_policy_together():
    from funcnodes.__main__ import add_worker_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_worker_parser(subparsers)

    with pytest.raises(SystemExit):
        parser.parse_args(
            ["worker", "new", "--autostart", "--autostart-policy", "always"]
        )


@pytest_funcnodes.funcnodes_test
def test_add_modules_parser_parses_args():
    from funcnodes.__main__ import add_modules_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_modules_parser(subparsers)

    args = parser.parse_args(["modules", "list"])
    assert args.task == "modules"
    assert args.moduletask == "list"


@pytest_funcnodes.funcnodes_test
def test_activate_worker_env_raises_when_env_missing(worker_config):
    from funcnodes.__main__ import activate_worker_env

    args = SimpleNamespace(
        uuid=worker_config["uuid"],
        name=None,
        workertype="WSWorker",
        debug=False,
    )

    with pytest.raises(Exception, match="does not have an environment"):
        activate_worker_env(args)


@pytest_funcnodes.funcnodes_test
def test_py_in_worker_env_invokes_subprocess(monkeypatch, worker_config):
    from funcnodes import __main__ as main_mod
    from funcnodes.__main__ import py_in_worker_env

    called: dict = {}

    def fake_run(cmd):
        called["cmd"] = cmd

    monkeypatch.setattr(main_mod.subprocess, "run", fake_run)

    args = SimpleNamespace(
        uuid=worker_config["uuid"],
        name=None,
        workertype="WSWorker",
        debug=False,
        command=["--", "-c", "print('ok')"],
    )
    py_in_worker_env(args)

    assert called["cmd"][0] == sys.executable
    assert called["cmd"][1:] == ["-c", "print('ok')"]


@pytest_funcnodes.funcnodes_test
def test_worker_modules_task_invokes_subprocess(monkeypatch, worker_config):
    from funcnodes import __main__ as main_mod
    from funcnodes.__main__ import worker_modules_task

    called: dict = {}

    def fake_run(cmd):
        called["cmd"] = cmd

    monkeypatch.setattr(main_mod.subprocess, "run", fake_run)

    args = SimpleNamespace(
        uuid=worker_config["uuid"],
        name=None,
        workertype="WSWorker",
        debug=False,
        moduletask="list",
    )
    worker_modules_task(args)

    assert called["cmd"][0] == sys.executable
    assert called["cmd"][1:] == ["-m", "funcnodes", "modules", "list"]


@pytest_funcnodes.funcnodes_test
def test_get_worker_conf_by_uuid(worker_config):
    from funcnodes.__main__ import _get_worker_conf

    cfg = _get_worker_conf(
        uuid=worker_config["uuid"],
        name=None,
        workertype="WSWorker",
        debug=False,
    )

    assert cfg["uuid"] == worker_config["uuid"]
    assert cfg["name"] == worker_config["name"]


@pytest_funcnodes.funcnodes_test
def test_get_worker_conf_by_name(worker_config):
    from funcnodes.__main__ import _get_worker_conf

    cfg = _get_worker_conf(
        uuid=None,
        name=worker_config["name"],
        workertype="WSWorker",
        debug=False,
    )

    assert cfg["uuid"] == worker_config["uuid"]


@pytest_funcnodes.funcnodes_test
def test_get_worker_conf_requires_identifier():
    from funcnodes.__main__ import _get_worker_conf

    with pytest.raises(Exception, match="uuid or name is required"):
        _get_worker_conf(uuid=None, name=None, workertype="WSWorker", debug=False)


@pytest_funcnodes.funcnodes_test
def test_get_worker_conf_raises_for_missing_uuid(worker_config):
    from funcnodes.__main__ import _get_worker_conf

    with pytest.raises(Exception, match="No worker found with the given uuid"):
        _get_worker_conf(uuid="missing", name=None, workertype="WSWorker", debug=False)


@pytest_funcnodes.funcnodes_test
def test_get_worker_conf_raises_for_missing_name(worker_config):
    from funcnodes.__main__ import _get_worker_conf

    with pytest.raises(Exception, match="No worker found with the given uuid or name"):
        _get_worker_conf(uuid=None, name="missing", workertype="WSWorker", debug=False)


@pytest_funcnodes.funcnodes_test
def test_get_worker_conf_raises_on_name_mismatch(worker_config):
    from funcnodes.__main__ import _get_worker_conf

    with pytest.raises(Exception, match="different name"):
        _get_worker_conf(
            uuid=worker_config["uuid"],
            name="other",
            workertype="WSWorker",
            debug=False,
        )


@pytest_funcnodes.funcnodes_test
def test_worker_conf_from_args_returns_config(worker_config):
    from funcnodes.__main__ import _worker_conf_from_args

    args = SimpleNamespace(
        uuid=worker_config["uuid"],
        name=None,
        workertype="WSWorker",
        debug=False,
    )
    cfg = _worker_conf_from_args(args)

    assert cfg["uuid"] == worker_config["uuid"]


@pytest_funcnodes.funcnodes_test
def test_get_worker_venv_returns_none_when_env_missing(worker_config):
    from funcnodes.__main__ import get_worker_venv

    cfg = dict(worker_config)
    cfg["env_path"] = None
    assert get_worker_venv(cfg) is None
