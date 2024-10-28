from typing import Type
from funcnodes_react_flow import run_server
import funcnodes as fn
import argparse
from pprint import pprint
import sys
import os
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
    worker_class: Type[fn.worker.Worker] = getattr(fn.worker, args.workertype)
    fn.FUNCNODES_LOGGER.info(f"Starting new worker of type {args.workertype}")

    mng = fn.worker.worker_manager.WorkerManager()
    workerdir = os.path.join(mng.worker_dir, "worker_" + str(args.uuid))
    if not os.path.exists(workerdir):
        os.makedirs(workerdir)
    env_path = os.path.join(workerdir, ".venv")
    env, new = venvmngr.get_or_create_virtual_env(env_path)
    env.install_package("funcnodes")
    env.install_package("venvmngr")

    if env.python_exe != sys.executable:
        nargs = ["worker", "new"]
        if args.uuid:
            nargs += ["--uuid", args.uuid]
        if args.name:
            nargs += ["--name", args.name]
        if args.debug:
            nargs += ["--debug"]
        return env.run_module("funcnodes", args=nargs)

    worker = worker_class(uuid=args.uuid, name=args.name, debug=args.debug)
    setproctitle("worker " + worker.uuid())
    worker.run_forever()


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
    worker_class: Type[fn.worker.Worker] = getattr(fn.worker, args.workertype)

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

    if cfg is None:
        raise Exception("No worker found with the given uuid or name")

    if cfg["python_path"] != sys.executable:
        # run the worker with the same python executable
        if not os.path.exists(cfg["python_path"]):
            raise Exception(f"Python executable not found: {cfg['python_path']}")
        os.execv(cfg["python_path"], ["-m", "funcnodes"] + sys.argv[1:])

    fn.FUNCNODES_LOGGER.info(f"Starting existing worker of type {args.workertype}")
    worker = worker_class(uuid=cfg["uuid"], debug=args.debug)

    setproctitle("worker " + worker.uuid())
    worker.run_forever()


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
    if workertask == "start":
        return start_existing_worker(args)
    elif workertask == "new":
        return start_new_worker(args)
    elif workertask == "list":
        return list_workers(args)
    else:
        raise Exception(f"Unknown workertask: {workertask}")


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


def main():
    """
    The main function.

    Returns:
      None

    Examples:
      >>> main()
      None
    """
    parser = argparse.ArgumentParser(description="Funcnodes Cli.")
    subparsers = parser.add_subparsers(dest="task", required=True)

    # Subparser for the 'runserver' task
    parser_runserver = subparsers.add_parser("runserver", help="Run the server")
    parser_runserver.add_argument(
        "--port",
        default=fn.config.CONFIG["frontend"]["port"],
        help="Port to run the server on",
        type=int,
    )
    parser_runserver.add_argument(
        "--no-browser",
        action="store_false",
        help="Open the browser after starting the server",
    )
    parser_runserver.add_argument(
        "--no-manager",
        action="store_false",
        help="Do not start the worker manager",
    )

    parser_runserver.add_argument(
        "--worker_manager_host",
        default=None,
        help="The host to run the worker manager on",
    )

    parser_runserver.add_argument(
        "--worker_manager_port",
        default=None,
        help="The port to run the worker manager on",
        type=int,
    )

    parser_runserver.add_argument(
        "--worker_manager_ssl",
        action="store_true",
        help="Use SSL for the worker manager",
    )

    # Subparser for the 'startworker' task
    parser_worker = subparsers.add_parser("worker", help="Start a worker")
    parser_worker.add_argument("workertask", help="The task to run in the worker")

    parser_worker.add_argument(
        "--full", action="store_true", help="printing option for extensive output"
    )

    parser_worker.add_argument(
        "--workertype", default="WSWorker", help="The type of worker to start"
    )
    parser_worker.add_argument(
        "--new", action="store_true", help="Create a new instance"
    )
    parser_worker.add_argument(
        "--uuid", default=None, required=False, help="The uuid of the worker to start"
    )

    parser_worker.add_argument(
        "--name", default=None, required=False, help="The name of the worker to start"
    )

    parser_worker.add_argument(
        "--debug", action="store_true", help="Run the worker in debug mode"
    )
    # Subparser for the 'startworkermanager' task
    startworkermanagerparser = subparsers.add_parser(
        "startworkermanager", help="Start the worker manager"
    )

    startworkermanagerparser.add_argument(
        "--host",
        default=None,
        help="The host to run the worker manager on",
    )

    startworkermanagerparser.add_argument(
        "--port",
        default=None,
        help="The port to run the worker manager on",
        type=int,
    )

    startworkermanagerparser.add_argument(
        "--debug", action="store_true", help="Run the worker manager in debug mode"
    )

    # Global argument applicable to all subparsers
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {fn.__version__}"
    )

    modules_parser = subparsers.add_parser("modules", help="")
    modules_parser.add_argument("moduletask", help="The task to run on the modules")

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


if __name__ == "__main__":
    main()
