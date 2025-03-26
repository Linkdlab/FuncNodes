import threading
from typing import Type

import funcnodes as fn
import argparse
from pprint import pprint
import textwrap
import sys
import os
import time
import shutil
from funcnodes.utils.cmd import build_worker_start
import asyncio
import dotenv

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
        debug=args.debug,
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
    mng = fn.worker.worker_manager.WorkerManager(debug=args.debug)
    if args.full:
        pprint(mng.get_all_workercfg())
    else:
        for cf in mng.get_all_workercfg():
            print(f"{cf['uuid']}\t{cf.get('name')}")


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

    fn.FUNCNODES_LOGGER.info(
        "Starting new worker of type %s", args.workertype or "WSWorker"
    )

    mng = fn.worker.worker_manager.WorkerManager(debug=args.debug)

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
    if cfg["env_path"] and venvmngr:
        workerenv = venvmngr.UVVenvManager.get_virtual_env(cfg["env_path"])

        update_on_startup = cfg.get("update_on_startup", {})
        if update_on_startup.get("funcnodes", True):
            workerenv.install_package("funcnodes", upgrade=True)
        if update_on_startup.get("funcnodes-core", True):
            workerenv.install_package("funcnodes-core", upgrade=True)
        if update_on_startup.get("funcnodes-core", True):
            workerenv.install_package("funcnodes-worker", upgrade=True)
        cfg["python_path"] = str(workerenv.python_exe)

    if cfg.get("python_path", sys.executable) != sys.executable:
        # run the worker with the same python executable
        if not os.path.exists(cfg["python_path"]):
            raise Exception(f"Python executable not found: {cfg['python_path']}")

        kwargs = {}
        if args.debug:
            kwargs["debug"] = args.debug
        if args.profile:
            kwargs["profile"] = args.profile
        calllist = [
            cfg["python_path"],
            "-m",
        ] + build_worker_start(uuid=cfg["uuid"], workertype=args.workertype, **kwargs)

        return os.execv(
            cfg["python_path"],
            calllist,
        )

    workertype = args.workertype
    if workertype is None:
        workertype = cfg.get("type", "WSWorker")

    worker_class: Type[fn.worker.Worker] = getattr(fn.worker, workertype)
    fn.FUNCNODES_LOGGER.info("Starting existing worker of type %s", workertype)
    worker = worker_class(uuid=cfg["uuid"], debug=args.debug)

    worker.run_forever()


def stop_worker(args: argparse.Namespace):
    cfg = _worker_conf_from_args(args)
    mng = fn.worker.worker_manager.WorkerManager(debug=args.debug)
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

    mng = fn.worker.worker_manager.WorkerManager(debug=args.debug)
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

    # Run the command in the worker environment
    if args.command[0] == "--":
        args.command = args.command[1:]
    command = [cfg["python_path"]] + args.command
    fn.FUNCNODES_LOGGER.debug("Executing: %s", command)

    subprocess.run(command)


def worker_modules_task(args: argparse.Namespace):
    cfg = _worker_conf_from_args(args)
    command = [cfg["python_path"], "-m", "funcnodes", "modules", args.moduletask]

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

    parser.set_defaults(long_running=True)


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

        if args.dir:
            fn.config.reload(os.path.abspath(args.dir))
            # try:
        if args.debug:
            fn.FUNCNODES_LOGGER.setLevel("DEBUG")

        if (
            getattr(args, "long_running", False)
            and os.environ.get("SUBPROCESS_MONITOR_PID") is None
            and int(os.environ.get("USE_SUBPROCESS_MONITOR", "1"))
            and subprocess_monitor
        ):
            fn.FUNCNODES_LOGGER.info("Starting subprocess via monitor")

            async def via_subprocess_monitor():
                monitor = subprocess_monitor.SubprocessMonitor()
                asyncio.create_task(monitor.run())
                await asyncio.sleep(1)
                resp = await subprocess_monitor.send_spawn_request(
                    sys.executable,
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


if __name__ == "__main__":
    main()
