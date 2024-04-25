from typing import Type
from funcnodes.frontends.funcnodes_react import run_server
import funcnodes as fn
import argparse
from pprint import pprint
import sys
import os


def task_run_server(args: argparse.Namespace):
    run_server(port=args.port, open_browser=args.no_browser)


def list_workers(args: argparse.Namespace):
    mng = fn.worker.worker_manager.WorkerManager()
    if args.full:
        pprint(mng.get_all_workercfg())
    else:
        for cf in mng.get_all_workercfg():
            print(f"{cf['uuid']}\t{cf.get('name')}")


def start_new_worker(args: argparse.Namespace):
    worker_class: Type[fn.worker.Worker] = getattr(fn.worker, args.workertype)
    fn.FUNCNODES_LOGGER.info(f"Starting new worker of type {args.workertype}")

    worker = worker_class(uuid=args.uuid, name=args.name)
    worker.run_forever()


def start_existing_worker(args: argparse.Namespace):
    worker_class: Type[fn.worker.Worker] = getattr(fn.worker, args.workertype)

    if args.uuid is None:
        if args.name is None:
            raise Exception("uuid or name is required to start an existing worker")

    mng = fn.worker.worker_manager.WorkerManager()
    cfg = None
    for cf in mng.get_all_workercfg():
        if args.uuid and cf["uuid"] != args.uuid:
            continue
        if args.name and cf.get("name") != args.name:
            continue
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
    worker = worker_class(uuid=cfg["uuid"])

    worker.run_forever()


def task_worker(args: argparse.Namespace):

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
    fn.worker.worker_manager.start_worker_manager()


def main():
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
    # Subparser for the 'startworkermanager' task
    subparsers.add_parser("startworkermanager", help="Start the worker manager")

    # Global argument applicable to all subparsers
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
    else:
        raise Exception(f"Unknown task: {args.task}")
    # except Exception as exc:
    #     fn.FUNCNODES_LOGGER.exception(exc)
    #     raise


if __name__ == "__main__":
    main()
