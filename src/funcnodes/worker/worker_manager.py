import json
import time
import psutil
import funcnodes as fn
import os
import subprocess_monitor.defaults
import asyncio
import subprocess
import sys
from typing import List, Optional, Type, Any
from collections.abc import Callable
import threading
import weakref

import aiohttp
from aiohttp import (
    web,
    WSMsgType,
    ClientWebSocketResponse,
    ClientConnectorError,
)

from funcnodes_worker.worker import WorkerJson, WorkerState
import subprocess_monitor
import venvmngr

from funcnodes_worker.utils.messages import make_progress_message_string
from funcnodes.utils.cmd import build_worker_start, build_startworkermanager
from funcnodes_core.utils.files import write_json_secure

DEVMODE = int(os.environ.get("DEVELOPMENT_MODE", "0")) >= 1
if DEVMODE:
    pass

logger = fn.get_logger("worker_manager", propagate=False)


class ReturnValueThread(threading.Thread):
    """
    A thread class for returning values from a thread.
    """

    def __init__(
        self,
        target: Optional[Callable] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
    ) -> None:
        super().__init__(target=target, args=args or (), kwargs=kwargs or {})
        self.result: Any = None
        self.exception: Optional[Exception] = None

    def run(self):
        """
        Runs the target function in a new thread.

        Returns:
          None
        """
        if self._target is None:
            return
        try:
            self.result = self._target(*self._args, **self._kwargs)
        except Exception as exc:
            self.exception = exc

    def join(self, *args, **kwargs):
        """
        Waits for the thread to finish and returns the result of the target function.

        Returns:
          Any: The result of the target function.
        """
        #
        super().join(*args, **kwargs)
        if self.exception:
            raise self.exception
        return self.result


def run_in_new_process(*args, **kwargs):
    """
    Starts a new process with the given arguments.

    Args:
      *args (str): The arguments to pass to the new process.
      **kwargs (str): The keyword arguments to pass to the new process.

    Returns:
      subprocess.Popen: The new process.
    """
    logger.info(f"Starting new process: {' '.join(args)}")
    if os.name == "posix":
        p = subprocess.Popen(args, start_new_session=True)
    else:
        # Windows
        p = subprocess.Popen(
            args,
            creationflags=subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP,
            **kwargs,
        )
    return p


def create_worker_env(workerconfig: WorkerJson):
    """
    Creates a virtual environment for the worker and installs funcnodes.

    Args:
      workerconfig (WorkerJson): The worker configuration.

    Returns:
      None
    """
    # install env
    if not os.path.exists(workerconfig["env_path"]):
        os.makedirs(workerconfig["env_path"], exist_ok=True)
    command = [sys.executable, "-m", "venv", workerconfig["env_path"]]
    subprocess.run(command, check=True)

    if os.name == "nt":  # Windows
        pip_path = os.path.join(workerconfig["env_path"], "Scripts", "pip")
    else:  # Linux/macOS
        pip_path = os.path.join(workerconfig["env_path"], "bin", "pip")

    # purge pip cache
    command = [pip_path, "cache", "purge"]
    subprocess.run(
        command, check=True, cwd=os.path.join(workerconfig["data_path"], "..")
    )

    # install funcnodes
    command = [pip_path, "install", "funcnodes", "--upgrade"]
    subprocess.run(
        command, check=True, cwd=os.path.join(workerconfig["data_path"], "..")
    )


def start_worker(workerconfig: WorkerJson, debug=False):
    """
    Starts the worker process.

    Args:
      workerconfig (WorkerJson): The worker configuration.

    Returns:
      None
    """
    args = [
        sys.executable,
        "-m",
    ]
    args += build_worker_start(uuid=workerconfig["uuid"], debug=debug)

    if os.environ.get("SUBPROCESS_MONITOR_PORT", None) is not None:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            loop.run_until_complete(
                subprocess_monitor.send_spawn_request(
                    args[0],
                    args[1:],
                    env={},
                    port=int(os.environ["SUBPROCESS_MONITOR_PORT"]),
                )
            )
        else:
            loop.create_task(
                subprocess_monitor.send_spawn_request(
                    args[0],
                    args[1:],
                    env={},
                    port=int(os.environ["SUBPROCESS_MONITOR_PORT"]),
                )
            )
    else:
        run_in_new_process(*args)


async def check_worker(workerconfig: WorkerJson):
    """
    Checks if the worker is active.

    Args:
      workerconfig (WorkerJson): The worker configuration.

    Returns:
      Tuple[str, bool]: The worker UUID and whether the worker is active.
    """

    try:
        # initial check via the pid
        if "pid" in workerconfig and workerconfig["pid"] is not None:
            pid = int(workerconfig["pid"])
            if not psutil.pid_exists(pid):
                return workerconfig["uuid"], False
    except Exception:
        pass

    if "host" in workerconfig and "port" in workerconfig:
        # request uuid
        logger.debug(f"Checking worker {workerconfig['host']}:{workerconfig['port']}")
        protocol = (
            "wss" if fn.config.CONFIG["worker_manager"].get("ssl", False) else "ws"
        )
        url = f"{protocol}://{workerconfig['host']}:{workerconfig['port']}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url) as ws:
                    await asyncio.wait_for(
                        ws.send_str(json.dumps({"type": "cmd", "cmd": "uuid"})),
                        timeout=1,
                    )
                    resp = await asyncio.wait_for(ws.receive(), timeout=1)
                    if resp.type == WSMsgType.TEXT:
                        data = json.loads(resp.data)
                        if data["type"] == "result":
                            if workerconfig["uuid"] == data["result"]:
                                return workerconfig["uuid"], True
                            else:
                                raise KeyError(
                                    f"UUID mismatch: "
                                    f"{workerconfig['uuid']} != {data['result']}"
                                )
        except (
            ConnectionRefusedError,
            asyncio.TimeoutError,
            KeyError,
            json.JSONDecodeError,
            ClientConnectorError,
        ):
            pass

    return workerconfig["uuid"], False


def sync_check_worker(workerconfig: WorkerJson):
    """
    Synchronously checks if the worker is active.

    Args:
      workerconfig (WorkerJson): The worker configuration.

    Returns:
      Tuple[str, bool]: The worker UUID and whether the worker is active.
    """
    return asyncio.run(check_worker(workerconfig))


class WorkerManager:
    """
    This class is responsible for managing the workers.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        debug: bool = False,
    ):
        """
        Initializes the WorkerManager.

        Returns:
          None
        """
        if host is not None:
            fn.config.CONFIG["worker_manager"]["host"] = host
        if port is not None:
            fn.config.CONFIG["worker_manager"]["port"] = port

        self._worker_dir = os.path.join(fn.config.CONFIG_DIR, "workers")
        if not os.path.exists(self._worker_dir):
            os.makedirs(self._worker_dir)

        self._isrunninglock = threading.Lock()
        self._is_running = False
        self._connectionslock = threading.Lock()
        # Store each aiohttp WebSocketResponse using a weakref
        self._connections: List[weakref.ReferenceType[web.WebSocketResponse]] = []

        self._active_workers: List[WorkerJson] = []
        self._inactive_workers: List[WorkerJson] = []
        self._debug = debug
        if debug:
            logger.setLevel("DEBUG")

        self.app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._last_woker_check = 0

    @property
    def worker_dir(self):
        return self._worker_dir

    async def run_forever(self):
        """
        Runs the WorkerManager forever, serving WebSockets on the given host/port.
        """
        self.app = web.Application()

        # Route for the websocket endpoint at "/"
        self.app.router.add_get("/", self._handle_connection)

        self._runner = web.AppRunner(self.app)
        await self._runner.setup()

        protocol = (
            "wss" if fn.config.CONFIG["worker_manager"].get("ssl", False) else "ws"
        )
        host = fn.config.CONFIG["worker_manager"]["host"]
        port = fn.config.CONFIG["worker_manager"]["port"]

        self._site = web.TCPSite(self._runner, host, port)
        await self._site.start()

        logger.info("Worker manager started at %s://%s:%s", protocol, host, port)

        with self._isrunninglock:
            self._is_running = True

        def _stop():
            with self._isrunninglock:
                self._is_running = False

        # If running under a subprocess monitor, stop if parent dies
        if os.environ.get("SUBPROCESS_MONITOR_PORT", None) is not None:
            if not os.environ.get("SUBPROCESS_MONITOR_KEEP_RUNNING"):
                subprocess_monitor.call_on_manager_death(_stop)

        # Start background thread to periodically check workers
        asyncio.create_task(self._checking_worker_loop())

        # Main loop
        while self._is_running:
            await asyncio.sleep(0.5)
            # Remove dead references
            with self._connectionslock:
                self._connections = [c for c in self._connections if c() is not None]

            await self.check_shutdown()

    async def _handle_connection(self, request: web.Request):
        """
        Handles incoming WebSocket connections.
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Track connection
        with self._connectionslock:
            self._connections.append(weakref.ref(ws))
        logger.debug("New connection.")
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    message = msg.data
                    # Dispatch handling of this message
                    asyncio.create_task(self._handle_message(message, ws))
                elif msg.type == WSMsgType.ERROR:
                    logger.warning(
                        "WebSocket connection closed with error: %s", ws.exception()
                    )
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
                    break

        finally:
            # Remove from connections list
            with self._connectionslock:
                logger.debug("Removing connection.")
                self._connections = [
                    c for c in self._connections if c() is not None and c() != ws
                ]

        return ws

    async def _checking_worker_loop(self):
        while self._is_running:
            if time.time() - self._last_woker_check > 10 or self.worker_changed():
                await self.reload_workers()
                self._last_woker_check = time.time()
            await asyncio.sleep(1)

    async def _handle_message(self, message: str, ws: web.WebSocketResponse):
        """
        Handles incoming messages from a single WebSocket client.
        """
        logger.debug("Received message: %s", message)
        if message == "ping":
            return await ws.send_str("pong")

        if message == "identify":
            return await ws.send_str(
                json.dumps({"class": "WorkerManager", "py": sys.executable})
            )
        elif message == "stop":
            await self.set_progress_state(
                message="Stopping worker manager.",
                progress=1.0,
                blocking=False,
                status="info",
                websocket=ws,
            )
            return await self.stop()
        elif message == "worker_status":
            return await ws.send_str(
                json.dumps(
                    {
                        "type": "worker_status",
                        "active": self._active_workers,
                        "inactive": self._inactive_workers,
                    }
                )
            )
        elif message == "new_worker":
            # Create a new worker with default arguments
            new_w = await self.new_worker()
            if new_w:
                return await ws.send_str(
                    json.dumps({"type": "worker_created", "uuid": new_w.uuid()})
                )
            else:
                return
        else:
            # Possibly a JSON command
            try:
                msg = json.loads(message)
                if msg["type"] == "set_active":
                    return await self.activate_worker(msg["workerid"], ws)
                elif msg["type"] == "stop_worker":
                    return await self.stop_worker(msg["workerid"], ws)
                elif msg["type"] == "restart_worker":
                    await self.stop_worker(msg["workerid"], ws)
                    return await self.activate_worker(msg["workerid"], ws)
                elif msg["type"] == "new_worker":
                    # Extra kwargs for creation
                    new_w = await self.new_worker(**msg.get("kwargs", {}))
                    if new_w:
                        await ws.send_str(
                            json.dumps(
                                {
                                    "type": "worker_created",
                                    "uuid": new_w.uuid(),
                                }
                            )
                        )
                    return
            except json.JSONDecodeError:
                pass

            logger.warning(f"Unknown message: {message}")

    async def reset_progress_state(self, websocket: web.WebSocketResponse = None):
        """
        Resets the progress state.

        Returns:
          None

        Examples:
          >>> await reset_progress_state(websocket)
        """
        await self.set_progress_state(
            message="",
            progress=1,
            blocking=False,
            status="info",
            websocket=websocket,
        )

    async def set_progress_state(
        self,
        message,
        status="info",
        progress=0.0,
        blocking=False,
        websocket: web.WebSocketResponse = None,
    ):
        """
        Sets the progress state.

        Args:
          message (str): The message to display.
          status (str, optional): The status of the message. Defaults to "info".
          progress (float, optional): The progress value. Defaults to 0.0.
          blocking (bool, optional): Whether the message should block other messages. Defaults to False.
          websocket (WebSocketResponse, optional): The websocket connection. Defaults to None.

        Returns:
          None

        Examples:
          >>> await set_progress_state("Processing...", "info", 0.5, False, websocket)
        """
        msg = make_progress_message_string(
            message=message, status=status, progress=progress, blocking=blocking
        )
        if websocket is not None:
            try:
                await websocket.send_str(msg)
            except Exception:
                pass
        else:
            await self.broadcast(msg)

        await asyncio.sleep(0.05)

    async def stop(self):
        """
        Stops the worker manager.

        Returns:
          None

        Examples:
          >>> await stop()
        """
        if self._runner is not None:
            await self._runner.cleanup()
        with self._isrunninglock:
            self._is_running = False

    async def check_shutdown(self):
        """
        Checks if the worker manager should be shut down.

        Returns:
          None

        Examples:
          >>> await check_shutdown()
        """
        if os.path.exists(os.path.join(fn.config.CONFIG_DIR, "kill_worker_manager")):
            await self.stop()
            os.remove(os.path.join(fn.config.CONFIG_DIR, "kill_worker_manager"))

    def get_all_worker_files(self):
        jsonbases = set()
        processbases = set()
        for f in os.listdir(self.worker_dir):
            if f.startswith("worker_") and f.endswith(".json"):
                jsonbases.add(f[:-5])
            elif f.startswith("worker_") and f.endswith(".p"):
                processbases.add(f[:-2])

        processes_wo_json = processbases - jsonbases
        for p in processes_wo_json:
            try:
                os.remove(os.path.join(self.worker_dir, f"{p}.p"))
            except Exception:
                pass

        for j in jsonbases:
            yield j + ".json", j + ".p" if j in processbases else None

    def worker_changed(self):
        """
        Checks if the worker configuration has changed.

        Returns:
          bool: True if the worker configuration has changed, False otherwise.

        Examples:
          >>> worker_changed()
        """
        active_uuids = set([w["uuid"] for w in self._active_workers])
        active_files = set()
        inactive_files = set()
        for jsonf, pf in self.get_all_worker_files():
            if pf:
                active_files.add(pf.split("_", 1)[1].split(".")[0])
            else:
                inactive_files.add(jsonf.split("_", 1)[1].split(".")[0])

        if active_uuids != active_files:
            return True
        inactive_uuids = set([w["uuid"] for w in self._inactive_workers])
        if inactive_uuids != inactive_files:
            return True

        return False

    def get_all_workercfg(self) -> List[WorkerJson]:
        """
        Gets all worker configurations.

        Returns:
          List[WorkerJson]: A list of all worker configurations.

        Examples:
          >>> get_all_workercfg()
        """
        workerconfigs: List[WorkerJson] = []
        for jsonf, pf in self.get_all_worker_files():
            jsonfilepath = os.path.join(self.worker_dir, jsonf)
            with open(jsonfilepath, "r", encoding="utf-8") as file:
                try:
                    workerconfig: WorkerJson = json.load(file)
                except json.JSONDecodeError:
                    continue

            if workerconfig["type"] == "TestWorker":
                os.remove(jsonfilepath)
                continue

            if pf:
                pfile = os.path.join(self.worker_dir, pf)
                try:
                    with open(pfile, "rb") as file:
                        workerconfig["pid"] = int(file.read())
                except Exception:
                    workerconfig["pid"] = None

            workerconfigs.append(workerconfig)

        return workerconfigs

    async def reload_workers(self):
        """
        Reloads all workers.

        Returns:
          None

        Examples:
          >>> await reload_workers()
        """

        active_worker: List[WorkerJson] = []
        inactive_worker: List[WorkerJson] = []
        active_worker_ids: List[str] = []
        inactive_worker_ids: List[str] = []

        workerchecks = []
        workerconfigs = {}
        for workerconfig in self.get_all_workercfg():
            workerconfigs[workerconfig["uuid"]] = workerconfig
            pfile = os.path.join(self.worker_dir, f"worker_{workerconfig['uuid']}.p")
            if os.path.exists(pfile):
                for wc in self._inactive_workers:
                    if wc["uuid"] == workerconfig["uuid"]:
                        self._inactive_workers.remove(wc)
                self._active_workers.append(workerconfig)
            else:
                for wc in self._active_workers:
                    if wc["uuid"] == workerconfig["uuid"]:
                        self._active_workers.remove(wc)
                self._inactive_workers.append(workerconfig)

            thread = ReturnValueThread(target=sync_check_worker, args=(workerconfig,))
            workerchecks.append(thread)
            thread.start()

        while any(t.is_alive() for t in workerchecks):
            await asyncio.sleep(0.05)

        for t in workerchecks:
            try:
                res = t.join()
                if res is None:
                    continue
                if res[1]:
                    active_worker_ids.append(res[0])
                else:
                    inactive_worker_ids.append(res[0])
            except Exception as exc:
                logger.exception(exc)

        for iid in inactive_worker_ids:
            pfile = os.path.join(self.worker_dir, f"worker_{iid}.p")
            if os.path.exists(pfile):
                try:
                    os.remove(pfile)
                except Exception:
                    pass
            inactive_worker.append(workerconfigs[iid])

        for aid in active_worker_ids:
            active_worker.append(workerconfigs[aid])

        self._active_workers = active_worker
        self._inactive_workers = inactive_worker

        active_names = [
            f"{workerconfigs[uuid].get('name')}({uuid})" for uuid in active_worker_ids
        ]
        inactive_names = [
            f"{workerconfigs[uuid].get('name')}({uuid})" for uuid in inactive_worker_ids
        ]

        logger.info(
            "Active workers: %s\ninactive workers: %s",
            json.dumps(active_names, indent=2),
            json.dumps(inactive_names, indent=2),
        )

        await self.broadcast_worker_status()

    async def broadcast_worker_status(self):
        """
        Broadcasts the worker status to all connected websockets.

        Returns:
          None

        Examples:
          >>> await broadcast_worker_status()
        """

        await self.broadcast(
            json.dumps(
                {
                    "type": "worker_status",
                    "active": self._active_workers,
                    "inactive": self._inactive_workers,
                }
            )
        )

    async def broadcast(self, message: str):
        """
        Broadcasts a message to all connected WebSocket clients.
        """

        async def try_send(ws: web.WebSocketResponse, msg: str):
            try:
                await ws.send_str(msg)
            except Exception:
                pass

        with self._connectionslock:
            conns = [c() for c in self._connections]
            conns = [c for c in conns if c is not None]

        await asyncio.gather(*[try_send(ws, message) for ws in conns])

    async def stop_worker(self, workerid, websocket: web.WebSocketResponse = None):
        """
        Stops a worker.

        Args:
          workerid (str): The id of the worker to stop.
          websocket (WebSocketResponse): The websocket connection to send status updates to.

        Returns:
          None

        Examples:
          >>> await stop_worker("1234", websocket)
          None
        """
        logger.info("Stopping worker %s", workerid)
        target_worker = None
        for worker in self._active_workers:
            if worker["uuid"] == workerid:
                target_worker = worker
                break
        if target_worker is None:
            for worker in self._inactive_workers:
                if worker["uuid"] == workerid:
                    target_worker = worker
                    break

        if target_worker is None:
            return

        try:
            await self.set_progress_state(
                message="Stopping worker.",
                progress=0.1,
                blocking=True,
                status="info",
                websocket=websocket,
            )
            protocol = (
                "wss" if fn.config.CONFIG["worker_manager"].get("ssl", False) else "ws"
            )
            url = f"{protocol}://{target_worker['host']}:{target_worker['port']}"

            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url) as ws:
                    await asyncio.wait_for(
                        ws.send_str(json.dumps({"type": "cmd", "cmd": "stop_worker"})),
                        timeout=1,
                    )
                    response_msg = await asyncio.wait_for(ws.receive(), timeout=1)
                    if response_msg.type == WSMsgType.TEXT:
                        response = json.loads(response_msg.data)
                        if response.get("result") is True:
                            # Wait for it to actually stop
                            while workerid in [w["uuid"] for w in self._active_workers]:
                                await asyncio.sleep(0.5)
                                logger.debug("Waiting for worker to stop.")

        except Exception as e:
            raise e
        finally:
            self._last_woker_check = 0
            # await self.broadcast_worker_status() # already done in reload_workers
            await self.reset_progress_state(websocket=websocket)

    async def activate_worker(self, workerid, websocket: web.WebSocketResponse):
        """
        Activates a worker.

        Args:
          workerid (str): The id of the worker to activate.
          websocket (web.WebSocketResponse): The websocket connection to send status updates to.

        Returns:
          None

        Examples:
          >>> await activate_worker("1234", websocket)
          None
        """
        try:
            logger.info("Activating worker %s", workerid)
            await self.set_progress_state(
                message="Activating worker.",
                progress=0.1,
                blocking=True,
                status="info",
                websocket=websocket,
            )
            active_worker = None
            for worker in self._active_workers:
                if worker["uuid"] == workerid:
                    active_worker = worker

            if active_worker is None:
                for worker in self._inactive_workers:
                    if worker["uuid"] == workerid:
                        if worker["env_path"] is not None:
                            # check if abs or rel path
                            if not os.path.isabs(worker["env_path"]):
                                worker["env_path"] = os.path.abspath(
                                    os.path.join(self.worker_dir, worker["env_path"])
                                )

                            logger.info("Updating worker %s", workerid)
                            await self.set_progress_state(
                                message="Updating worker.",
                                progress=0.2,
                                blocking=True,
                                status="info",
                                websocket=websocket,
                            )
                            workerenv = venvmngr.UVVenvManager.get_virtual_env(
                                worker["env_path"]
                            )
                            update_on_startup = worker.get("update_on_startup", {})
                            if update_on_startup.get("funcnodes", True):
                                logger.info("Updating worker %s - funcnodes", workerid)
                                await self.set_progress_state(
                                    message="updating funcnodes",
                                    progress=0.3,
                                    blocking=True,
                                    status="info",
                                    websocket=websocket,
                                )
                                workerenv.install_package("funcnodes", upgrade=True)
                            if update_on_startup.get("funcnodes-core", True):
                                logger.info(
                                    "Updating worker %s - funcnodes-core", workerid
                                )
                                await self.set_progress_state(
                                    message="updating funcnodes-core",
                                    progress=0.3,
                                    blocking=True,
                                    status="info",
                                    websocket=websocket,
                                )
                                workerenv.install_package(
                                    "funcnodes-core", upgrade=True
                                )

                            for k, dep in worker["package_dependencies"].items():
                                if "package" in dep:
                                    if dep.get("version", None) is None:
                                        logger.info(
                                            "Updating worker %s - %s",
                                            workerid,
                                            dep["package"],
                                        )
                                        await self.set_progress_state(
                                            message="updating " + dep["package"],
                                            progress=0.3,
                                            blocking=True,
                                            status="info",
                                            websocket=websocket,
                                        )
                                        workerenv.install_package(
                                            dep["package"], upgrade=True
                                        )

                        await self.set_progress_state(
                            message="Starting worker.",
                            progress=0.4,
                            blocking=True,
                            status="info",
                            websocket=websocket,
                        )
                        start_worker(worker, debug=self._debug)
                        active_worker = worker

            if active_worker is None:
                return await websocket.send_str(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Worker with id {workerid} not found.",
                        }
                    )
                )

            # Try to contact the new worker
            workerconfigfile = os.path.join(
                self.worker_dir, f"worker_{active_worker['uuid']}.json"
            )
            await self.set_progress_state(
                message="Contacting worker.",
                progress=0.5,
                blocking=True,
                status="info",
                websocket=websocket,
            )

            protocol = (
                "wss" if fn.config.CONFIG["worker_manager"].get("ssl", False) else "ws"
            )
            for i in range(20):
                await self.set_progress_state(
                    message="Contacting worker.",
                    progress=0.5 + i * 0.02,
                    blocking=True,
                    status="info",
                    websocket=websocket,
                )
                if not os.path.exists(workerconfigfile):
                    await asyncio.sleep(0.5)
                    continue

                with open(workerconfigfile, "r", encoding="utf-8") as file:
                    workerconfig = json.load(file)

                if workerconfig["uuid"] != active_worker["uuid"]:
                    raise KeyError(
                        f"UUID mismatch: {workerconfig['uuid']} != {active_worker['uuid']}"
                    )

                url = f"{protocol}://{workerconfig['host']}:{workerconfig['port']}"
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.ws_connect(url) as wsc:
                            await asyncio.wait_for(
                                wsc.send_str(
                                    json.dumps({"type": "cmd", "cmd": "uuid"})
                                ),
                                timeout=1,
                            )
                            rmsg = await asyncio.wait_for(wsc.receive(), timeout=1)
                            if rmsg.type == WSMsgType.TEXT:
                                resp = json.loads(rmsg.data)
                                if resp["type"] == "result":
                                    if workerconfig["uuid"] != resp["result"]:
                                        raise KeyError(
                                            f"UUID mismatch: "
                                            f"{workerconfig['uuid']} != {resp['result']}"
                                        )
                                    return await websocket.send_str(
                                        json.dumps(
                                            {
                                                "type": "set_worker",
                                                "data": workerconfig,
                                            }
                                        )
                                    )
                except (
                    ConnectionRefusedError,
                    asyncio.TimeoutError,
                    KeyError,
                    json.JSONDecodeError,
                    ClientConnectorError,
                ):
                    await asyncio.sleep(0.5)
                    continue
                except Exception as e:
                    logger.exception(e)

            return await websocket.send_str(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Could not activate worker with id {workerid}.",
                    }
                )
            )
        except Exception as e:
            logger.exception(e)
            return await websocket.send_str(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Could not activate worker with id {workerid}.",
                    }
                )
            )
        finally:
            await self.reset_progress_state(websocket=websocket)

    async def new_worker(
        self,
        name: Optional[str] = None,
        reference: Optional[str] = None,
        copyLib: bool = False,
        copyNS: bool = False,
        uuid: Optional[str] = None,
        workertype: str = "WSWorker",
        in_venv: Optional[bool] = None,
    ):
        """
        Creates a new worker.

        Args:
          name (str): The name of the new worker.
          reference (str): The id of the worker to use as a reference.
          copyLib (bool): Whether to copy the libraries from the reference worker.
          copyNS (bool): Whether to copy the nodespace from the reference worker.

        Returns:
          None

        Examples:
          >>> await new_worker("MyWorker", "1234", True, False)
          None
        """
        logger.info("Creating new worker.")
        worker_class: Type[fn.worker.Worker] = getattr(fn.worker, workertype)
        logger.debug("Init Worker class: %s", worker_class)
        new_worker = worker_class(name=name, uuid=uuid)
        logger.debug("Init Worker config")
        await new_worker.ini_config()
        logger.debug("Stopping Worker")
        new_worker.stop()
        logger.debug("Write Worker config")
        c = new_worker.write_config()
        if name:
            c["name"] = name

        if in_venv is None:
            in_venv = os.environ.get("FUNCNODES_WORKER_IN_VENV", "1") in [
                "1",
                "True",
                "true",
                "yes",
                "Yes",
                "YES",
            ]

        if in_venv:
            logger.debug("using worker with venv")
            await self.set_progress_state(
                message="Making virtual environment.",
                progress=0.1,
                status="info",
                blocking=True,
            )

            workerenv, _ = venvmngr.UVVenvManager.get_or_create_virtual_env(
                new_worker.data_path / "pyproject.toml",
                python="3.11",
                description="A Funcnodes worker environment",
            )
            await self.set_progress_state(
                message="Adding funcnodes",
                progress=0.5,
                status="info",
                blocking=True,
            )

            workerenv.install_package("funcnodes", upgrade=True)
            c["python_path"] = str(workerenv.python_exe)
            c["env_path"] = str(workerenv.env_path)
        else:
            logger.debug("using worker global venv")
            c["python_path"] = sys.executable
            c["env_path"] = None

        logger.debug("Write config")
        ref_cfg = None
        if reference:
            for cfg in self.get_all_workercfg():
                if cfg["uuid"] == reference:
                    ref_cfg = cfg
                    break

        if ref_cfg:
            if copyLib:
                c["package_dependencies"] = ref_cfg["package_dependencies"]
            if copyNS:
                nsfile = os.path.join(ref_cfg["data_path"], "nodespace.json")
                if os.path.exists(nsfile):
                    with open(nsfile, "r", encoding="utf-8") as file:
                        ns: WorkerState = json.load(file)
                    nsd = dict(ns)
                    del nsd["meta"]
                nsfile = os.path.join(c["data_path"], "nodespace.json")
                write_json_secure(data=nsd, filepath=nsfile)
        await self.set_progress_state(
            message="Writing configuration.",
            progress=0.9,
            status="info",
            blocking=True,
        )

        new_worker.write_config(c)
        await self.set_progress_state(
            message="Creating new worker.",
            progress=1.0,
            status="info",
            blocking=True,
        )

        self._last_woker_check = 0
        logger.debug("Worker created")
        return new_worker


def start_worker_manager(
    host: Optional[str] = None,
    port: Optional[int] = None,
    debug: bool = False,
):
    """
    Starts the worker manager.

    Args:
      None

    Returns:
      None

    Examples:
      >>> start_worker_manager()
      None
    """

    wm = WorkerManager(host=host, port=port, debug=debug)
    asyncio.run(wm.run_forever())


class WorkerManagerConnection:
    """
    Represents a client connection to the WorkerManager using aiohttp.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        ssl: Optional[bool] = None,
    ):
        if host is None:
            host = fn.config.CONFIG["worker_manager"]["host"]
        if port is None:
            port = fn.config.CONFIG["worker_manager"]["port"]
        if ssl is None:
            ssl = fn.config.CONFIG["worker_manager"].get("ssl", False)

        self.protocol = "wss" if ssl else "ws"
        self.host = host
        self.port = port
        self._ws: Optional[ClientWebSocketResponse] = None

    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(self.url)
        return self._ws

    async def __aexit__(self, exc_type, exc_val, exc_tb):  # noqa: F841
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()

    async def ping(self, timeout=5):
        """
        Send a ping/pong test.
        """
        async with self as ws:
            await ws.send_str("ping")
            try:
                resp = await asyncio.wait_for(ws.receive(), timeout=timeout)
                if resp.type == WSMsgType.TEXT and resp.data == "pong":
                    return True
            except (asyncio.TimeoutError, ClientConnectorError):
                pass
        return False

    async def identify(self, timeout=5):
        """
        Identify that we're talking to the WorkerManager.
        """
        async with self as ws:
            await ws.send_str("identify")
            try:
                resp = await asyncio.wait_for(ws.receive(), timeout=timeout)
                if resp.type == WSMsgType.TEXT:
                    data = json.loads(resp.data)
                    if data.get("class") == "WorkerManager":
                        return data
            except (asyncio.TimeoutError, ClientConnectorError):
                pass
        raise ValueError("Could not identify WorkerManager.")


async def assert_worker_manager_running(
    retry_interval=1.0,
    termination_wait=10.0,
    max_retries=5,
    host: Optional[str] = None,
    port: Optional[int] = None,
    ssl: Optional[bool] = None,
    debug: bool = False,
) -> WorkerManagerConnection:
    """
    Build a connection to the worker manager and assert that it is running.
    If it is not running, start it in a new process.
    """
    p = None
    wsc = WorkerManagerConnection(host=host, port=port, ssl=ssl)

    logger.info("Trying to connect to worker manager at %s", wsc.url)
    for _ in range(max_retries):
        try:
            if await wsc.ping():
                if await wsc.identify():
                    return wsc
        except (ConnectionRefusedError, ClientConnectorError, ValueError):
            logger.info("Worker manager not running. Starting new worker manager.")
            # Terminate previous worker manager if any
            if p is not None:
                p.terminate()
                # Wait up to termination_wait seconds
                for _ in range(int(termination_wait * 10) + 1):
                    if p.poll() is not None:
                        break
                    await asyncio.sleep(0.1)
                if p.poll() is None:
                    p.kill()

            # Start worker manager in a new process or via subprocess_monitor
            args = [sys.executable, "-m"] + build_startworkermanager(
                host=host, port=port, debug=debug
            )
            if os.environ.get("SUBPROCESS_MONITOR_PORT", None) is not None:
                resp = await subprocess_monitor.send_spawn_request(
                    args[0],
                    args[1:],
                    port=int(os.environ["SUBPROCESS_MONITOR_PORT"]),
                    host=os.environ.get(
                        "SUBPROCESS_MONITOR_HOST",
                        subprocess_monitor.defaults.DEFAULT_HOST,
                    ),
                )
                pid = resp["pid"]
                asyncio.create_task(
                    subprocess_monitor.subscribe(
                        pid=pid,
                        port=int(os.environ["SUBPROCESS_MONITOR_PORT"]),
                        host=os.environ.get(
                            "SUBPROCESS_MONITOR_HOST",
                            subprocess_monitor.defaults.DEFAULT_HOST,
                        ),
                        callback=lambda x: logger.info("Worker manager: %s", x["data"]),
                    )
                )
            else:
                run_in_new_process(*args)

            await asyncio.sleep(retry_interval)
    else:
        raise ConnectionRefusedError("Could not connect to worker manager.")
