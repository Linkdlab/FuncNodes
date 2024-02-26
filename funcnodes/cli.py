from funcnodes.frontends.funcnodes_react import run_server
import argparse


def main():
    parser = argparse.ArgumentParser(description="Funcnodes Cli.")
    parser.add_argument("task", help="The task to perform")
    parser.add_argument("--port", help="Port to run the server on", default=8000)
    args = parser.parse_args()

    # Example of handling tasks
    if args.task == "runserver":

        run_server(
            port=args.port,
        )

    else:
        print(f"Unknown task: {args.task}")


if __name__ == "__main__":
    main()
