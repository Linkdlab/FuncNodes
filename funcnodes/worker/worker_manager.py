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

from funcnodes.worker.worker import WorkerJson


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

    run_in_new_process(
        pypath,
        "-m",
        "funcnodes",
        "startworker",
        f"--uuid={workerconfig['uuid']}",
        #  cwd=os.path.join(workerconfig["data_path"], ".."),
    )


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
        self._is_running = True
        l_rl = 0
        while self._is_running:
            await asyncio.sleep(1)
            t = time.time()
            await self.check_shutdown()

            if t - l_rl > 20 or self.worker_changed():
                await self.reload_workers()
                l_rl = t

    async def _handle_connection(
        self, websocket: websockets.WebSocketServerProtocol, path
    ):
        self._connections.append(websocket)
        async for message in websocket:
            await self._handle_message(message, websocket)
        self._connections.remove(websocket)

    async def _handle_message(
        self, message: str, websocket: websockets.WebSocketServerProtocol
    ):
        if message == "ping":
            return await websocket.send("pong")
        elif message == "stop":
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
            except json.JSONDecodeError as e:
                pass

            print(f"Unknown message: {message}")

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
        active_files = set(
            [
                f.split("_")[1].split(".")[0]
                for f in os.listdir(self._worker_dir)
                if f.startswith("worker_") and f.endswith(".p")
            ]
        )

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

        async def check_worker(workerconfig: WorkerJson):
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
                                active_worker.append(workerconfig)
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
                    inactive_worker.append(workerconfig)
                    pfile = os.path.join(
                        self._worker_dir, f"worker_{workerconfig['uuid']}.p"
                    )
                    if os.path.exists(pfile):
                        os.remove(pfile)

        workerchecks = []
        for f in os.listdir(self._worker_dir):
            if f.startswith("worker_") and f.endswith(".json"):
                with open(
                    os.path.join(self._worker_dir, f), "r", encoding="utf-8"
                ) as file:
                    workerconfig: WorkerJson = json.load(file)
                    workerchecks.append(check_worker(workerconfig))
        await asyncio.gather(*workerchecks)

        self._active_workers = active_worker
        self._inactive_workers = inactive_worker
        print(f"Active workers: {active_worker}")
        print(f"inactive workers: {inactive_worker}")

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

    async def activate_worker(
        self, workerid, websocket: websockets.WebSocketServerProtocol
    ):
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
        for i in range(20):
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
