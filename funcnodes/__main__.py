from typing import Type
from funcnodes.frontends.funcnodes_react import run_server
import funcnodes as fn
import argparse


def main():
    parser = argparse.ArgumentParser(description="Funcnodes Cli.")
    parser.add_argument("task", help="The task to perform")
    parser.add_argument(
        "--port",
        help="Port to run the server on",
        default=fn.config.CONFIG["frontend"]["port"],
    )
    parser.add_argument(
        "--no-browser",
        help="Open the browser after starting the server",
        action="store_false",
    )

    parser.add_argument(
        "--workertype",
        help="The type of worker to start",
        default="WSWorker",
    )
    parser.add_argument(
        "--new",
        help="Create a new instance",
        action="store_true",
    )
    parser.add_argument(
        "--uuid",
        help="The uuid of the worker to start",
        default=None,
        required=False,
    )

    args = parser.parse_args()
    try:

        # Example of handling tasks
        if args.task == "runserver":

            run_server(port=args.port, open_browser=args.no_browser)

        elif args.task == "startworker":
            worker_class: Type[fn.worker.Worker] = getattr(fn.worker, args.workertype)
            if args.new:
                fn.FUNCNODES_LOGGER.info(
                    f"Starting new worker of type {args.workertype}"
                )
                worker = worker_class()
                worker.run_forever()
            else:
                fn.FUNCNODES_LOGGER.info(
                    f"Starting existing worker of type {args.workertype} with uuid {args.uuid}"
                )
                if args.uuid is None:
                    raise Exception("uuid is required to start an existing worker")
                worker = worker_class(uuid=args.uuid)
                worker.run_forever()

        elif args.task == "startworkermanager":
            fn.worker.worker_manager.start_worker_manager()
        else:
            print(f"Unknown task: {args.task}")
    except Exception as e:
        fn.FUNCNODES_LOGGER.exception(e)
        raise

    import time

    time.sleep(1)


if __name__ == "__main__":
    main()
