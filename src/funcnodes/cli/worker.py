import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from pprint import pprint
from typing import Any, Optional, Type

import funcnodes as fn
from funcnodes.utils.cmd import build_worker_start
from funcnodes_worker.worker import WorkerJson, worker_json_get_data_path

from .runtime import subprocess, venvmngr


# =============================================================================
# Worker Configuration Functions
# =============================================================================


def get_worker_venv(cfg: WorkerJson) -> Optional[venvmngr.UVVenvManager]:
    """Get the virtual environment manager for a worker configuration."""
    if cfg["env_path"] and venvmngr:
        workerenv = venvmngr.UVVenvManager.get_virtual_env(cfg["env_path"])
        return workerenv
    return None


def _get_worker_conf(uuid: str, name: str, workertype: str, debug: bool) -> WorkerJson:
    """
    Get worker configuration by UUID or name.

    Args:
        uuid: The UUID of the worker.
        name: The name of the worker.
        workertype: The type of worker.
        debug: Whether debug mode is enabled.

    Returns:
        The worker configuration dictionary.

    Raises:
        Exception: If no worker is found with the given UUID or name.
    """
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
    """Extract worker configuration from parsed arguments."""
    return _get_worker_conf(
        uuid=args.uuid, name=args.name, workertype=args.workertype, debug=args.debug
    )


# =============================================================================
# Worker Operations
# =============================================================================


def list_workers(args: argparse.Namespace):
    """List all workers."""
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
    Start a new worker.

    Args:
        uuid: The UUID of the worker.
        name: The name of the worker.
        workertype: The type of the worker.
        debug: Whether to run the worker in debug mode.
        in_venv: Whether to run the worker in a virtual environment.
        create_only: Whether to create the worker only.
        profile: Whether to run the worker in profile mode.
    """
    fn.FUNCNODES_LOGGER.info(
        f"Starting new worker with uuid: {uuid}, name: {name}, "
        f"workertype: {workertype}, debug: {debug}"
    )

    mng = fn.worker.worker_manager.WorkerManager(debug=debug)

    new_worker_routine = mng.new_worker(
        name=name,
        uuid=uuid,
        workertype=workertype or "WSWorker",
        in_venv=in_venv,
        **kwargs,
    )

    new_worker_config = asyncio.run(new_worker_routine)

    uuid = new_worker_config["uuid"]
    name = new_worker_config.get("name", None)

    if create_only:
        return None

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
    Start an existing worker.

    Args:
        uuid: The UUID of the worker.
        name: The name of the worker.
        workertype: The type of the worker.
        debug: Whether to run the worker in debug mode.
        profile: Whether to run the worker in profile mode.

    Raises:
        Exception: If no worker is found or Python executable is missing.
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
        # Run the worker with the worker's Python executable
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

    return None


def stop_worker(
    uuid: Optional[str] = None,
    name: Optional[str] = None,
    workertype: Optional[str] = "WSWorker",
    debug: bool = False,
):
    """Stop an existing worker."""
    cfg = _get_worker_conf(uuid=uuid, name=name, workertype=workertype, debug=debug)
    mng = fn.worker.worker_manager.WorkerManager(debug=debug)
    asyncio.run(mng.stop_worker(cfg["uuid"]))


def listen_worker(
    uuid: Optional[str] = None,
    name: Optional[str] = None,
    workertype: Optional[str] = "WSWorker",
    debug: bool = False,
    out=sys.stdout.write,
):
    """
    Listen to a running worker's log output.

    Args:
        uuid: The UUID of the worker.
        name: The name of the worker.
        workertype: The type of worker.
        debug: Whether debug mode is enabled.
        out: Output function for log lines.
    """
    cfg = _get_worker_conf(
        uuid=uuid,
        name=name,
        workertype=workertype,
        debug=debug,
    )
    log_file_path = os.path.join(worker_json_get_data_path(cfg), "worker.log")

    while True:
        if os.path.exists(log_file_path):
            current_size = os.path.getsize(log_file_path)
            with open(log_file_path, "r") as log_file:
                # Read the entire file initially
                for line in log_file:
                    out(line)

                # Tail new content
                while True:
                    line = log_file.readline()
                    if line:
                        out(line)
                    else:
                        time.sleep(0.5)

                        if not os.path.exists(log_file_path):
                            break
                        new_size = os.path.getsize(log_file_path)
                        if new_size < current_size:  # Log file has been rotated
                            break
                        current_size = new_size

        time.sleep(5)


def activate_worker_env(args: argparse.Namespace):
    """Activate the worker's virtual environment in a new shell."""
    if not subprocess:
        raise Exception(
            "This command is only available on systems with subprocess support"
        )

    cfg = _worker_conf_from_args(args)
    venv = cfg["env_path"]

    if venv is None:
        raise Exception("This worker does not have an environment")

    if not os.path.exists(venv):
        raise Exception(f"Environment not found: {venv}")

    if sys.platform == "win32":
        venv_activate_script = os.path.join(venv, "Scripts", "activate.bat")
        shell_command = [venv_activate_script, "&&", "cmd /k"]
        executable = None
    else:
        venv_activate_script = os.path.join(venv, "bin", "activate")
        shell_command = f"source {venv_activate_script} && exec $SHELL"
        executable = shutil.which("bash") or shutil.which("sh")

    subprocess.run(shell_command, shell=True, executable=executable)


def py_in_worker_env(args: argparse.Namespace):
    """Run Python in the worker's virtual environment."""
    cfg = _worker_conf_from_args(args)
    workerenv = get_worker_venv(cfg)
    pypath = str(workerenv.python_exe) if workerenv else sys.executable

    if args.command[0] == "--":
        args.command = args.command[1:]

    command = [pypath] + args.command
    fn.FUNCNODES_LOGGER.debug("Executing: %s", command)
    subprocess.run(command)


# =============================================================================
# Worker Command Execution
# =============================================================================


async def call_worker_command(
    worker_config: WorkerJson,
    command: str,
    kwargs: dict[str, Any],
    timeout: float = 30.0,
) -> Any:
    """
    Call a command on a running worker via WebSocket.

    Args:
        worker_config: The worker configuration.
        command: The command method name to call.
        kwargs: Arguments to pass to the command.
        timeout: Maximum time to wait for a response.

    Returns:
        The result of the command execution.

    Raises:
        ValueError: If the worker is not a WebSocket worker or has no port.
        RuntimeError: If the command fails or times out.
    """
    workertype = worker_config.get("type", "WSWorker")
    if workertype != "WSWorker":
        raise ValueError(
            f"Worker {worker_config.get('uuid')} is not a WebSocket worker but "
            f"{workertype}, command is only supported for WebSocket workers for now"
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
    """Execute a command on a running worker and print the result."""
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


def worker_modules_task(args: argparse.Namespace):
    """Run a modules task in the worker's environment."""
    cfg = _worker_conf_from_args(args)
    workerenv = get_worker_venv(cfg)
    pypath = str(workerenv.python_exe) if workerenv else sys.executable
    command = [pypath, "-m", "funcnodes", "modules", args.moduletask]
    subprocess.run(command)
