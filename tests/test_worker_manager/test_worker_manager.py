import sys

if sys.platform != "emscripten":
    import contextlib
    import unittest
    import asyncio
    import json
    import os
    import shutil
    import aiohttp
    from aiohttp import WSMsgType, web
    import tempfile
    import time

    # Import your WorkerManager from wherever it's defined
    from funcnodes.worker.worker_manager import WorkerManager
    from funcnodes_worker.worker import worker_json_get_data_path

    # If your code references `funcnodes.config.CONFIG` or a similar global config,
    # you can mock it out here or set it before running tests.
    from funcnodes import config

    class TestWorkerManager(unittest.IsolatedAsyncioTestCase):
        """
        Example test suite for WorkerManager using unittest's IsolatedAsyncioTestCase.
        """

        async def asyncSetUp(self):
            """
            Called before each test. Sets up a WorkerManager server using aiohttp.
            """
            # Mock out funcnodes.config.CONFIG to avoid polluting real directories.
            self.testdir = tempfile.mkdtemp(prefix="funcnodes_test_config_")
            # Remove the temporary config directory if desired

            config.reload(funcnodes_config_dir=self.testdir)

            # Initialize the WorkerManager
            self.wm = WorkerManager(
                host="127.0.0.1",
                port=0,  # Let OS pick
                debug=True,
            )
            # WorkerManager normally sets up self.wm.app inside run_forever(), but
            # we can do so manually here to leverage aiohttp test utilities.
            if not self.wm.app:
                self.wm.app = web.Application()
                self.wm.app.router.add_get("/", self.wm._handle_connection)

            # Create an AppRunner and Site to bind to an ephemeral port
            self._runner = web.AppRunner(self.wm.app)
            await self._runner.setup()
            self._site = web.TCPSite(self._runner, "127.0.0.1", 0)
            await self._site.start()

            # The site was started on an ephemeral port. Let's retrieve it:
            self._port = self._site._server.sockets[0].getsockname()[1]

            # Mark manager as running
            self.wm._is_running = True

            # Start the WorkerManager's main loop in the background
            # We'll keep a reference to the task, so we can stop it in asyncTearDown
            self._main_loop_task = asyncio.create_task(self.wm.run_forever())

        async def asyncTearDown(self):
            """
            Called after each test. Cleans up the WorkerManager and any mocks.
            """
            # Stop the manager's main loop
            self.wm._is_running = False

            # Cancel the background loop task
            self._main_loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._main_loop_task

            # Clean up the aiohttp runner
            await self._runner.cleanup()

            # Remove the temporary config directory if desired
            if os.path.exists(self.testdir):
                shutil.rmtree(self.testdir, ignore_errors=True)

        async def test_ping_pong(self):
            """
            Test that sending 'ping' returns 'pong'.
            """
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f"ws://127.0.0.1:{self._port}") as ws:
                    await ws.send_str("ping")
                    resp = await ws.receive()
                    self.assertEqual(resp.type, WSMsgType.TEXT)
                    self.assertEqual(resp.data, "pong")

        async def test_identify(self):
            """
            Test that sending 'identify' returns the correct WorkerManager identity JSON.
            """
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f"ws://127.0.0.1:{self._port}") as ws:
                    await ws.send_str("identify")
                    resp = await ws.receive()
                    self.assertEqual(resp.type, WSMsgType.TEXT)
                    data = json.loads(resp.data)
                    self.assertEqual(data.get("class"), "WorkerManager")

        async def test_worker_status_empty(self):
            """
            Test that 'worker_status' initially returns empty lists for active/inactive.
            """
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f"ws://127.0.0.1:{self._port}") as ws:
                    await ws.send_str("worker_status")
                    resp = await ws.receive()
                    self.assertEqual(resp.type, WSMsgType.TEXT)
                    data = json.loads(resp.data)
                    self.assertEqual(data["type"], "worker_status")
                    self.assertEqual(len(data["active"]), 0)
                    self.assertEqual(len(data["inactive"]), 0)

        async def test_stop_manager(self):
            """
            Test sending 'stop' causes the worker manager to shut down.
            """
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f"ws://127.0.0.1:{self._port}") as ws:
                    await ws.send_str("stop")
                    # Wait briefly for the manager to process the command
                    await asyncio.sleep(1)

            # Now the manager should have set _is_running = False
            self.assertFalse(self.wm._is_running)

        async def test_handle_unknown_message(self):
            """
            Test that sending an unrecognized command logs a warning and doesn't crash.
            """
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f"ws://127.0.0.1:{self._port}") as ws:
                    await ws.send_str("some_unknown_command")
                    # The manager logs a warning, but doesn't close the connection.

                    # Verify it hasn't closed:
                    await asyncio.sleep(0.2)
                    self.assertFalse(ws.closed)

                    # We can still ping
                    await ws.send_str("ping")
                    resp = await ws.receive()
                    self.assertEqual(resp.type, WSMsgType.TEXT)
                    self.assertEqual(resp.data, "pong")

        async def test_new_worker(self):
            """
            Test creating a new worker, mocking environment creation calls.
            """

            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f"ws://127.0.0.1:{self._port}") as ws:
                    t = time.time()
                    await ws.send_str(json.dumps({"type": "new_worker"}))
                    while time.time() - t < 40:
                        try:
                            resp = await ws.receive(timeout=3)
                        except asyncio.TimeoutError:
                            continue
                        self.assertEqual(resp.type, WSMsgType.TEXT)
                        data = json.loads(resp.data)
                        print(time.time() - t, "\n", data, "\n\n")

                        if data["type"] == "worker_status":
                            continue
                        elif data["type"] == "progress":
                            continue
                        else:
                            break
                    self.assertEqual(data["type"], "worker_created")
                    # Check that a 'uuid' is returned
                    self.assertIn("uuid", data)

        async def test_delete_worker_traceless(self):
            """
            Create a worker, then delete it and verify all related files are gone.
            """
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f"ws://127.0.0.1:{self._port}") as ws:
                    # Create new worker
                    t = time.time()
                    await ws.send_str(json.dumps({"type": "new_worker"}))
                    uuid = None
                    while time.time() - t < 60:
                        try:
                            resp = await ws.receive(timeout=3)
                        except asyncio.TimeoutError:
                            continue
                        self.assertEqual(resp.type, WSMsgType.TEXT)
                        data = json.loads(resp.data)
                        if data.get("type") in {"progress", "worker_status"}:
                            continue
                        if data.get("type") == "worker_created":
                            uuid = data["uuid"]
                            break
                    self.assertIsNotNone(uuid, "Worker was not created in time")

                    # Locate worker files to verify deletion later
                    workers_dir = os.path.join(self.testdir, "workers")
                    json_file = os.path.join(workers_dir, f"worker_{uuid}.json")
                    p_file = os.path.join(workers_dir, f"worker_{uuid}.p")
                    runstate_file = os.path.join(workers_dir, f"worker_{uuid}.runstate")

                    # Read config to know data_path and env_path
                    # Wait briefly for file to be written
                    for _ in range(30):
                        if os.path.exists(json_file):
                            break
                        await asyncio.sleep(0.1)
                    self.assertTrue(
                        os.path.exists(json_file), "Worker config file missing"
                    )
                    with open(json_file, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    data_path = worker_json_get_data_path(cfg)
                    env_path = cfg.get("env_path")

                    # Request deletion
                    await ws.send_str(
                        json.dumps({"type": "delete_worker", "workerid": uuid})
                    )

                    # Consume messages until we see confirmation or timeout
                    t = time.time()
                    deleted = False
                    while time.time() - t < 30:
                        try:
                            resp = await ws.receive(timeout=3)
                        except asyncio.TimeoutError:
                            # Still allow filesystem checks
                            pass
                        else:
                            if resp.type == WSMsgType.TEXT:
                                data = json.loads(resp.data)
                                if data.get("type") in {"progress", "worker_status"}:
                                    # continue waiting
                                    pass
                                elif (
                                    data.get("type") == "worker_deleted"
                                    and data.get("uuid") == uuid
                                ):
                                    deleted = True
                                    break

                        # Check if files are gone already
                        if not any(
                            os.path.exists(p)
                            for p in [json_file, p_file, runstate_file]
                        ):
                            if (not data_path or not os.path.exists(data_path)) and (
                                not env_path or not os.path.exists(env_path)
                            ):
                                deleted = True
                                break

                    self.assertTrue(
                        deleted, "Did not receive deletion confirmation in time"
                    )

                    # Final assertions that everything is removed
                    self.assertFalse(os.path.exists(json_file))
                    self.assertFalse(os.path.exists(p_file))
                    self.assertFalse(os.path.exists(runstate_file))
                    if data_path:
                        self.assertFalse(os.path.exists(data_path))
                    if env_path:
                        self.assertFalse(os.path.exists(env_path))

        async def test_activate_unknown_worker(self):
            """
            Test that activating an unknown worker returns an error message.
            """
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f"ws://127.0.0.1:{self._port}") as ws:
                    await ws.send_str(
                        json.dumps({"type": "set_active", "workerid": "does-not-exist"})
                    )
                    t = time.time()
                    while time.time() - t < 20:
                        resp = await ws.receive()
                        self.assertEqual(resp.type, WSMsgType.TEXT)
                        data = json.loads(resp.data)
                        if data["type"] == "progress":
                            continue
                        else:
                            break
                    self.assertEqual(data["type"], "error")
                    self.assertIn("not found", data["message"])

        async def test_stop_unknown_worker(self):
            """
            Test stopping an unknown worker returns gracefully (no crash).
            """
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f"ws://127.0.0.1:{self._port}") as ws:
                    await ws.send_str(
                        json.dumps(
                            {"type": "stop_worker", "workerid": "does-not-exist"}
                        )
                    )
                    # The code checks for a target_worker; if None, it just returns.
                    # We'll wait a moment to see if it closes or errors:
                    await asyncio.sleep(0.2)
                    self.assertFalse(ws.closed)
