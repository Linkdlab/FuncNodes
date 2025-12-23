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
