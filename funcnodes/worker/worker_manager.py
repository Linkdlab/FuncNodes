import json
import time
import funcnodes as fn
import os
import websockets
import asyncio
import subprocess
import sys
from typing import List, Optional, Type
import threading

from funcnodes.worker.worker import WorkerJson, WorkerState
import subprocess_monitor
import venvmngr

DEVMODE = int(os.environ.get("DEVELOPMENT_MODE", "0")) >= 1

if DEVMODE:
    pass


class ReturnValueThread(threading.Thread):
    """
    A thread class for returning values from a thread.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes a new instance of the ReturnValueThread class.

        Args:
          *args: Variable length argument list.
          **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.result = None

    def run(self):
        """
        Runs the target function in a new thread.

        Returns:
          None
        """
        if self._target is None:
            return  # could alternatively raise an exception, depends on the use case
        try:
            self.result = self._target(*self._args, **self._kwargs)
        except Exception as exc:
            fn.FUNCNODES_LOGGER.exception(exc)

    def join(self, *args, **kwargs):
        """
        Waits for the thread to finish and returns the result of the target function.

        Returns:
          Any: The result of the target function.
        """
        super().join(*args, **kwargs)
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
    fn.FUNCNODES_LOGGER.info(f"Starting new process: {' '.join(args)}")
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


def start_worker(workerconfig: WorkerJson, debug=False):
    """
    Starts the worker process.

    Args:
      workerconfig (WorkerJson): The worker configuration.

    Returns:
      None
    """
    args = [
        workerconfig["python_path"],
        "-m",
        "funcnodes",
        "worker",
        "start",
        f"--uuid={workerconfig['uuid']}",
    ]
    if debug:
        args.append("--debug")

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


#


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
        fn.FUNCNODES_LOGGER.info(
            f"Checking worker {workerconfig['host']}:{workerconfig['port']}"
        )
        try:
            async with websockets.connect(
                f"ws{'s' if workerconfig.get('ssl',False) else ''}://{workerconfig['host']}:{workerconfig['port']}"
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
        self._connections: List[websockets.WebSocketServerProtocol] = []
        self._active_workers: List[WorkerJson] = []
        self._inactive_workers: List[WorkerJson] = []
        self._debug = debug
        if debug:
            fn.FUNCNODES_LOGGER.setLevel("DEBUG")

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
        fn.FUNCNODES_LOGGER.info(
            f"Worker manager started at ws{'s' if fn.config.CONFIG['worker_manager'].get('ssl',False) else ''}://%s:%s",
            fn.config.CONFIG["worker_manager"]["host"],
            fn.config.CONFIG["worker_manager"]["port"],
        )
        with self._isrunninglock:
            self._is_running = True
        l_rl = 0

        def _stop():
            with self._isrunninglock:
                self._is_running = False

        if os.environ.get("SUBPROCESS_MONITOR_PORT", None) is not None:
            if not os.environ.get("SUBPROCESS_MONITOR_KEEP_RUNNING"):
                subprocess_monitor.call_on_manager_death(_stop)

        while self._is_running:
            await asyncio.sleep(0.5)
            for conn in self._connections:
                if conn.closed:
                    self._connections.remove(conn)

            t = time.time()
            await self.check_shutdown()

            if t - l_rl > 20 or self.worker_changed():
                await self.reload_workers()
                l_rl = t

        await self.stop()

    async def _handle_connection(
        self, websocket: websockets.WebSocketServerProtocol, path
    ):
        """
        Handles a new connection to the WorkerManager.

        Args:
          websocket (websockets.WebSocketServerProtocol): The websocket connection.
          path (str): The path of the connection.

        Returns:
          None
        """
        fn.FUNCNODES_LOGGER.debug("New connection: %s", websocket)
        self._connections.append(websocket)
        try:
            async for message in websocket:
                await self._handle_message(message, websocket)
        except (websockets.exceptions.WebSocketException,):
            pass
        finally:
            if websocket in self._connections:
                self._connections.remove(websocket)

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
        fn.FUNCNODES_LOGGER.debug("Received message: %s", message)
        if message == "ping":
            return await websocket.send("pong")
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

            fn.FUNCNODES_LOGGER.warning(f"Unknown message: {message}")

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
        msg = json.dumps(
            {
                "type": "progress",
                "message": message,
                "status": status,
                "progress": progress,
                "blocking": blocking,
            }
        )
        if websocket is not None:
            await websocket.send(msg)
        else:
            await self.broadcast(msg)

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
        for f in os.listdir(self.worker_dir):
            if f.startswith("worker_") and f.endswith(".p"):
                if not os.path.exists(os.path.join(self.worker_dir, f[:-2] + ".json")):
                    continue
                active_files.add(f.split("_")[1].split(".")[0])

        if active_uuids != active_files:
            return True

        inactive_uuids = set([w["uuid"] for w in self._inactive_workers])

        inactive_files = set(
            [
                f.split("_")[1].split(".")[0]
                for f in os.listdir(self.worker_dir)
                if f.startswith("worker_") and f.endswith(".json")
            ]
        )
        inactive_files = inactive_files - active_files

        if inactive_uuids != inactive_files:
            return True
        return False

    def get_all_workercfg(self):
        """
        Gets all worker configurations.

        Returns:
          List[WorkerJson]: A list of all worker configurations.

        Examples:
          >>> get_all_workercfg()
        """
        workerconfigs: List[WorkerJson] = []
        for f in os.listdir(self.worker_dir):
            if f.startswith("worker_") and f.endswith(".json"):
                with open(
                    os.path.join(self.worker_dir, f), "r", encoding="utf-8"
                ) as file:
                    try:
                        workerconfig: WorkerJson = json.load(file)
                    except json.JSONDecodeError:
                        continue
                if workerconfig["type"] == "TestWorker":
                    os.remove(os.path.join(self.worker_dir, f))
                    continue

                pfile = os.path.join(
                    self.worker_dir, f"worker_{workerconfig['uuid']}.p"
                )
                if os.path.exists(pfile):
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
            res = t.join()
            if res is None:
                continue

            if res[1]:
                active_worker_ids.append(res[0])
            else:
                inactive_worker_ids.append(res[0])

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
        joined_names = "\n".join(active_names)

        inactive_names = [
            f"{workerconfigs[uuid].get('name')}({uuid})" for uuid in inactive_worker_ids
        ]
        joined_names = "\n  ".join(inactive_names)
        fn.FUNCNODES_LOGGER.info(
            f"Active workers: [\n{joined_names}\n  ]\ninactive workers:[\n{joined_names}\n  ]"
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

        await asyncio.gather(*[try_send(conn, message) for conn in self._connections])

    async def stop_worker(
        self, workerid, websocket: websockets.WebSocketServerProtocol
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
        await self.set_progress_state(
            message="Stopping worker.",
            progress=0.1,
            blocking=True,
            status="info",
            websocket=websocket,
        )
        fn.FUNCNODES_LOGGER.info("Stopping worker %s", workerid)
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
            async with websockets.connect(
                f"ws{'s' if target_worker.get('ssl',False) else ''}://"
                f"{target_worker['host']}:{target_worker['port']}"
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
                        fn.FUNCNODES_LOGGER.debug("Waiting for worker to stop.")

                await self.reload_workers()

        except Exception:
            raise

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
            fn.FUNCNODES_LOGGER.info("Activating worker %s", workerid)
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
                message="Activating worker.",
                progress=0.5,
                blocking=True,
                status="info",
                websocket=websocket,
            )
            for i in range(20):
                await self.set_progress_state(
                    message="Activating worker.",
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
                    async with websockets.connect(
                        f"ws{'s' if workerconfig.get('ssl',False) else ''}://"
                        f"{workerconfig['host']}:{workerconfig['port']}"
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
                ):
                    await asyncio.sleep(0.5)
                    continue
                except Exception as e:
                    fn.FUNCNODES_LOGGER.exception(e)

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
        new_worker.ini_config()
        new_worker.stop()
        c = new_worker.write_config()
        if name:
            c["name"] = name

        # craete env
        workerenv, new = venvmngr.get_or_create_virtual_env(
            os.path.join(new_worker.data_path, "env")
        )
        workerenv.install_package("funcnodes", upgrade=True)
        c["python_path"] = workerenv.python_exe
        c["env_path"] = workerenv.env_path

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
                with open(nsfile, "w", encoding="utf-8") as file:
                    json.dump(nsd, file, indent=4)
        new_worker.write_config(c)
        await self.reload_workers()
        return new_worker

    # def start_worker(workerconfig):
    #     subprocess.Popen(
    #         [
    #             sys.executable,
    #             os.path.join(fn.__path__[0], "worker", "worker.py"),
    #             workerconfig["host"],
    #             str(workerconfig["port"]),
    #         ]
    #     )


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
    asyncio.run(WorkerManager(host=host, port=port, debug=debug).run_forever())


async def assert_worker_manager_running(
    retry_interval=1.0,
    termination_wait=10.0,
    max_retries=5,
    host: Optional[str] = None,
    port: Optional[int] = None,
    ssl: Optional[bool] = None,
):
    """
    build a connection to the worker manager and assert that it is running.
    If it is not running, start it in a new process.
    """

    if host is None:
        host = fn.config.CONFIG["worker_manager"]["host"]
    if port is None:
        port = fn.config.CONFIG["worker_manager"]["port"]
    if ssl is None:
        ssl = fn.config.CONFIG["worker_manager"].get("ssl", False)

    p = None
    for i in range(max_retries):
        try:
            fn.FUNCNODES_LOGGER.info(
                f"Trying to connect to worker manager at ws{'s' if ssl else ''}://{host}:{port}"
            )
            async with websockets.connect(
                f"ws{'s' if ssl else ''}://{host}:{port}"
            ) as ws:
                # healtch check via ping pong
                await ws.send("ping")
                response = await ws.recv()
                if response == "pong":
                    break
        except ConnectionRefusedError:
            fn.FUNCNODES_LOGGER.info(
                "Worker manager not running. Starting new worker manager."
            )

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

            # start worker manager in a new process
            p = run_in_new_process(
                sys.executable,
                "-m",
                "funcnodes",
                "startworkermanager",
                "--host",
                host,
                "--port",
                str(port),
            )

            await asyncio.sleep(retry_interval)
    else:
        raise ConnectionRefusedError("Could not connect to worker manager.")
    fn.FUNCNODES_LOGGER.info("Connected to worker manager.")
    return True
