import json
import time
import funcnodes as fn
import os
import websockets
import asyncio
import subprocess
import sys
from typing import List
from funcnodes.worker.websocket import WSWorker
import threading

from funcnodes.worker.worker import WorkerJson

DEVMODE = int(os.environ.get("DEVELOPMENT_MODE", "0")) >= 1

if DEVMODE:
    import shutil


class ReturnValueThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = None

    def run(self):
        if self._target is None:
            return  # could alternatively raise an exception, depends on the use case
        try:
            self.result = self._target(*self._args, **self._kwargs)
        except Exception as exc:
            print(
                f"{type(exc).__name__}: {exc}", file=sys.stderr
            )  # properly handle the exception

    def join(self, *args, **kwargs):
        super().join(*args, **kwargs)
        return self.result


def run_in_new_process(*args, **kwargs):
    print(f"Starting new process: {' '.join(args)}")
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


def start_worker(workerconfig: WorkerJson):

    create_worker_env(workerconfig)

    if os.name == "nt":  # Windows
        pypath = os.path.join(workerconfig["env_path"], "Scripts", "python")
    else:  # Linux
        pypath = os.path.join(workerconfig["env_path"], "bin", "python")

    # print funcnodes location

    print(f"Funcnodes location: {fn.__path__[0]} {DEVMODE}")
    if DEVMODE:
        ## if in development mode, copy the current funcnodes to the worker env
        fn.FUNCNODES_LOGGER.info(
            f"Copying funcnodes to worker env {workerconfig['env_path']}"
        )

        if os.name == "nt":
            packedir = os.path.join(workerconfig["env_path"], "Lib", "site-packages")
        else:
            packedir = os.path.join(workerconfig["env_path"], "lib", "site-packages")

        funcnodesdir = os.path.join(packedir, "funcnodes")

        shutil.copytree(fn.__path__[0], funcnodesdir, dirs_exist_ok=True)

        # run poetry install in the worker env
        subprocess.run(
            [pypath, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True,
            cwd=os.path.join(fn.__path__[0], ".."),
        )

    run_in_new_process(
        pypath,
        "-m",
        "funcnodes",
        "startworker",
        f"--uuid={workerconfig['uuid']}",
        #  cwd=os.path.join(workerconfig["data_path"], ".."),
    )


#


async def check_worker(workerconfig: WorkerJson):
    active_worker: List[str] = []
    inactive_worker: List[str] = []
    if "host" in workerconfig and "port" in workerconfig:
        # reqest uuid
        print(f"Checking worker {workerconfig['host']}:{workerconfig['port']}")
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
        ) as e:
            pass

    return workerconfig["uuid"], False


def sync_check_worker(workerconfig: WorkerJson):
    return asyncio.run(check_worker(workerconfig))


class WorkerManager:
    def __init__(
        self,
    ):
        self._worker_dir = os.path.join(fn.config.CONFIG_DIR, "workers")
        if not os.path.exists(self._worker_dir):
            os.makedirs(self._worker_dir)
        self._is_running = False
        self._connections: List[websockets.WebSocketServerProtocol] = []
        self._active_workers: List[WorkerJson] = []
        self._inactive_workers: List[WorkerJson] = []

    async def run_forever(self):
        self.ws_server = await websockets.serve(
            self._handle_connection,
            fn.config.CONFIG["worker_manager"]["host"],
            fn.config.CONFIG["worker_manager"]["port"],
        )
        fn.FUNCNODES_LOGGER.info(
            f"Worker manager started at ws://{fn.config.CONFIG['worker_manager']['host']}:{fn.config.CONFIG['worker_manager']['port']}"
        )
        self._is_running = True
        l_rl = 0
        while self._is_running:
            await asyncio.sleep(1)
            for conn in self._connections:
                if conn.closed:
                    self._connections.remove(conn)

            t = time.time()
            await self.check_shutdown()

            # print("Checking workers", self.worker_changed())
            if t - l_rl > 20 or self.worker_changed():
                await self.reload_workers()
                l_rl = t

    async def _handle_connection(
        self, websocket: websockets.WebSocketServerProtocol, path
    ):
        fn.FUNCNODES_LOGGER.debug(f"New connection: {websocket}")
        self._connections.append(websocket)
        async for message in websocket:
            await self._handle_message(message, websocket)
        self._connections.remove(websocket)

    async def _handle_message(
        self, message: str, websocket: websockets.WebSocketServerProtocol
    ):
        fn.FUNCNODES_LOGGER.debug(f"Received message: {message}")
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

            except json.JSONDecodeError as e:
                pass

            print(f"Unknown message: {message}")

    async def reset_progress_state(
        self, websocket: websockets.WebSocketServerProtocol = None
    ):
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

        if self.ws_server is not None:
            self.ws_server.close()
            await self.ws_server.wait_closed()
        self._is_running = False

    async def check_shutdown(self):
        if os.path.exists(os.path.join(fn.config.CONFIG_DIR, "kill_worker_manager")):
            await self.stop()
            os.remove(os.path.join(fn.config.CONFIG_DIR, "kill_worker_manager"))

    def worker_changed(self):
        active_uuids = set([w["uuid"] for w in self._active_workers])
        active_files = set()
        for f in os.listdir(self._worker_dir):
            if f.startswith("worker_") and f.endswith(".p"):
                if not os.path.exists(os.path.join(self._worker_dir, f[:-2] + ".json")):
                    continue
                active_files.add(f.split("_")[1].split(".")[0])

        if active_uuids != active_files:
            return True

        inactive_uuids = set([w["uuid"] for w in self._inactive_workers])

        inactive_files = set(
            [
                f.split("_")[1].split(".")[0]
                for f in os.listdir(self._worker_dir)
                if f.startswith("worker_") and f.endswith(".json")
            ]
        )
        inactive_files = inactive_files - active_files

        if inactive_uuids != inactive_files:
            return True
        return False

    async def reload_workers(self):
        active_worker: List[WorkerJson] = []
        inactive_worker: List[WorkerJson] = []
        active_worker_ids: List[WorkerJson] = []
        inactive_worker_ids: List[WorkerJson] = []

        workerchecks = []
        workerconfigs = {}
        for f in os.listdir(self._worker_dir):
            if f.startswith("worker_") and f.endswith(".json"):
                with open(
                    os.path.join(self._worker_dir, f), "r", encoding="utf-8"
                ) as file:
                    try:
                        workerconfig: WorkerJson = json.load(file)
                    except json.JSONDecodeError:
                        continue
                if workerconfig["type"] == "TestWorker":
                    os.remove(os.path.join(self._worker_dir, f))
                    continue

                workerconfigs[workerconfig["uuid"]] = workerconfig

                thread = ReturnValueThread(
                    target=sync_check_worker, args=(workerconfig,)
                )
                workerchecks.append(thread)
                thread.start()

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
            pfile = os.path.join(self._worker_dir, f"worker_{iid}.p")
            if os.path.exists(pfile):
                os.remove(pfile)
            inactive_worker.append(workerconfigs[iid])

        for aid in active_worker_ids:
            active_worker.append(workerconfigs[aid])

        self._active_workers = active_worker
        self._inactive_workers = inactive_worker
        print(f"Active workers: {active_worker_ids}")
        print(f"inactive workers: {inactive_worker_ids}")

        await self.broadcast(
            json.dumps(
                {
                    "type": "worker_status",
                    "active": active_worker,
                    "inactive": inactive_worker,
                }
            )
        )

    async def broadcast(self, message: str):
        async def try_send(conn, message):
            try:
                await conn.send(message)
            except Exception:
                pass

        await asyncio.gather(*[try_send(conn, message) for conn in self._connections])

    async def stop_worker(
        self, workerid, websocket: websockets.WebSocketServerProtocol
    ):
        await self.set_progress_state(
            message="Stopping worker.",
            progress=0.1,
            blocking=True,
            status="info",
            websocket=websocket,
        )
        fn.FUNCNODES_LOGGER.info(f"Stopping worker {workerid}")
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
                f"ws{'s' if target_worker.get('ssl',False) else ''}://{target_worker['host']}:{target_worker['port']}"
            ) as ws:
                # send with timeout

                await asyncio.wait_for(
                    ws.send(json.dumps({"type": "cmd", "cmd": "stop_worker"})),
                    timeout=1,
                )
                response = await asyncio.wait_for(ws.recv(), timeout=1)
                response = json.loads(response)
                if response["result"] is True:
                    while workerid in [w["uuid"] for w in self._active_workers]:
                        await asyncio.sleep(0.5)
                        print("Waiting for worker to stop.")
        except Exception:
            pass

        await self.reset_progress_state(
            websocket=websocket,
        )

    async def activate_worker(
        self, workerid, websocket: websockets.WebSocketServerProtocol
    ):
        try:
            fn.FUNCNODES_LOGGER.info(f"Activating worker {workerid}")
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
                        start_worker(worker)
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
                self._worker_dir, f"worker_{active_worker['uuid']}.json"
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

    async def new_worker(self):
        new_worker = WSWorker()
        new_worker.ini_config()
        new_worker.stop()
        await self.reload_workers()

    # def start_worker(workerconfig):
    #     subprocess.Popen(
    #         [
    #             sys.executable,
    #             os.path.join(fn.__path__[0], "worker", "worker.py"),
    #             workerconfig["host"],
    #             str(workerconfig["port"]),
    #         ]
    #     )


def start_worker_manager():
    asyncio.run(WorkerManager().run_forever())


async def assert_worker_manager_running(retry_interval=1.0, max_retries=5):
    """
    build a connection to the worker manager and assert that it is running.
    If it is not running, start it in a new process.
    """

    for i in range(max_retries):
        try:
            print(
                f"Trying to connect to worker manager at ws://{fn.config.CONFIG['worker_manager']['host']}:{fn.config.CONFIG['worker_manager']['port']}"
            )
            async with websockets.connect(
                f"ws://{fn.config.CONFIG['worker_manager']['host']}:{fn.config.CONFIG['worker_manager']['port']}"
            ) as ws:
                ## healtch check via ping pong
                await ws.send("ping")
                response = await ws.recv()
                if response == "pong":
                    break
        except ConnectionRefusedError:
            print("Worker manager not running. Starting new worker manager.")
            ### start worker manager in a new process
            run_in_new_process(sys.executable, __file__)

            await asyncio.sleep(retry_interval)
    else:
        raise ConnectionRefusedError("Could not connect to worker manager.")
    print("Connected to worker manager.")
    return True


if __name__ == "__main__":
    start_worker_manager()
