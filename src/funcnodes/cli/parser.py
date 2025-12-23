import argparse
import os

import funcnodes as fn


# =============================================================================
# CLI Parser Setup
# =============================================================================


def _add_worker_identifiers(parser):
    """Add common worker identifier arguments to a parser."""
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


def add_runserver_parser(subparsers):
    """Add the 'runserver' subcommand parser."""
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
        "--no-manager",
        action="store_false",
        help="Do not start the worker manager",
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
    """Add the 'standalone' subcommand parser."""
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
    """Validate arguments for the standalone subcommand."""
    if getattr(args, "task", None) != "standalone":
        return

    register = bool(getattr(args, "register", False))
    fnw_file = getattr(args, "fnw_file", None)

    if register:
        if fnw_file is not None:
            parser.error("--register does not take a .fnw file argument")
        # Registration should run in-process (no subprocess monitor indirection)
        setattr(args, "long_running", False)
        return

    if not fnw_file:
        parser.error(
            "the following arguments are required: fnw_file (unless --register)"
        )


def add_worker_parser(subparsers):
    """Add the 'worker' subcommand parser with all worker-related subcommands."""
    parser = subparsers.add_parser("worker", help="Manage workers")
    worker_subparsers = parser.add_subparsers(
        dest="workertask", help="Worker-related tasks", required=True
    )

    _add_worker_identifiers(parser)

    # List workers
    list_parser = worker_subparsers.add_parser("list", help="List all workers")
    list_parser.add_argument(
        "--full", action="store_true", help="Show detailed worker information"
    )

    # Listen to worker logs
    worker_subparsers.add_parser("listen", help="Listen to a worker")

    # Activate worker environment
    worker_subparsers.add_parser("activate", help="Activate the worker environment")

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
    worker_subparsers.add_parser("stop", help="Stops an existing worker")

    # Add modules subparser under worker
    add_modules_parser(worker_subparsers)


def add_worker_manager_parser(subparsers):
    """Add the 'startworkermanager' subcommand parser."""
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
    """Add the 'modules' subcommand parser."""
    parser = subparsers.add_parser("modules", help="Manage modules")
    parser.add_argument("moduletask", help="Task to perform on modules")


def add_cli_parser(subparsers):
    """Add the 'cli' subcommand parser."""
    subparsers.add_parser("cli", help="Launch the interactive CLI")


def _setup_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(description="Funcnodes Cli.")

    # Global arguments
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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run the worker in debug mode",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {fn.__version__}",
    )

    # Add subparsers for each major task
    subparsers = parser.add_subparsers(dest="task", required=False)
    add_runserver_parser(subparsers)
    add_standalone_parser(subparsers)
    add_worker_parser(subparsers)
    add_worker_manager_parser(subparsers)
    add_modules_parser(subparsers)
    add_cli_parser(subparsers)

    return parser
