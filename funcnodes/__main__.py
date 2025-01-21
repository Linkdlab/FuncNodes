from typing import Type
from funcnodes_react_flow import run_server
import funcnodes as fn
import argparse
from pprint import pprint
import sys
import os
import time
import shutil
from funcnodes.utils.cmd import build_worker_start
import asyncio
import venvmngr

try:
    from setproctitle import setproctitle
except ModuleNotFoundError:
    setproctitle = print


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
    setproctitle("funcnodes_server")
    run_server(
        port=args.port,
        open_browser=args.no_browser,
        worker_manager_host=args.worker_manager_host,
        worker_manager_port=args.worker_manager_port,
        worker_manager_ssl=args.worker_manager_ssl,
        start_worker_manager=args.no_manager,
    )


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
    mng = fn.worker.worker_manager.WorkerManager()
    if args.full:
        pprint(mng.get_all_workercfg())
    else:
        for cf in mng.get_all_workercfg():
            print(f"{cf['uuid']}\t{cf.get('name')}")
            print(f"  {cf['python_path']}")


def start_new_worker(args: argparse.Namespace):
    """
    Starts a new worker.

    Args:
      args (argparse.Namespace): The arguments passed to the function.

    Returns:
      None

    Examples:
      >>> start_new_worker(args)
      None
    """

    fn.FUNCNODES_LOGGER.info(f"Starting new worker of type {args.workertype}")

    mng = fn.worker.worker_manager.WorkerManager()

    new_worker_routine = mng.new_worker(
        name=args.name,
        uuid=args.uuid,
        workertype=args.workertype or "WSWorker",
        in_venv=args.in_venv,
    )
    import asyncio

    new_worker = asyncio.run(new_worker_routine)

    args.uuid = new_worker.uuid()
    args.name = new_worker.name()

    if args.create_only:
        return
    return start_existing_worker(args)


def start_existing_worker(args: argparse.Namespace):
    """
    Starts an existing worker.

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

    cfg = _worker_conf_from_args(args)
    if cfg["env_path"]:
        workerenv = venvmngr.UVVenvManager.get_virtual_env(cfg["env_path"])

        update_on_startup = cfg.get("update_on_startup", {})
        if update_on_startup.get("funcnodes", True):
            workerenv.install_package("funcnodes", upgrade=True)
        if update_on_startup.get("funcnodes-core", True):
            workerenv.install_package("funcnodes-core", upgrade=True)
        cfg["python_path"] = str(workerenv.python_exe)

    if cfg.get("python_path", sys.executable) != sys.executable:
        # run the worker with the same python executable
        if not os.path.exists(cfg["python_path"]):
            raise Exception(f"Python executable not found: {cfg['python_path']}")
        calllist = [
            cfg["python_path"],
            "-m",
        ] + build_worker_start(uuid=cfg["uuid"], workertype=args.workertype)

        return os.execv(
            cfg["python_path"],
            calllist,
        )

    workertype = args.workertype
    if workertype is None:
        workertype = cfg.get("type", "WSWorker")

    worker_class: Type[fn.worker.Worker] = getattr(fn.worker, workertype)
    fn.FUNCNODES_LOGGER.info(f"Starting existing worker of type {workertype}")
    worker = worker_class(uuid=cfg["uuid"], debug=args.debug)

    setproctitle("worker " + worker.uuid())
    worker.run_forever()


def stop_worker(args: argparse.Namespace):
    cfg = _worker_conf_from_args(args)
    mng = fn.worker.worker_manager.WorkerManager()
    asyncio.run(mng.stop_worker(cfg["uuid"]))


def _worker_conf_from_args(args: argparse.Namespace):
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
    if args.uuid is None:
        if args.name is None:
            raise Exception("uuid or name is required to start an existing worker")

    mng = fn.worker.worker_manager.WorkerManager()
    cfg = None
    if args.uuid:
        for cf in mng.get_all_workercfg():
            if cf["uuid"] == args.uuid:
                cfg = cf
                break

        if cfg is None:
            raise Exception("No worker found with the given uuid")

    if args.name:
        if cfg is None:
            for cf in mng.get_all_workercfg():
                if cf.get("name") == args.name:
                    cfg = cf
                    break
        else:
            if cfg.get("name") != args.name:
                raise Exception(
                    "Worker found with the given uuid but with a different name"
                )

    if cfg is None:
        raise Exception("No worker found with the given uuid or name")

    return cfg


def listen_worker(args: argparse.Namespace):
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

    cfg = _worker_conf_from_args(args)
    log_file_path = os.path.join(cfg["data_path"], "worker.log")
    # log file path
    while True:
        if os.path.exists(log_file_path):
            current_size = os.path.getsize(log_file_path)
            with open(log_file_path, "r") as log_file:
                # Read the entire file initially
                for line in log_file:
                    print(line, end="")  # Print each line from the existing content

                # Move to the end of the file to begin tailing new content
                while True:
                    line = log_file.readline()
                    if line:
                        print(line, end="")  # Print any new line added to the file
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
            return start_existing_worker(args)
        elif workertask == "stop":
            return stop_worker(args)
        elif workertask == "new":
            return start_new_worker(args)
        elif workertask == "list":
            return list_workers(args)
        elif workertask == "listen":
            return listen_worker(args)
        elif workertask == "activate":
            return activate_worker_env(args)
        elif workertask == "py":
            return py_in_worker_env(args)
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
    setproctitle("worker_manager")

    fn.worker.worker_manager.start_worker_manager(
        host=args.host, port=args.port, debug=args.debug
    )


def activate_worker_env(args: argparse.Namespace):
    """
    Activates the funcnodes environment.

    Returns:
      None

    Examples:
      >>> activate_fn_env()
      None
    """
    import subprocess

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

    # Run the command in the worker environment
    print(f"{cfg['python_path']} {' '.join(args.command)}")
    os.system(
        f"{cfg['python_path']} {' '.join(args.command)}"
    )  # Run the command in the worker environment


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
        pprint(fn.utils.plugins.get_installed_modules())
    else:
        raise Exception(f"Unknown moduletask: {args.moduletask}")


def add_runserver_parser(subparsers):
    parser = subparsers.add_parser("runserver", help="Run the server")
    parser.add_argument(
        "--port",
        default=fn.config.CONFIG["frontend"]["port"],
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

    # Start a new worker
    new_worker_parser = worker_subparsers.add_parser("new", help="Start a new worker")
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
    start_worker_parser.add_argument(
        "--workertype", default=None, help="The type of worker to start"
    )

    # Stop an existing worker
    stop_worker_parser = worker_subparsers.add_parser(  # noqa: F841
        "stop", help="Stops an existing worker"
    )


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


def add_modules_parser(subparsers):
    parser = subparsers.add_parser("modules", help="Manage modules")
    parser.add_argument("moduletask", help="Task to perform on modules")


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
        subparsers = parser.add_subparsers(dest="task", required=True)

        # Add subparsers for each major task
        add_runserver_parser(subparsers)
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
        args = parser.parse_args()
        # try:
        if args.task == "runserver":
            task_run_server(args)
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
    except Exception as exc:
        fn.FUNCNODES_LOGGER.exception(exc)
        raise


if __name__ == "__main__":
    main()
