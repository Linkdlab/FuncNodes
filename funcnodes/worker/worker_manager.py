import json
import time
import funcnodes as fn
import os
import websockets
import asyncio
import subprocess
import sys
from typing import List, Optional, Type, Any
from collections.abc import Callable
import threading

from funcnodes.worker.worker import WorkerJson, WorkerState
import subprocess_monitor
import weakref
import venvmngr

from funcnodes.utils.messages import make_progress_message_string
from funcnodes.utils.cmd import build_worker_start, build_startworkermanager
from funcnodes.utils.files import write_json_secure

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
        """
        Initializes a new instance of the ReturnValueThread class.

        Args:
          *args: Variable length argument list.
          **kwargs: Arbitrary keyword arguments.
        """
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
    # For Windows
    else:
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
    else:  # Linux
        pip_path = os.path.join(workerconfig["env_path"], "bin", "pip")

    # purge pip cache
    command = [
        pip_path,
        "cache",
        "purge",
    ]
    subprocess.run(
        command, check=True, cwd=os.path.join(workerconfig["data_path"], "..")
    )

    # install funcnodes
    command = [
        pip_path,
        "install",
        "funcnodes",
        "--upgrade",
    ]
    subprocess.run(
        command, check=True, cwd=os.path.join(workerconfig["data_path"], "..")
    )


def update_worker_env(workerconfig: WorkerJson):
    if workerconfig["env_path"] is None:
        return
    workerenv = venvmngr.UVVenvManager.get_virtual_env(workerconfig["env_path"])

    update_on_startup = workerconfig.get("update_on_startup", {})
    if update_on_startup.get("funcnodes", True):
        workerenv.install_package("funcnodes", upgrade=True)
    if update_on_startup.get("funcnodes-core", True):
        workerenv.install_package("funcnodes-core", upgrade=True)


def start_worker(workerconfig: WorkerJson, debug=False):
    """
    Starts the worker process.

    Args:
      workerconfig (WorkerJson): The worker configuration.

    Returns:
      None
    """
    args = [
        workerconfig.get("python_path", sys.executable),
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
        run_in_new_process(
            *args,
        )


async def check_worker(workerconfig: WorkerJson):
    """
    Checks if the worker is active.

    Args:
      workerconfig (WorkerJson): The worker configuration.

    Returns:
      Tuple[str, bool]: The worker UUID and whether the worker is active.
    """

    if "host" in workerconfig and "port" in workerconfig:
        # reqest uuid
        logger.debug(f"Checking worker {workerconfig['host']}:{workerconfig['port']}")
        try:
            protocoll = (
                "wss" if fn.config.CONFIG["worker_manager"].get("ssl", False) else "ws"
            )
            async with websockets.connect(
                f"{protocoll}://{workerconfig['host']}:{workerconfig['port']}"
            ) as ws:
                # send with timeout

                await asyncio.wait_for(
                    ws.send(json.dumps({"type": "cmd", "cmd": "uuid"})),
                    timeout=1,
                )
                response = await asyncio.wait_for(ws.recv(), timeout=1)
                response = json.loads(response)
                if response["type"] == "result":
                    if workerconfig["uuid"] == response["result"]:
                        return workerconfig["uuid"], True
                    else:
                        raise KeyError(
                            f"UUID mismatch: {workerconfig['uuid']} != {response['result']}"
                        )

        except (
            ConnectionRefusedError,
            asyncio.TimeoutError,
            KeyError,
            json.JSONDecodeError,
            websockets.exceptions.WebSocketException,
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
        self._connections: List[
            weakref.ReferenceType[websockets.WebSocketServerProtocol]
        ] = []
        self._active_workers: List[WorkerJson] = []
        self._inactive_workers: List[WorkerJson] = []
        self._debug = debug
        if debug:
            logger.setLevel("DEBUG")

        self._checking_worker_thread = None

    @property
    def worker_dir(self):
        return self._worker_dir

    async def run_forever(self):
        """
        Runs the WorkerManager forever.

        Returns:
          None
        """
        self.ws_server = await websockets.serve(
            self._handle_connection,
            fn.config.CONFIG["worker_manager"]["host"],
            fn.config.CONFIG["worker_manager"]["port"],
        )
        protocoll = (
            "wss" if fn.config.CONFIG["worker_manager"].get("ssl", False) else "ws"
        )
        logger.info(
            "Worker manager started at %s://%s:%s",
            protocoll,
            fn.config.CONFIG["worker_manager"]["host"],
            fn.config.CONFIG["worker_manager"]["port"],
        )
        with self._isrunninglock:
            self._is_running = True

        def _stop():
            with self._isrunninglock:
                self._is_running = False

        if os.environ.get("SUBPROCESS_MONITOR_PORT", None) is not None:
            if not os.environ.get("SUBPROCESS_MONITOR_KEEP_RUNNING"):
                subprocess_monitor.call_on_manager_death(_stop)

        self._checking_worker_thread = threading.Thread(
            target=self._checking_worker_thread_fn, daemon=True
        )
        self._checking_worker_thread.start()

        while self._is_running:
            await asyncio.sleep(0.5)
            # remove dead references
            with self._connectionslock:
                self._connections = [
                    conn for conn in self._connections if conn() is not None
                ]

            await self.check_shutdown()

    def _checking_worker_thread_fn(self):
        l_rl = 0
        while self._is_running:
            t = time.time()
            if t - l_rl > 5 or self.worker_changed():
                asyncio.run(self.reload_workers())
                l_rl = t
            time.sleep(1)

    async def _handle_connection(
        self, websocket: websockets.WebSocketServerProtocol, *args, **kwargs
    ):
        """
        Handles a new connection to the WorkerManager.

        Args:
          websocket (websockets.WebSocketServerProtocol): The websocket connection.

        Returns:
          None
        """

        logger.debug("New connection: %s", websocket)
        with self._connectionslock:
            self._connections.append(weakref.ref(websocket))

        try:
            async for message in websocket:
                asyncio.create_task(self._handle_message(message, websocket))

            await websocket.close()
        except (websockets.exceptions.WebSocketException,):
            pass

        finally:
            with self._connectionslock:
                self._connections = [
                    conn
                    for conn in self._connections
                    if conn() is not None and conn() != websocket
                ]

    async def _handle_message(
        self, message: str, websocket: websockets.WebSocketServerProtocol
    ):
        """
        Handles incoming messages from the websocket.

        Args:
          message (str): The message received from the websocket.
          websocket (websockets.WebSocketServerProtocol): The websocket connection.

        Returns:
          None

        Examples:
          >>> await _handle_message("ping", websocket)
          "pong"
        """
        logger.debug("Received message: %s", message)
        if message == "ping":
            return await websocket.send("pong")
        if message == "identify":
            return await websocket.send(
                json.dumps(
                    {
                        "class": "WorkerManager",
                        "py": sys.executable,
                    }
                )
            )

        elif message == "stop":
            await self.set_progress_state(
                message="Stopping worker manager.",
                progress=1.0,
                blocking=False,
                status="info",
                websocket=websocket,
            )
            return await self.stop()
        elif message == "worker_status":
            return await websocket.send(
                json.dumps(
                    {
                        "type": "worker_status",
                        "active": self._active_workers,
                        "inactive": self._inactive_workers,
                    }
                )
            )
        elif message == "new_worker":
            return await self.new_worker()
        else:
            try:
                msg = json.loads(message)
                if msg["type"] == "set_active":
                    return await self.activate_worker(msg["workerid"], websocket)
                elif msg["type"] == "stop_worker":
                    return await self.stop_worker(msg["workerid"], websocket)
                elif msg["type"] == "restart_worker":
                    await self.stop_worker(msg["workerid"], websocket)
                    return await self.activate_worker(msg["workerid"], websocket)
                elif msg["type"] == "new_worker":
                    return await self.new_worker(**msg.get("kwargs", {}))

            except json.JSONDecodeError:
                pass

            logger.warning(f"Unknown message: {message}")

    async def reset_progress_state(
        self, websocket: websockets.WebSocketServerProtocol = None
    ):
        """
        Resets the progress state.

        Args:
          websocket (websockets.WebSocketServerProtocol, optional): The websocket connection. Defaults to None.

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
        websocket: websockets.WebSocketServerProtocol = None,
    ):
        """
        Sets the progress state.

        Args:
          message (str): The message to display.
          status (str, optional): The status of the message. Defaults to "info".
          progress (float, optional): The progress value. Defaults to 0.0.
          blocking (bool, optional): Whether the message should block other messages. Defaults to False.
          websocket (websockets.WebSocketServerProtocol, optional): The websocket connection. Defaults to None.

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
                await websocket.send(msg)
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

        if self.ws_server is not None:
            self.ws_server.close()
            await self.ws_server.wait_closed()
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
                active_files.add(pf.split("_")[1].split(".")[0])
            else:
                inactive_files.add(jsonf.split("_")[1].split(".")[0])

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
                    pass
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
        await self.broadcast_worker_status()

        while any([t.is_alive() for t in workerchecks]):
            await asyncio.sleep(0.1)

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
        Broadcasts a message to all connected workers.

        Args:
          message (str): The message to broadcast.

        Returns:
          None

        Examples:
          >>> await broadcast("Hello world!")
          None
        """

        async def try_send(conn, message):
            """
            Tries to send a message to a specific connection.

            Args:
              conn (websockets.WebSocketServerProtocol): The connection to send the message to.
              message (str): The message to send.

            Returns:
              None

            Examples:
              >>> await try_send(conn, "Hello world!")
              None
            """
            try:
                await conn.send(message)
            except Exception:
                pass

        with self._connectionslock:
            cons = [conn() for conn in self._connections]
            cons = [conn for conn in cons if conn is not None]
        await asyncio.gather(*[try_send(conn, message) for conn in cons])

    async def stop_worker(
        self, workerid, websocket: websockets.WebSocketServerProtocol = None
    ):
        """
        Stops a worker.

        Args:
          workerid (str): The id of the worker to stop.
          websocket (websockets.WebSocketServerProtocol): The websocket connection to send status updates to.

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

        try:
            if target_worker is None:
                return

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

            async with websockets.connect(
                f"{protocol}://{target_worker['host']}:{target_worker['port']}"
            ) as ws:
                # send with timeout

                await asyncio.wait_for(
                    ws.send(json.dumps({"type": "cmd", "cmd": "stop_worker"})),
                    timeout=1,
                )
                response = await asyncio.wait_for(ws.recv(), timeout=1)
                response = json.loads(response)
                if response.get("result") is True:
                    while workerid in [w["uuid"] for w in self._active_workers]:
                        await asyncio.sleep(0.5)
                        logger.debug("Waiting for worker to stop.")

        except Exception:
            raise
        finally:
            await self.reload_workers()
            await self.broadcast_worker_status()

            await self.reset_progress_state(
                websocket=websocket,
            )

    async def activate_worker(
        self, workerid, websocket: websockets.WebSocketServerProtocol
    ):
        """
        Activates a worker.

        Args:
          workerid (str): The id of the worker to activate.
          websocket (websockets.WebSocketServerProtocol): The websocket connection to send status updates to.

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
                return await websocket.send(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Worker with id {workerid} not found.",
                        }
                    )
                )

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
                try:
                    protocol = (
                        "wss"
                        if fn.config.CONFIG["worker_manager"].get("ssl", False)
                        else "ws"
                    )
                    async with websockets.connect(
                        f"{protocol}://{workerconfig['host']}:{workerconfig['port']}"
                    ) as ws:
                        # send with timeout

                        await asyncio.wait_for(
                            ws.send(json.dumps({"type": "cmd", "cmd": "uuid"})),
                            timeout=1,
                        )
                        response = await asyncio.wait_for(ws.recv(), timeout=1)
                        response = json.loads(response)
                        if response["type"] == "result":
                            if workerconfig["uuid"] != response["result"]:
                                raise KeyError(
                                    f"UUID mismatch: {workerconfig['uuid']} != {response['result']}"
                                )
                            return await websocket.send(
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
                    websockets.exceptions.WebSocketException,
                ):
                    await asyncio.sleep(0.5)
                    continue
                except Exception as e:
                    logger.exception(e)

            return await websocket.send(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Could not activate worker with id {workerid}.",
                    }
                )
            )
        except Exception as e:
            logger.exception(e)
            return await websocket.send(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Could not activate worker with id {workerid}.",
                    }
                )
            )
        finally:
            await self.reset_progress_state(
                websocket=websocket,
            )

    async def new_worker(
        self,
        name: str = None,
        reference: str = None,
        copyLib: bool = False,
        copyNS: bool = False,
        uuid: str = None,
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
        worker_class: Type[fn.worker.Worker] = getattr(fn.worker, workertype)

        new_worker = worker_class(name=name, uuid=uuid)
        await new_worker.ini_config()
        new_worker.stop()
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
            # craete env
            workerenv, new = venvmngr.UVVenvManager.get_or_create_virtual_env(
                new_worker.data_path / "pyproject.toml"
            )
            workerenv.install_package("funcnodes", upgrade=True)
            c["python_path"] = str(workerenv.python_exe)
            c["env_path"] = str(workerenv.env_path)
        else:
            c["python_path"] = sys.executable
            c["env_path"] = None
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

        new_worker.write_config(c)
        await self.reload_workers()
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

        protocol = "wss" if ssl else "ws"

        self.host = host
        self.port = port
        self.protocol = protocol
        self._ws: Optional[websockets.ClientConnection] = None

    async def __aenter__(self):
        self._ws = await websockets.connect(
            f"{self.protocol}://{self.host}:{self.port}"
        )
        return self._ws

    async def __aexit__(
        self,
        exc_type,  # noqa: F841
        exc_value,  # noqa: F841
        traceback,  # noqa: F841
    ):
        if self._ws:
            await self._ws.close()

    async def ping(self, timeout=5):
        async with self as ws:
            # healtch check via ping pong
            await ws.send("ping")
            async with asyncio.timeout(timeout):
                response = await ws.recv()
                if response == "pong":
                    return True
        return False

    async def identify(self, timeout=5):
        async with self as ws:
            # healtch check via ping pong
            await ws.send("identify")
            async with asyncio.timeout(timeout):
                response = json.loads(await ws.recv())
                if response["class"] == "WorkerManager":
                    return response
        raise ValueError("Could not identify")


async def assert_worker_manager_running(
    retry_interval=1.0,
    termination_wait=10.0,
    max_retries=5,
    host: Optional[str] = None,
    port: Optional[int] = None,
    ssl: Optional[bool] = None,
) -> WorkerManagerConnection:
    """
    build a connection to the worker manager and assert that it is running.
    If it is not running, start it in a new process.
    """

    p = None

    wsc = WorkerManagerConnection(host=host, port=port, ssl=ssl)
    logger.info(
        "Trying to connect to worker manager at %s://%s:%s",
        wsc.protocol,
        wsc.host,
        wsc.port,
    )
    for i in range(max_retries):
        try:
            if await wsc.ping():
                if await wsc.identify():
                    return wsc
        except ConnectionRefusedError:
            logger.info("Worker manager not running. Starting new worker manager.")

            if p is not None:
                # terminate previous worker manager
                p.terminate()

                # wait max 5 seconds for termination
                for j in range(int(termination_wait * 10) + 1):
                    if p.poll() is not None:
                        break
                    await asyncio.sleep(0.1)

                if p.poll() is None:
                    p.kill()
            # start worker manager in a new

            args = [
                sys.executable,
                "-m",
            ] + build_startworkermanager(host=host, port=port)
            p = run_in_new_process(*args)

            await asyncio.sleep(retry_interval)
    else:
        raise ConnectionRefusedError("Could not connect to worker manager.")
