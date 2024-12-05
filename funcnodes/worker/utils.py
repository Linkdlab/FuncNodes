import os
import sys
from typing import Optional, Dict, Any, Callable, Union, Type
import psutil
import subprocess_monitor
from subprocess_monitor.types import StreamingLineOutput
from funcnodes.utils.asyncutils import async_to_sync
from funcnodes.worker import Worker


async def start_worker_via_subprocess_monitor(
    uuid,
    port: Optional[int] = None,
    workertype: Optional[str] = None,
    host: Optional[str] = None,
    subscription_callback: Optional[Callable[[StreamingLineOutput], None]] = None,
):
    if port is None:
        if (
            "SUBPROCESS_MONITOR_PORT" not in os.environ
            or "SUBPROCESS_MONITOR_PID" not in os.environ
        ):
            raise Exception("Subprocess monitor not running")
        if not psutil.pid_exists(int(os.environ["SUBPROCESS_MONITOR_PID"])):
            raise Exception("Subprocess monitor not running")
        port = int(os.environ["SUBPROCESS_MONITOR_PORT"])

    args = [
        "-m",
        "funcnodes",
        "worker",
        "start",
        "--uuid",
        uuid,
    ]
    if workertype is not None:
        args.extend(["--workertype", workertype])

    subprocess_kwargs: Dict[str, Any] = {
        "port": port,
    }
    if host is not None:
        subprocess_kwargs["host"] = host
    resp = await subprocess_monitor.send_spawn_request(
        sys.executable, args, **subprocess_kwargs
    )

    if subscription_callback is not None and resp["status"] == "success":
        await subprocess_monitor.subscribe(
            pid=resp["pid"], **subprocess_kwargs, callback=subscription_callback
        )

    return resp


sync_start_worker_via_subprocess_monitor = async_to_sync(
    start_worker_via_subprocess_monitor
)


async def spawn_worker_via_subprocess_monitor(
    uuid: str,
    port: Optional[int] = None,
    workertype: Union[str, Type[Worker], None] = None,
    host: Optional[str] = None,
    subscription_callback: Optional[Callable[[StreamingLineOutput], None]] = None,
):
    if port is None:
        if (
            "SUBPROCESS_MONITOR_PORT" not in os.environ
            or "SUBPROCESS_MONITOR_PID" not in os.environ
        ):
            raise Exception("Subprocess monitor not running")
        if not psutil.pid_exists(int(os.environ["SUBPROCESS_MONITOR_PID"])):
            raise Exception("Subprocess monitor not running")
        port = int(os.environ["SUBPROCESS_MONITOR_PORT"])

    args = [
        "-m",
        "funcnodes",
        "worker",
        "new",
        "--uuid",
        uuid,
        "--create-only",
    ]
    if workertype is not None:
        if isinstance(workertype, type):
            workertype = workertype.__name__
        args.extend(["--workertype", workertype])
    subprocess_kwargs: Dict[str, Any] = {
        "port": port,
    }
    if host is not None:
        subprocess_kwargs["host"] = host
    resp = await subprocess_monitor.send_spawn_request(
        sys.executable, args, **subprocess_kwargs
    )

    if subscription_callback is not None and resp["status"] == "success":
        await subprocess_monitor.subscribe(
            pid=resp["pid"], **subprocess_kwargs, callback=subscription_callback
        )

    return resp


sync_spawn_worker_via_subprocess_monitor = async_to_sync(
    spawn_worker_via_subprocess_monitor
)
