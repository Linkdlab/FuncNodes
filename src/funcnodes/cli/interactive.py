import shlex
from types import SimpleNamespace

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

import funcnodes as fn

from .tasks import (
    start_worker_manager,
    task_modules,
    task_run_server,
    task_standalone,
    task_worker,
)


class _DefaultIO:
    def __init__(self, console: Console):
        self._console = console

    def ask(self, prompt: str, **kwargs):
        return Prompt.ask(prompt, console=self._console, **kwargs)

    def confirm(self, prompt: str, **kwargs):
        return Confirm.ask(prompt, console=self._console, **kwargs)

    def ask_int(self, prompt: str, **kwargs):
        return IntPrompt.ask(prompt, console=self._console, **kwargs)


def _optional_text(io, console: Console, prompt: str, default=None):
    while True:
        value = io.ask(prompt, default="" if default is None else str(default))
        if value is None:
            return default
        value = str(value).strip()
        if value == "":
            return default
        return value


def _optional_int(io, console: Console, prompt: str, default=None):
    while True:
        value = io.ask(prompt, default="" if default is None else str(default))
        if value is None:
            return default
        value = str(value).strip()
        if value == "":
            return default
        try:
            return int(value)
        except ValueError:
            console.print("Please enter a valid integer.", style="red")


def _print_header(console: Console, title: str, subtitle: str | None = None):
    content = title if subtitle is None else f"{title}\n{subtitle}"
    console.print(Panel.fit(content, title="FuncNodes", style="bold cyan"))


def _render_menu(console: Console, title: str, items: list[tuple[str, str]]):
    table = Table(title=title, header_style="bold magenta")
    table.add_column("Key", style="bold")
    table.add_column("Action")
    for key, label in items:
        table.add_row(key, label)
    console.print(table)


def _prompt_worker_identifiers(io, console: Console):
    uuid = _optional_text(io, console, "Worker uuid (blank to use name)", default=None)
    if uuid:
        return {"uuid": uuid, "name": None}
    name = _optional_text(io, console, "Worker name", default=None)
    if not name:
        raise ValueError("Worker uuid or name is required.")
    return {"uuid": None, "name": name}


def _run_runserver(console: Console, io, base_args: SimpleNamespace):
    frontend_cfg = fn.config.get_config().get("frontend", {})
    default_host = frontend_cfg.get("host") or "localhost"
    default_port = int(frontend_cfg.get("port", 8000))

    host = io.ask("Server host", default=str(default_host))
    port = io.ask_int("Server port", default=default_port)
    open_browser = io.confirm("Open browser after start", default=True)
    start_manager = io.confirm("Start worker manager", default=True)

    worker_manager_host = None
    worker_manager_port = None
    worker_manager_ssl = False
    if start_manager:
        worker_manager_host = _optional_text(
            io, console, "Worker manager host (blank for default)", default=None
        )
        worker_manager_port = _optional_int(
            io, console, "Worker manager port (blank for default)", default=None
        )
        worker_manager_ssl = io.confirm("Worker manager SSL", default=False)

    worker_host = io.ask("Worker host", default="localhost")
    worker_port = io.ask_int("Worker port", default=9380)
    worker_ssl = io.confirm("Worker SSL", default=False)

    args = SimpleNamespace(
        frontend="react_flow",
        port=port,
        host=host,
        no_browser=open_browser,
        worker_manager_host=worker_manager_host,
        worker_manager_port=worker_manager_port,
        worker_manager_ssl=worker_manager_ssl,
        no_manager=start_manager,
        worker_host=worker_host,
        worker_port=worker_port,
        worker_ssl=worker_ssl,
        debug=bool(getattr(base_args, "debug", False)),
    )
    task_run_server(args)


def _run_standalone(console: Console, io, base_args: SimpleNamespace):
    register = io.confirm("Register FuncNodes as .fnw opener", default=False)
    if register:
        args = SimpleNamespace(register=True)
        task_standalone(args)
        return

    fnw_file = _optional_text(io, console, "Path to .fnw file", default=None)
    if not fnw_file:
        console.print("A .fnw file path is required.", style="red")
        return

    config_dir = _optional_text(
        io, console, "Config dir (blank for default)", default=None
    )
    host = io.ask("Host", default="localhost")
    worker_port = _optional_int(
        io, console, "Worker port (blank for auto)", default=None
    )
    ui_port = _optional_int(io, console, "UI port (blank for auto)", default=None)
    open_browser = io.confirm("Open browser after start", default=True)

    args = SimpleNamespace(
        register=False,
        fnw_file=fnw_file,
        config_dir=config_dir,
        ui_port=ui_port,
        host=host,
        worker_port=worker_port,
        open_browser=open_browser,
        debug=bool(getattr(base_args, "debug", False)),
    )
    task_standalone(args)


def _run_worker_menu(console: Console, io, base_args: SimpleNamespace):
    items = [
        ("1", "List workers"),
        ("2", "Listen to worker logs"),
        ("3", "Start existing worker"),
        ("4", "Create new worker"),
        ("5", "Stop worker"),
        ("6", "Activate worker environment"),
        ("7", "Run python in worker environment"),
        ("8", "Send command to worker"),
        ("9", "Worker modules"),
        ("0", "Back"),
    ]

    while True:
        _render_menu(console, "Worker Menu", items)
        choice = io.ask(
            "Select an action", choices=[item[0] for item in items], default="0"
        )
        if choice == "0":
            return

        try:
            if choice == "1":
                full = io.confirm("Show full worker config", default=False)
                args = SimpleNamespace(
                    workertask="list",
                    debug=bool(getattr(base_args, "debug", False)),
                    full=full,
                    uuid=None,
                    name=None,
                    workertype="WSWorker",
                )
                task_worker(args)
            elif choice == "2":
                identifiers = _prompt_worker_identifiers(io, console)
                args = SimpleNamespace(
                    workertask="listen",
                    debug=bool(getattr(base_args, "debug", False)),
                    uuid=identifiers["uuid"],
                    name=identifiers["name"],
                    workertype="WSWorker",
                )
                task_worker(args)
            elif choice == "3":
                identifiers = _prompt_worker_identifiers(io, console)
                workertype = _optional_text(
                    io, console, "Workertype (blank for default)", default=None
                )
                debug = io.confirm(
                    "Debug mode", default=bool(getattr(base_args, "debug", False))
                )
                profile = io.confirm("Profile worker", default=False)
                args = SimpleNamespace(
                    workertask="start",
                    debug=debug,
                    profile=profile,
                    uuid=identifiers["uuid"],
                    name=identifiers["name"],
                    workertype=workertype,
                )
                task_worker(args)
            elif choice == "4":
                uuid = _optional_text(
                    io, console, "Worker uuid (blank for auto)", default=None
                )
                name = _optional_text(
                    io, console, "Worker name (blank for auto)", default=None
                )
                workertype = _optional_text(
                    io, console, "Workertype (blank for default)", default=None
                )
                in_venv = io.confirm("Use venv", default=True)
                create_only = io.confirm("Create only (do not start)", default=False)
                debug = io.confirm(
                    "Debug mode", default=bool(getattr(base_args, "debug", False))
                )
                profile = io.confirm("Profile worker", default=False)
                args = SimpleNamespace(
                    workertask="new",
                    debug=debug,
                    profile=profile,
                    uuid=uuid,
                    name=name,
                    workertype=workertype,
                    in_venv=in_venv,
                    create_only=create_only,
                )
                task_worker(args)
            elif choice == "5":
                identifiers = _prompt_worker_identifiers(io, console)
                args = SimpleNamespace(
                    workertask="stop",
                    debug=bool(getattr(base_args, "debug", False)),
                    uuid=identifiers["uuid"],
                    name=identifiers["name"],
                    workertype="WSWorker",
                )
                task_worker(args)
            elif choice == "6":
                identifiers = _prompt_worker_identifiers(io, console)
                args = SimpleNamespace(
                    workertask="activate",
                    debug=bool(getattr(base_args, "debug", False)),
                    uuid=identifiers["uuid"],
                    name=identifiers["name"],
                    workertype="WSWorker",
                )
                task_worker(args)
            elif choice == "7":
                identifiers = _prompt_worker_identifiers(io, console)
                command = _optional_text(io, console, "Python command", default=None)
                if not command:
                    console.print("Command is required.", style="red")
                    continue
                args = SimpleNamespace(
                    workertask="py",
                    debug=bool(getattr(base_args, "debug", False)),
                    uuid=identifiers["uuid"],
                    name=identifiers["name"],
                    workertype="WSWorker",
                    command=shlex.split(command),
                )
                task_worker(args)
            elif choice == "8":
                identifiers = _prompt_worker_identifiers(io, console)
                cmd = _optional_text(io, console, "Worker command", default=None)
                if not cmd:
                    console.print("Command is required.", style="red")
                    continue
                extra = _optional_text(
                    io, console, "Extra args (e.g. --foo 1 --bar true)", default=None
                )
                kwargs = shlex.split(extra) if extra else []
                args = SimpleNamespace(
                    workertask="command",
                    debug=bool(getattr(base_args, "debug", False)),
                    uuid=identifiers["uuid"],
                    name=identifiers["name"],
                    workertype="WSWorker",
                    command=cmd,
                    kwargs=kwargs,
                )
                task_worker(args)
            elif choice == "9":
                identifiers = _prompt_worker_identifiers(io, console)
                moduletask = _optional_text(io, console, "Module task", default="list")
                args = SimpleNamespace(
                    workertask="modules",
                    debug=bool(getattr(base_args, "debug", False)),
                    uuid=identifiers["uuid"],
                    name=identifiers["name"],
                    workertype="WSWorker",
                    moduletask=moduletask or "list",
                )
                task_worker(args)
        except Exception as exc:
            console.print(f"Error: {exc}", style="red")


def _run_worker_manager(console: Console, io, base_args: SimpleNamespace):
    host = _optional_text(io, console, "Manager host (blank for default)", default=None)
    port = _optional_int(io, console, "Manager port (blank for default)", default=None)
    debug = io.confirm("Debug mode", default=bool(getattr(base_args, "debug", False)))
    args = SimpleNamespace(host=host, port=port, debug=debug)
    start_worker_manager(args)


def _run_modules(console: Console, io, base_args: SimpleNamespace):
    moduletask = _optional_text(io, console, "Module task", default="list")
    args = SimpleNamespace(moduletask=moduletask or "list")
    task_modules(args)


def run_interactive_cli(
    args: SimpleNamespace | None = None, io=None, console: Console | None = None
):
    console = console or Console()
    io = io or _DefaultIO(console)
    base_args = args or SimpleNamespace(debug=False)

    _print_header(console, "Interactive CLI", "Select an action to continue")

    items = [
        ("1", "Run server"),
        ("2", "Standalone .fnw"),
        ("3", "Worker management"),
        ("4", "Worker manager"),
        ("5", "Modules"),
        ("6", "Show version"),
        ("0", "Exit"),
    ]

    while True:
        _render_menu(console, "Main Menu", items)
        choice = io.ask(
            "Select an action", choices=[item[0] for item in items], default="0"
        )
        if choice == "0":
            console.print("Goodbye!", style="bold green")
            return
        if choice == "1":
            _run_runserver(console, io, base_args)
        elif choice == "2":
            _run_standalone(console, io, base_args)
        elif choice == "3":
            _run_worker_menu(console, io, base_args)
        elif choice == "4":
            _run_worker_manager(console, io, base_args)
        elif choice == "5":
            _run_modules(console, io, base_args)
        elif choice == "6":
            console.print(f"FuncNodes version {fn.__version__}", style="bold cyan")
