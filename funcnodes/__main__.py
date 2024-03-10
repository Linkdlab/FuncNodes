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
    args = parser.parse_args()

    # Example of handling tasks
    if args.task == "runserver":

        run_server(port=args.port, open_browser=args.no_browser)

    else:
        print(f"Unknown task: {args.task}")


if __name__ == "__main__":
    main()
