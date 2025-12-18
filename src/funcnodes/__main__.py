from collections.abc import Callable
from concurrent.futures import Future
import threading
from typing import Any, Optional, Type

import funcnodes as fn
import argparse
import json
from pprint import pprint
import textwrap
import sys
import os
import time
import shutil
from funcnodes.utils.cmd import build_worker_start
import asyncio
import dotenv
from funcnodes_worker.worker import WorkerJson, worker_json_get_data_path
from pathlib import Path

import warnings

if sys.platform != "emscripten":
    import venvmngr
    import subprocess_monitor
    import subprocess
else:
    venvmngr = None
    subprocess_monitor = None
    subprocess = None

try:
    # yappi is an optional dependency
    import yappi
except (ImportError, ModuleNotFoundError):
    yappi = None


dotenv.load_dotenv()


def task_run_server(args: argparse.Namespace):
    """
    Runs the server.

    Args:
      args (argparse.Namespace): The arguments passed to the function.

    Returns:
      None

    Examples:
      >>> task_run_server(args)
      None
    """
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
    if getattr(args, "register", False):
        from funcnodes.runner.register import register_fnw

        register_fnw()
        return

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
            # run_coroutine_threadsafe returns a concurrent.futures.Future
            # It's thread-safe and will execute in the event loop's thread
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


def list_workers(args: argparse.Namespace):
    """
    Lists all workers.

    Args:
      args (argparse.Namespace): The arguments passed to the function.

    Returns:
      None

    Examples:
      >>> list_workers(args)
      None
    """
    mng = fn.worker.worker_manager.WorkerManager(debug=args.debug)
    if args.full:
        pprint(mng.get_all_workercfg())
    else:
        for cf in mng.get_all_workercfg():
            print(f"{cf['uuid']}\t{cf.get('name')}")


def start_new_worker(
    uuid: Optional[str] = None,
    name: Optional[str] = None,
    workertype: Optional[str] = "WSWorker",
    debug: bool = False,
    in_venv: bool = True,
    create_only: bool = False,
    profile: bool = False,
    **kwargs,
):
    """
    Starts a new worker.

    Args:
      uuid: The uuid of the worker.
      name: The name of the worker.
      workertype: The type of the worker.
      debug: Whether to run the worker in debug mode.
      in_venv: Whether to run the worker in a virtual environment.
      create_only: Whether to create the worker only.
      profile: Whether to run the worker in profile mode.

    Returns:
      None

    Examples:
      >>> start_new_worker(uuid=worker124, in_venv=True, create_only=True)
      None
    """

    fn.FUNCNODES_LOGGER.info(
        f"Starting new worker with uuid: {uuid}, name: {name}, workertype: {workertype}, debug: {debug}"
    )

    mng = fn.worker.worker_manager.WorkerManager(debug=debug)

    new_worker_routine = mng.new_worker(
        name=name,
        uuid=uuid,
        workertype=workertype or "WSWorker",
        in_venv=in_venv,
        **kwargs,
    )
    import asyncio

    new_worker_config = asyncio.run(new_worker_routine)

    uuid = new_worker_config["uuid"]
    name = new_worker_config.get("name", None)
    if create_only:
        return
    return start_existing_worker(
        uuid=uuid, name=name, workertype=workertype, debug=debug, profile=profile
    )


def start_existing_worker(
    uuid: Optional[str] = None,
    name: Optional[str] = None,
    workertype: Optional[str] = "WSWorker",
    debug: bool = False,
    profile: bool = False,
):
    """
    Starts an existing worker.

    Args:
      uuid: The uuid of the worker.
      name: The name of the worker.
      workertype: The type of the worker.
      debug: Whether to run the worker in debug mode.
      profile: Whether to run the worker in profile mode.

    Returns:
      None

    Raises:
      Exception: If no worker is found with the given uuid or name.

    Examples:
      >>> start_existing_worker(uuid=uuid, name=name, workertype=workertype, debug=debug, profile=profile)
      None
    """

    cfg = _get_worker_conf(uuid=uuid, name=name, workertype=workertype, debug=debug)

    workerenv = get_worker_venv(cfg)
    pypath = str(workerenv.python_exe) if workerenv else sys.executable

    fn.FUNCNODES_LOGGER.info("Starting existing worker with pypath: %s", pypath)

    if workerenv:
        update_on_startup = cfg.get("update_on_startup", {})
        if update_on_startup.get("funcnodes", True):
            workerenv.install_package("funcnodes", upgrade=True)
        if update_on_startup.get("funcnodes-core", True):
            workerenv.install_package("funcnodes-core", upgrade=True)
        if update_on_startup.get("funcnodes-core", True):
            workerenv.install_package("funcnodes-worker", upgrade=True)

    if pypath != sys.executable:
        # run the worker with the same python executable
        if not os.path.exists(pypath):
            raise Exception(f"Python executable not found: {pypath}")

        kwargs = {}
        if debug:
            kwargs["debug"] = debug
        if profile:
            kwargs["profile"] = profile
        calllist = [
            pypath,
            "-m",
        ] + build_worker_start(uuid=cfg["uuid"], workertype=workertype, **kwargs)

        return subprocess.run(calllist)

    if workertype is None:
        workertype = cfg.get("type", "WSWorker")

    worker_class: Type[fn.worker.Worker] = getattr(fn.worker, workertype)
    fn.FUNCNODES_LOGGER.info("Starting existing worker of type %s", workertype)
    fn.logging.set_logging_dir(worker_json_get_data_path(cfg))
    worker = worker_class(uuid=cfg["uuid"], debug=debug)

    worker.run_forever()


def stop_worker(
    uuid: Optional[str] = None,
    name: Optional[str] = None,
    workertype: Optional[str] = "WSWorker",
    debug: bool = False,
):
    cfg = _get_worker_conf(uuid=uuid, name=name, workertype=workertype, debug=debug)
    mng = fn.worker.worker_manager.WorkerManager(debug=debug)
    asyncio.run(mng.stop_worker(cfg["uuid"]))


def _get_worker_conf(uuid: str, name: str, workertype: str, debug: bool) -> WorkerJson:
    if uuid is None:
        if name is None:
            raise Exception("uuid or name is required to start an existing worker")

    mng = fn.worker.worker_manager.WorkerManager(debug=debug)
    cfg = None
    if uuid:
        for cf in mng.get_all_workercfg():
            if cf["uuid"] == uuid:
                cfg = cf
                break

        if cfg is None:
            raise Exception("No worker found with the given uuid")

    if name:
        if cfg is None:
            for cf in mng.get_all_workercfg():
                if cf.get("name") == name:
                    cfg = cf
                    break
        else:
            if cfg.get("name") != name:
                raise Exception(
                    "Worker found with the given uuid but with a different name"
                )

    if cfg is None:
        raise Exception("No worker found with the given uuid or name")

    return cfg


def _worker_conf_from_args(args: argparse.Namespace) -> WorkerJson:
    """
    Returns the worker configuration from the arguments.

    Args:
      args (argparse.Namespace): The arguments passed to the function.

    Returns:
      dict: The worker configuration.

    Examples:
      >>> _worker_conf_from_args(args)
      {}
    """
    return _get_worker_conf(
        uuid=args.uuid, name=args.name, workertype=args.workertype, debug=args.debug
    )


def listen_worker(
    uuid: Optional[str] = None,
    name: Optional[str] = None,
    workertype: Optional[str] = "WSWorker",
    debug: bool = False,
    out=sys.stdout.write,
):
    """
    Listens to a running worker.

    Args:
      args (argparse.Namespace): The arguments passed to the function.

    Returns:
      None

    Raises:
      Exception: If no worker is found with the given uuid or name.

    Examples:
      >>> start_existing_worker(args)
      None
    """

    cfg = _get_worker_conf(
        uuid=uuid,
        name=name,
        workertype=workertype,
        debug=debug,
    )
    log_file_path = os.path.join(worker_json_get_data_path(cfg), "worker.log")
    # log file path
    while True:
        if os.path.exists(log_file_path):
            current_size = os.path.getsize(log_file_path)
            with open(log_file_path, "r") as log_file:
                # Read the entire file initially
                for line in log_file:
                    out(line)  # Print each line from the existing content

                # Move to the end of the file to begin tailing new content
                while True:
                    line = log_file.readline()
                    if line:
                        out(line)  # Print any new line added to the file
                    else:
                        time.sleep(
                            0.5
                        )  # Avoid high CPU usage when there's no new content

                        if not os.path.exists(  # Check if the file has been removed
                            log_file_path
                        ):
                            break
                        new_size = os.path.getsize(log_file_path)
                        if new_size < current_size:  # log file has been rotated
                            break
                        current_size = new_size

        time.sleep(5)  # Avoid high CPU usage when there's no new content


def _parse_command_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass

    lowered = value.lower()
    if lowered in ("true", "false"):
        return lowered == "true"

    if lowered in ("none", "null"):
        return None

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    return value


def parse_command_kwargs(argv: Optional[list[str]]) -> dict[str, Any]:
    if not argv:
        return {}

    kwargs: dict[str, Any] = {}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--":
            i += 1
            continue

        if not token.startswith("--") or token == "--":
            raise ValueError(f"Unexpected argument: {token}")

        key_with_value = token[2:]
        if not key_with_value:
            raise ValueError("Unexpected argument: --")

        if "=" in key_with_value:
            key, value = key_with_value.split("=", 1)
            kwargs[key] = _parse_command_value(value)
            i += 1
            continue

        key = key_with_value
        if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            kwargs[key] = _parse_command_value(argv[i + 1])
            i += 2
            continue

        kwargs[key] = True
        i += 1

    return kwargs


async def call_worker_command(
    worker_config: WorkerJson,
    command: str,
    kwargs: dict[str, Any],
    timeout: float = 30.0,
) -> Any:
    workertype = worker_config.get("type", "WSWorker")
    if workertype != "WSWorker":
        raise ValueError(
            f"Worker {worker_config.get('uuid')} is not a WebSocket worker but {workertype},"
            " command is only supported for WebSocket workers for now"
        )
    host = worker_config.get("host") or "localhost"
    port = worker_config.get("port")

    if not port:
        raise ValueError(f"Worker {worker_config.get('uuid')} has no port configured")

    connect_host = host if host not in ("0.0.0.0", "::", "") else "127.0.0.1"
    protocol = "wss" if worker_config.get("ssl", False) else "ws"
    url = f"{protocol}://{connect_host}:{port}"

    import aiohttp
    from aiohttp import WSMsgType

    timeout_cfg = aiohttp.ClientTimeout(total=timeout)

    async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
        async with session.ws_connect(url) as ws:
            message = {"type": "cmd", "cmd": command, "kwargs": kwargs}
            await ws.send_str(json.dumps(message))
            start_time = time.time()
            while time.time() - start_time < timeout:
                msg = await ws.receive()
                if msg.type != WSMsgType.TEXT:
                    continue

                try:
                    data = json.loads(msg.data)
                    msg_type = data.get("type")

                    if msg_type == "result":
                        return data.get("result")
                    if msg_type == "error":
                        raise RuntimeError(str(data.get("error") or "Unknown error"))
                except json.JSONDecodeError:
                    pass
                continue
            raise RuntimeError(
                f"Timeout waiting for result from worker {worker_config.get('uuid')}"
            )


def worker_command_task(
    command: str,
    uuid: Optional[str] = None,
    name: Optional[str] = None,
    workertype: Optional[str] = "WSWorker",
    debug: bool = False,
    **kwargs,
):
    cfg = _get_worker_conf(uuid=uuid, name=name, workertype=workertype, debug=debug)

    result = asyncio.run(
        call_worker_command(
            worker_config=cfg,
            command=command,
            kwargs=kwargs,
        )
    )

    if isinstance(result, (dict, list)):
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(result)


def task_worker(args: argparse.Namespace):
    """
    Performs a task on worker(s).

    Args:
      args (argparse.Namespace): The arguments passed to the function.

    Returns:
      None

    Raises:
      Exception: If the workertask is unknown.

    Examples:
      >>> task_worker(args)
      None
    """

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


def start_worker_manager(args: argparse.Namespace):
    """
    Starts the worker manager.

    Args:
      args (argparse.Namespace): The arguments passed to the function.

    Returns:
      None

    Examples:
      >>> start_worker_manager(args)
      None
    """

    fn.worker.worker_manager.start_worker_manager(
        host=args.host, port=args.port, debug=args.debug
    )


def get_worker_venv(cfg: WorkerJson) -> Optional[venvmngr.UVVenvManager]:
    if cfg["env_path"] and venvmngr:
        workerenv = venvmngr.UVVenvManager.get_virtual_env(cfg["env_path"])
        return workerenv
    return None


def activate_worker_env(args: argparse.Namespace):
    """
    Activates the funcnodes environment.

    Returns:
      None

    Examples:
      >>> activate_fn_env()
      None
    """

    if not subprocess:
        raise Exception(
            "This command is only available on system with subprocess support"
        )

    cfg = _worker_conf_from_args(args)

    venv = cfg["env_path"]

    if venv is None:
        raise Exception("This worker does not have an environment")

    if not os.path.exists(venv):
        raise Exception(f"Environment not found: {venv}")

    # Construct the command to open a new shell with the environment activated
    if sys.platform == "win32":
        # For Windows
        venv_activate_script = os.path.join(venv, "Scripts", "activate.bat")
        shell_command = [
            venv_activate_script,
            "&&",
            "cmd /k",
        ]
        executable = None
    else:
        # For Unix-based systems (Linux, macOS)
        venv_activate_script = os.path.join(venv, "bin", "activate")
        shell_command = f"source {venv_activate_script} && exec $SHELL"
        executable = shutil.which("bash") or shutil.which("sh")
    # Run the shell command
    subprocess.run(
        shell_command,
        shell=True,
        executable=executable,
    )


def py_in_worker_env(args: argparse.Namespace):
    """
    Runs python in the worker environment.

    Args:
      args (argparse.Namespace): The arguments passed to the function.

    Returns:
      None

    Examples:
      >>> py_in_worker_env(args)
      None
    """
    cfg = _worker_conf_from_args(args)
    workerenv = get_worker_venv(cfg)
    pypath = str(workerenv.python_exe) if workerenv else sys.executable

    # Run the command in the worker environment
    if args.command[0] == "--":
        args.command = args.command[1:]
    command = [pypath] + args.command
    fn.FUNCNODES_LOGGER.debug("Executing: %s", command)

    subprocess.run(command)


def worker_modules_task(args: argparse.Namespace):
    cfg = _worker_conf_from_args(args)
    workerenv = get_worker_venv(cfg)
    pypath = str(workerenv.python_exe) if workerenv else sys.executable
    command = [pypath, "-m", "funcnodes", "modules", args.moduletask]

    subprocess.run(command)


def task_modules(args: argparse.Namespace):
    """
    Performs a task on modules.

    Args:
      args (argparse.Namespace): The arguments passed to the function.

    Returns:
      None

    Examples:
      >>> task_modules(args)
      None
    """
    if args.moduletask == "list":
        from funcnodes_core.utils import plugins

        for k, v in plugins.get_installed_modules().items():
            value_str = repr(v)  # Convert the value to a string
            indented_value = textwrap.indent(
                textwrap.fill(value_str, subsequent_indent="\t", width=80), "\t"
            )
            print(f"{k}:\n{indented_value}")

    else:
        raise Exception(f"Unknown moduletask: {args.moduletask}")


def add_runserver_parser(subparsers):
    parser = subparsers.add_parser("runserver", help="Run the server")
    parser.add_argument(
        "--host",
        default=fn.config.get_config().get("frontend", {}).get("host", None),
        help="Host to run the server on",
    )
    parser.add_argument(
        "--port",
        default=fn.config.get_config().get("frontend", {}).get("port", 8000),
        type=int,
        help="Port to run the server on",
    )
    parser.add_argument(
        "--no-browser",
        action="store_false",
        help="Do not open the browser after starting the server",
    )
    parser.add_argument(
        "--no-manager", action="store_false", help="Do not start the worker manager"
    )
    parser.add_argument(
        "--worker_manager_host",
        default=None,
        help="The host to run the worker manager on",
    )
    parser.add_argument(
        "--worker_manager_port",
        default=None,
        type=int,
        help="The port to run the worker manager on",
    )
    parser.add_argument(
        "--worker_manager_ssl",
        action="store_true",
        help="Use SSL for the worker manager",
    )

    parser.add_argument(
        "--frontend",
        default="react_flow",
        help="The frontend to use (e.g. react_flow)",
        choices=["react_flow"],
    )

    parser.add_argument(
        "--worker_host",
        default="localhost",
        help="The host to run the worker on",
    )
    parser.add_argument(
        "--worker_port",
        default=9380,
        type=int,
        help="The port to run the worker on",
    )
    parser.add_argument(
        "--worker_ssl",
        action="store_true",
        help="Use SSL for the worker",
    )

    parser.set_defaults(long_running=True)


def add_standalone_parser(subparsers):
    parser = subparsers.add_parser(
        "standalone",
        help="Open a .fnw file with its own worker (no manager)",
    )
    parser.set_defaults(long_running=True)

    parser.add_argument(
        "fnw_file",
        nargs="?",
        type=str,
        default=None,
        help="Path to the .fnw file to open",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Register FuncNodes as the default opener for .fnw files",
    )
    parser.add_argument(
        "--config-dir",
        type=str,
        default=None,
        help="Config directory (default: <fnw_dir>/<fnw_stem>_config)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host to bind to",
    )
    parser.add_argument(
        "--worker-port",
        type=int,
        default=None,
        help="Worker port (default: auto)",
    )
    parser.add_argument(
        "--port",
        "--ui-port",
        dest="ui_port",
        type=int,
        default=None,
        help="UI server port (default: auto)",
    )
    parser.add_argument(
        "--no-browser",
        dest="open_browser",
        action="store_false",
        default=True,
        help="Don't open browser automatically",
    )


def validate_standalone_args(parser: argparse.ArgumentParser, args: argparse.Namespace):
    if getattr(args, "task", None) != "standalone":
        return

    register = bool(getattr(args, "register", False))
    fnw_file = getattr(args, "fnw_file", None)

    if register:
        if fnw_file is not None:
            parser.error("--register does not take a .fnw file argument")
        # Registration should run in-process (no subprocess monitor indirection).
        setattr(args, "long_running", False)
        return

    if not fnw_file:
        parser.error(
            "the following arguments are required: fnw_file (unless --register)"
        )


def _add_worker_identifiers(parser):
    parser.add_argument(
        "--uuid",
        default=None,
        help="The UUID of the worker (shared across subcommands)",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="The name of the worker (shared across subcommands)",
    )


def add_worker_parser(subparsers):
    parser = subparsers.add_parser("worker", help="Manage workers")
    worker_subparsers = parser.add_subparsers(
        dest="workertask", help="Worker-related tasks", required=True
    )

    _add_worker_identifiers(parser)  # Add globally to "worker"

    # List workers
    list_parser = worker_subparsers.add_parser("list", help="List all workers")
    list_parser.add_argument(
        "--full", action="store_true", help="Show detailed worker information"
    )

    # Listen to worker logs
    listen_parser = worker_subparsers.add_parser(  # noqa: F841
        "listen", help="Listen to a worker"
    )

    # Activate worker environment
    activate_parser = worker_subparsers.add_parser(  # noqa: F841
        "activate", help="Activate the worker environment"
    )

    # Run a Python command in the worker environment
    py_parser = worker_subparsers.add_parser(
        "py", help="Run python in the worker environment"
    )
    py_parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="The command to run in the worker environment",
    )

    # Execute a command on a running worker
    command_parser = worker_subparsers.add_parser(
        "command", help="Execute a command on a running worker"
    )
    command_parser.add_argument(
        "-c",
        "--command",
        required=True,
        help="The exposed method name to call",
    )

    # Start a new worker
    new_worker_parser = worker_subparsers.add_parser("new", help="Start a new worker")
    new_worker_parser.set_defaults(long_running=True)
    new_worker_parser.add_argument(
        "--workertype", default=None, help="The type of worker to start"
    )
    new_worker_parser.add_argument(
        "--create-only", action="store_true", help="Only create a new worker instance"
    )
    new_worker_parser.add_argument(
        "--not-in-venv", action="store_false", dest="in_venv", help="Do not use a venv"
    )

    # Start an existing worker
    start_worker_parser = worker_subparsers.add_parser(
        "start", help="Start an existing worker"
    )
    start_worker_parser.set_defaults(long_running=True)
    start_worker_parser.add_argument(
        "--workertype", default=None, help="The type of worker to start"
    )

    # Stop an existing worker
    stop_worker_parser = worker_subparsers.add_parser(  # noqa: F841
        "stop", help="Stops an existing worker"
    )

    add_modules_parser(worker_subparsers)


def add_worker_manager_parser(subparsers):
    parser = subparsers.add_parser(
        "startworkermanager", help="Start the worker manager"
    )
    parser.add_argument(
        "--host", default=None, help="The host to run the worker manager on"
    )
    parser.add_argument(
        "--port", default=None, type=int, help="The port to run the worker manager on"
    )
    parser.set_defaults(long_running=True)


def add_modules_parser(subparsers):
    parser = subparsers.add_parser("modules", help="Manage modules")
    parser.add_argument("moduletask", help="Task to perform on modules")


def _submain(args):
    fn.FUNCNODES_LOGGER.debug("Running funcnodes with args: %s", args)
    if args.task == "runserver":
        task_run_server(args)
    elif args.task == "standalone":
        task_standalone(args)
    elif args.task == "worker":
        task_worker(args)
    elif args.task == "startworkermanager":
        start_worker_manager(args)
    elif args.task == "modules":
        task_modules(args)
    else:
        raise Exception(f"Unknown task: {args.task}")
    # except Exception as exc:
    #     fn.FUNCNODES_LOGGER.exception(exc)
    #     raise


def main():
    """
    The main function.

    Returns:
      None

    Examples:
      >>> main()
      None
    """

    try:
        parser = argparse.ArgumentParser(description="Funcnodes Cli.")

        parser.add_argument(
            "--dir",
            default=None,
            help="Funcnodes project directory",
        )

        parser.add_argument(
            "--profile",
            action="store_true",
            help="Profile the code",
        )

        parser.add_argument(
            "--use-subprocess-monitor",
            default=os.environ.get("USE_SUBPROCESS_MONITOR", "1"),
            type=int,
            help="Use the subprocess monitor to run the code",
        )

        subparsers = parser.add_subparsers(dest="task", required=True)

        # Add subparsers for each major task
        add_runserver_parser(subparsers)
        add_standalone_parser(subparsers)
        add_worker_parser(subparsers)
        add_worker_manager_parser(subparsers)
        add_modules_parser(subparsers)

        # Global worker arguments
        parser.add_argument(
            "--debug", action="store_true", help="Run the worker in debug mode"
        )

        parser.add_argument(
            "--version", action="version", version=f"%(prog)s {fn.__version__}"
        )
        args, unknown_args = parser.parse_known_args()
        if unknown_args:
            if args.task == "worker" and getattr(args, "workertask", None) == "command":
                setattr(args, "kwargs", unknown_args)
            else:
                parser.error(f"unrecognized arguments: {' '.join(unknown_args)}")

        validate_standalone_args(parser, args)

        if args.dir:
            fn.config.reload(os.path.abspath(args.dir))
            # try:
        if args.debug:
            fn.FUNCNODES_LOGGER.setLevel("DEBUG")

        os.environ["USE_SUBPROCESS_MONITOR"] = str(args.use_subprocess_monitor)

        if (
            getattr(args, "long_running", False)
            and os.environ.get("SUBPROCESS_MONITOR_PID") is None
            and int(os.environ.get("USE_SUBPROCESS_MONITOR", "1"))
            and subprocess_monitor
        ):
            fn.FUNCNODES_LOGGER.info("Starting subprocess via monitor")

            async def via_subprocess_monitor():
                monitor = subprocess_monitor.SubprocessMonitor(
                    logger=fn.FUNCNODES_LOGGER,
                )

                runtask = asyncio.create_task(monitor.run())
                try:
                    await asyncio.sleep(1)
                    resp = await subprocess_monitor.send_spawn_request(
                        str(Path(sys.executable).absolute()),
                        [os.path.abspath(__file__)] + sys.argv[1:],
                    )
                    if "pid" not in resp:
                        raise Exception(f"Subprocess failed: {resp}")
                    fn.FUNCNODES_LOGGER.debug("Subprocess started: %s", resp["pid"])
                    await subprocess_monitor.subscribe(
                        pid=resp["pid"], callback=lambda x: print(x["data"])
                    )
                    fn.FUNCNODES_LOGGER.debug("Subprocess ended:  %s", resp["pid"])
                    await asyncio.sleep(1)
                    while len(monitor.process_ownership) > 0:
                        await asyncio.sleep(1)
                except (KeyboardInterrupt, asyncio.CancelledError):
                    monitor.stop_serve()
                    await runtask

            asyncio.run(via_subprocess_monitor())
            return

        try:
            if args.profile and yappi is not None:
                print("Profiling the run to", os.path.abspath("funcnodesprofile.prof"))

                def periodic_dump(profiler, interval=10):
                    """Periodically dumps the profiler stats to a file."""
                    # counter = 0
                    while profiler.custom_running:
                        print(
                            "Profiling the run to",
                            os.path.abspath("funcnodesprofile.prof"),
                        )
                        time.sleep(interval)
                        if not profiler.custom_running:
                            break
                        # counter += 1
                        filename = "funcnodesprofile.prof"
                        yappi.get_func_stats().save("funcnodesprofile.pstat", "pstat")
                        print(f"Profile dumped to {filename}")
                    print("Profiler stopped")

                yappi.set_clock_type("WALL")

                yappi.custom_running = True  # Custom flag to control the thread
                yappi.start()
                # Start the background thread for periodic dumps
                dump_thread = threading.Thread(
                    target=periodic_dump, args=(yappi, 10), daemon=True
                )
                dump_thread.start()
            elif args.profile:
                warnings.warn(
                    "profiling is not available without yappi installed, "
                    "add funcnodes[profile] to your requirements or "
                    "install yappi manually"
                )

            _submain(args)

        finally:
            if args.profile and yappi is not None:
                yappi.stop()
                # yappi.get_thread_stats()
                yappi.get_func_stats().save("funcnodesprofile.pstat", "pstat")
                # profiler.disable()
                # profiler.running = False  # Stop the background thread
                # stats = pstats.Stats(profiler)
                # stats.dump_stats("funcnodesprofile.prof")

    except Exception as exc:
        fn.FUNCNODES_LOGGER.exception(exc)
        raise
    finally:
        fn.FUNCNODES_LOGGER.info("Funcnodes finished")


if __name__ == "__main__":
    main()
