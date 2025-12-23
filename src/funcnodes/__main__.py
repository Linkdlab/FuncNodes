"""
FuncNodes CLI Entry Point

This module re-exports the public CLI helpers and keeps the entrypoint thin.
"""

import funcnodes as fn

from funcnodes.cli.main import (
    _run_via_subprocess_monitor,
    _run_with_profiling,
    _submain,
    main,
)
from funcnodes.cli.interactive import run_interactive_cli
from funcnodes.cli.parser import (
    _add_worker_identifiers,
    _setup_argument_parser,
    add_cli_parser,
    add_modules_parser,
    add_runserver_parser,
    add_standalone_parser,
    add_worker_manager_parser,
    add_worker_parser,
    validate_standalone_args,
)
from funcnodes.cli.runtime import subprocess, subprocess_monitor, venvmngr
from funcnodes.cli.tasks import (
    start_worker_manager,
    task_modules,
    task_run_server,
    task_standalone,
    task_worker,
)
from funcnodes.cli.utils import _parse_command_value, parse_command_kwargs
from funcnodes.cli.worker import (
    _get_worker_conf,
    _worker_conf_from_args,
    activate_worker_env,
    call_worker_command,
    get_worker_venv,
    listen_worker,
    list_workers,
    py_in_worker_env,
    start_existing_worker,
    start_new_worker,
    stop_worker,
    worker_command_task,
    worker_modules_task,
)

__all__ = [
    "_add_worker_identifiers",
    "_get_worker_conf",
    "_run_via_subprocess_monitor",
    "_run_with_profiling",
    "_setup_argument_parser",
    "_submain",
    "_worker_conf_from_args",
    "_parse_command_value",
    "activate_worker_env",
    "add_cli_parser",
    "add_modules_parser",
    "add_runserver_parser",
    "add_standalone_parser",
    "add_worker_manager_parser",
    "add_worker_parser",
    "call_worker_command",
    "get_worker_venv",
    "listen_worker",
    "list_workers",
    "main",
    "parse_command_kwargs",
    "py_in_worker_env",
    "run_interactive_cli",
    "start_existing_worker",
    "start_new_worker",
    "start_worker_manager",
    "stop_worker",
    "subprocess",
    "subprocess_monitor",
    "task_modules",
    "task_run_server",
    "task_standalone",
    "task_worker",
    "validate_standalone_args",
    "venvmngr",
    "worker_command_task",
    "worker_modules_task",
    "fn",
]


if __name__ == "__main__":
    main()
