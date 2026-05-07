from collections.abc import Callable
from concurrent.futures import Future
import argparse
import asyncio
import textwrap
import threading
import time
from typing import Optional

from pathlib import Path

import funcnodes as fn
from funcnodes_core.utils.files import write_json_secure

from .utils import parse_command_kwargs
from .worker import (
    activate_worker_env,
    listen_worker,
    list_workers,
    py_in_worker_env,
    start_existing_worker,
    start_new_worker,
    stop_worker,
    worker_command_task,
    worker_modules_task,
)


# =============================================================================
# Task Handlers
# =============================================================================


def _get_runserver_worker_config(worker_uuid: str, debug: bool):
    """Return the manager and worker config for a direct runserver worker."""
    manager = fn.worker.worker_manager.WorkerManager(debug=debug)
    for worker_config in manager.get_all_workercfg():
        if worker_config["uuid"] == worker_uuid:
            return manager, worker_config

    raise ValueError(f"No worker found with uuid {worker_uuid!r}")


def _write_runserver_worker_config(manager, worker_config):
    """Persist direct worker host/port changes before starting the worker."""
    worker_config_file = (
        Path(manager.worker_dir) / f"worker_{worker_config['uuid']}.json"
    )
    write_json_secure(worker_config, worker_config_file, indent=2)


def _check_runserver_worker(worker_config) -> bool:
    """Check whether the configured worker websocket is reachable."""
    _, is_running = asyncio.run(fn.worker.worker_manager.check_worker(worker_config))
    return is_running


def _wait_for_runserver_worker(worker_uuid: str, debug: bool, timeout: float = 30.0):
    """Wait for a worker started by runserver to publish a reachable endpoint."""
    deadline = time.time() + timeout

    while time.time() < deadline:
        _, worker_config = _get_runserver_worker_config(worker_uuid, debug=debug)
        if _check_runserver_worker(worker_config):
            return worker_config
        time.sleep(0.5)

    raise TimeoutError(f"Worker {worker_uuid!r} did not become reachable")


def _stop_runserver_worker(worker_uuid: str, debug: bool):
    """Stop a worker that was started for a direct runserver session."""
    manager = fn.worker.worker_manager.WorkerManager(debug=debug)
    asyncio.run(manager.stop_worker(worker_uuid))


def _prepare_direct_worker_for_runserver(args: argparse.Namespace):
    """Attach to or start the worker requested by runserver --worker-uuid."""
    worker_uuid = getattr(args, "worker_uuid", None)
    if not worker_uuid:
        return None, False

    if getattr(args, "no_manager", True):
        raise ValueError("--worker-uuid requires --no-manager")

    debug = getattr(args, "debug", False)
    manager, worker_config = _get_runserver_worker_config(worker_uuid, debug=debug)

    if _check_runserver_worker(worker_config):
        return worker_config, False

    worker_config["host"] = (
        worker_config.get("host") or getattr(args, "worker_host", None) or "localhost"
    )
    worker_config["port"] = getattr(args, "worker_port", None) or worker_config.get(
        "port", 9380
    )
    worker_config["ssl"] = getattr(args, "worker_ssl", False)
    worker_config.pop("pid", None)
    _write_runserver_worker_config(manager, worker_config)

    fn.worker.worker_manager.start_worker(worker_config, debug=debug)
    try:
        worker_config = _wait_for_runserver_worker(worker_uuid, debug=debug)
    except Exception:
        _stop_runserver_worker(worker_uuid, debug=debug)
        raise
    return worker_config, True


def task_run_server(args: argparse.Namespace):
    """Run the FuncNodes server with the specified frontend."""
    frontend = args.frontend
    if frontend == "react_flow":
        from funcnodes_react_flow import run_server
    else:
        raise Exception(f"Unknown frontend: {frontend}")

    direct_worker_config, started_direct_worker = _prepare_direct_worker_for_runserver(
        args
    )

    worker_host = args.worker_host
    worker_port = args.worker_port
    worker_ssl = args.worker_ssl
    shutdown_handler_callback = None

    if direct_worker_config is not None:
        worker_host = direct_worker_config.get("host")
        worker_port = direct_worker_config.get("port")
        worker_ssl = direct_worker_config.get("ssl", False)
        if args.worker_host and args.worker_host != "localhost":
            worker_host = args.worker_host

        def _direct_worker_shutdown_handler(handler):
            return handler

        shutdown_handler_callback = _direct_worker_shutdown_handler

    try:
        run_server(
            port=args.port,
            host=args.host,
            open_browser=args.no_browser,
            worker_manager_host=args.worker_manager_host,
            worker_manager_port=args.worker_manager_port,
            worker_manager_ssl=args.worker_manager_ssl,
            start_worker_manager=args.no_manager,
            has_worker_manager=args.no_manager,
            worker_host=worker_host,
            worker_port=worker_port,
            worker_ssl=worker_ssl,
            debug=args.debug,
            register_shutdown_handler=shutdown_handler_callback,
        )
    finally:
        if started_direct_worker and direct_worker_config is not None:
            _stop_runserver_worker(direct_worker_config["uuid"], debug=args.debug)


def task_standalone(args: argparse.Namespace):
    """Run a standalone .fnw file with its own worker."""
    if getattr(args, "register", False):
        from funcnodes.runner.register import register_fnw

        register_fnw()
        return None

    from funcnodes.runner.standalone import StandaloneLauncher, pick_free_port

    fnw_path = Path(args.fnw_file).expanduser().resolve()
    if not fnw_path.exists():
        raise FileNotFoundError(f"File not found: {fnw_path}")

    config_dir = (
        Path(args.config_dir).expanduser().resolve() if args.config_dir else None
    )

    ui_port = args.ui_port if args.ui_port is not None else pick_free_port(args.host)

    server_shutdown_handler: Optional[Callable[[float], Future]] = None

    def _shutdown():
        fn.FUNCNODES_LOGGER.info("Shutting down standalone server")
        launcher.shutdown()
        if server_shutdown_handler:
            fn.FUNCNODES_LOGGER.debug("Shutting down server shutdown handler")
            server_shutdown_handler(0.5)
            fn.FUNCNODES_LOGGER.debug("Shutdown scheduled via run_coroutine_threadsafe")
        fn.FUNCNODES_LOGGER.debug("Standalone server shut down")

    launcher = StandaloneLauncher(
        fnw_path=fnw_path,
        config_dir=config_dir,
        host=args.host,
        ui_port=ui_port,
        worker_port=args.worker_port,
        open_browser=args.open_browser,
        debug=args.debug,
        on_worker_shutdown=_shutdown,
    )

    try:
        worker_port = launcher.ensure_worker(import_fnw=True)
        launcher_task = threading.Thread(target=launcher.run_forever)
        launcher_task.start()

        from funcnodes_react_flow import run_server

        def register_shutdown_handler(handler: Callable[[float], asyncio.Task]):
            nonlocal server_shutdown_handler
            server_shutdown_handler = handler

        run_server(
            port=ui_port,
            host=args.host,
            open_browser=args.open_browser,
            start_worker_manager=False,
            has_worker_manager=False,
            worker_host=args.host,
            worker_port=worker_port,
            worker_ssl=False,
            debug=args.debug,
            register_shutdown_handler=register_shutdown_handler,
        )
    except KeyboardInterrupt:
        _shutdown()
    finally:
        _shutdown()

    return None


def task_worker(args: argparse.Namespace):
    """Handle worker-related tasks."""
    workertask = args.workertask

    try:
        if workertask == "start":
            return start_existing_worker(
                uuid=args.uuid,
                name=args.name,
                workertype=args.workertype,
                debug=args.debug,
                profile=args.profile,
            )
        elif workertask == "stop":
            return stop_worker(
                uuid=args.uuid,
                name=args.name,
                workertype=args.workertype,
                debug=args.debug,
            )
        elif workertask == "new":
            return start_new_worker(
                uuid=args.uuid,
                name=args.name,
                workertype=args.workertype,
                debug=args.debug,
                in_venv=args.in_venv,
                create_only=args.create_only,
                profile=args.profile,
                autostart_policy=args.autostart_policy,
                host=getattr(args, "host", None),
                port=getattr(args, "port", None),
            )
        elif workertask == "list":
            return list_workers(args)
        elif workertask == "listen":
            return listen_worker(
                uuid=args.uuid,
                name=args.name,
                workertype=args.workertype,
                debug=args.debug,
            )
        elif workertask == "activate":
            return activate_worker_env(args)
        elif workertask == "py":
            return py_in_worker_env(args)
        elif workertask == "command":
            return worker_command_task(
                command=args.command,
                uuid=args.uuid,
                name=args.name,
                workertype=args.workertype,
                debug=args.debug,
                **parse_command_kwargs(getattr(args, "kwargs", None)),
            )
        elif workertask == "modules":
            return worker_modules_task(args)
        else:
            raise Exception(f"Unknown workertask: {workertask}")
    except Exception as exc:
        fn.FUNCNODES_LOGGER.exception(exc)
        raise


def task_modules(args: argparse.Namespace):
    """Handle module-related tasks."""
    if args.moduletask == "list":
        from funcnodes_core.utils import plugins

        for k, v in plugins.get_installed_modules().items():
            value_str = repr(v)
            indented_value = textwrap.indent(
                textwrap.fill(value_str, subsequent_indent="\t", width=80), "\t"
            )
            print(f"{k}:\n{indented_value}")
    else:
        raise Exception(f"Unknown moduletask: {args.moduletask}")


def start_worker_manager(args: argparse.Namespace):
    """Start the worker manager."""
    fn.worker.worker_manager.start_worker_manager(
        host=args.host, port=args.port, debug=args.debug
    )
