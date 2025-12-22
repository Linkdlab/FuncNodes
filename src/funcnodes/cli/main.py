import argparse
import asyncio
import os
import sys
import threading
import time
import warnings
from pathlib import Path

import dotenv

import funcnodes as fn

from funcnodes.cli.interactive import run_interactive_cli
from funcnodes.cli.parser import _setup_argument_parser, validate_standalone_args
from funcnodes.cli.runtime import subprocess_monitor
from funcnodes.cli.tasks import (
    start_worker_manager,
    task_modules,
    task_run_server,
    task_standalone,
    task_worker,
)

try:
    # yappi is an optional dependency for profiling
    import yappi
except (ImportError, ModuleNotFoundError):
    yappi = None

dotenv.load_dotenv()


# =============================================================================
# Main Entry Point
# =============================================================================


def _submain(args: argparse.Namespace):
    """Dispatch to the appropriate task handler based on parsed arguments."""
    fn.FUNCNODES_LOGGER.debug("Running funcnodes with args: %s", args)

    if args.task == "runserver":
        task_run_server(args)
    elif args.task == "standalone":
        task_standalone(args)
    elif args.task == "worker":
        task_worker(args)
    elif args.task == "startworkermanager":
        start_worker_manager(args)
    elif args.task == "modules":
        task_modules(args)
    else:
        raise Exception(f"Unknown task: {args.task}")


def _run_with_profiling(args: argparse.Namespace):
    """Run the main task with optional profiling support."""
    try:
        if args.profile and yappi is not None:
            print("Profiling the run to", os.path.abspath("funcnodesprofile.prof"))

            def periodic_dump(profiler, interval=10):
                """Periodically dump profiler stats to a file."""
                while profiler.custom_running:
                    print(
                        "Profiling the run to",
                        os.path.abspath("funcnodesprofile.prof"),
                    )
                    time.sleep(interval)
                    if not profiler.custom_running:
                        break
                    yappi.get_func_stats().save("funcnodesprofile.pstat", "pstat")
                    print("Profile dumped to funcnodesprofile.prof")
                print("Profiler stopped")

            yappi.set_clock_type("WALL")
            yappi.custom_running = True
            yappi.start()

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
            yappi.get_func_stats().save("funcnodesprofile.pstat", "pstat")


async def _run_via_subprocess_monitor(args: argparse.Namespace):
    """Run the command through the subprocess monitor for long-running tasks."""
    monitor = subprocess_monitor.SubprocessMonitor(
        logger=fn.FUNCNODES_LOGGER,
    )

    runtask = asyncio.create_task(monitor.run())
    try:
        await asyncio.sleep(1)
        resp = await subprocess_monitor.send_spawn_request(
            str(Path(sys.executable).absolute()),
            [os.path.abspath(__file__)] + sys.argv[1:],
        )
        if "pid" not in resp:
            raise Exception(f"Subprocess failed: {resp}")

        fn.FUNCNODES_LOGGER.debug("Subprocess started: %s", resp["pid"])

        await subprocess_monitor.subscribe(
            pid=resp["pid"], callback=lambda x: print(x["data"])
        )

        fn.FUNCNODES_LOGGER.debug("Subprocess ended: %s", resp["pid"])
        await asyncio.sleep(1)

        while len(monitor.process_ownership) > 0:
            await asyncio.sleep(1)

    except (KeyboardInterrupt, asyncio.CancelledError):
        monitor.stop_serve()
        await runtask


def main():
    """Main entry point for the FuncNodes CLI."""
    try:
        parser = _setup_argument_parser()
        args, unknown_args = parser.parse_known_args()

        if args.task in (None, "cli"):
            if unknown_args:
                parser.error(f"unrecognized arguments: {' '.join(unknown_args)}")
            if args.dir:
                fn.config.reload(os.path.abspath(args.dir))
            if args.debug:
                fn.FUNCNODES_LOGGER.setLevel("DEBUG")
            os.environ["USE_SUBPROCESS_MONITOR"] = str(args.use_subprocess_monitor)
            run_interactive_cli(args)
            return

        # Handle unknown args for worker command
        if unknown_args:
            if args.task == "worker" and getattr(args, "workertask", None) == "command":
                setattr(args, "kwargs", unknown_args)
            else:
                parser.error(f"unrecognized arguments: {' '.join(unknown_args)}")

        validate_standalone_args(parser, args)

        # Apply configuration
        if args.dir:
            fn.config.reload(os.path.abspath(args.dir))

        if args.debug:
            fn.FUNCNODES_LOGGER.setLevel("DEBUG")

        os.environ["USE_SUBPROCESS_MONITOR"] = str(args.use_subprocess_monitor)

        # Check if we should run via subprocess monitor
        should_use_monitor = (
            getattr(args, "long_running", False)
            and os.environ.get("SUBPROCESS_MONITOR_PID") is None
            and int(os.environ.get("USE_SUBPROCESS_MONITOR", "1"))
            and subprocess_monitor
        )

        if should_use_monitor:
            fn.FUNCNODES_LOGGER.info("Starting subprocess via monitor")
            asyncio.run(_run_via_subprocess_monitor(args))
            return

        _run_with_profiling(args)

    except Exception as exc:
        fn.FUNCNODES_LOGGER.exception(exc)
        raise
    finally:
        fn.FUNCNODES_LOGGER.info("Funcnodes finished")


if __name__ == "__main__":
    main()
