from collections.abc import Callable
from concurrent.futures import Future
import argparse
import asyncio
import textwrap
import threading
from typing import Optional

from pathlib import Path

import funcnodes as fn

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


def task_run_server(args: argparse.Namespace):
    """Run the FuncNodes server with the specified frontend."""
    frontend = args.frontend
    if frontend == "react_flow":
        from funcnodes_react_flow import run_server
    else:
        raise Exception(f"Unknown frontend: {frontend}")

    run_server(
        port=args.port,
        host=args.host,
        open_browser=args.no_browser,
        worker_manager_host=args.worker_manager_host,
        worker_manager_port=args.worker_manager_port,
        worker_manager_ssl=args.worker_manager_ssl,
        start_worker_manager=args.no_manager,
        has_worker_manager=args.no_manager,
        worker_host=args.worker_host,
        worker_port=args.worker_port,
        worker_ssl=args.worker_ssl,
        debug=args.debug,
    )


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
