import sys

if sys.platform != "emscripten":
    import contextlib
    import asyncio
    import json
    import os
    import aiohttp
    from aiohttp import WSMsgType, web
    import time

    # Import your WorkerManager from wherever it's defined
    from funcnodes.worker.worker_manager import WorkerManager
    from funcnodes_worker.worker import worker_json_get_data_path
    import funcnodes as fn

    # If your code references `funcnodes.config.CONFIG` or a similar global config,
    # you can mock it out here or set it before running tests.
    import pytest

    from pytest_funcnodes import funcnodes_test, get_in_test

    @pytest.fixture
    async def worker_managerpack():
        assert get_in_test(), "Not in test mode"
        wm = WorkerManager(
            host="127.0.0.1",
            port=0,  # Let OS pick
            debug=True,
        )
        if not wm.app:
            wm.app = web.Application()
            wm.app.router.add_get("/", wm._handle_connection)

        # Create an AppRunner and Site to bind to an ephemeral port
        _runner = web.AppRunner(wm.app)
        await _runner.setup()
        _site = web.TCPSite(_runner, "127.0.0.1", 0)
        await _site.start()

        # The site was started on an ephemeral port. Let's retrieve it:
        _port = _site._server.sockets[0].getsockname()[1]

        # Mark manager as running
        wm._is_running = True

        # Start the WorkerManager's main loop in the background
        # We'll keep a reference to the task, so we can stop it in asyncTearDown
        _main_loop_task = asyncio.create_task(wm.run_forever())
        yield wm, _port

        wm._is_running = False

        # Cancel the background loop task
        _main_loop_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _main_loop_task

        # Clean up the aiohttp runner
        await _runner.cleanup()

    @pytest.fixture
    async def worker_manager_port(worker_managerpack):
        return worker_managerpack[1]

    @pytest.fixture
    async def worker_manager(worker_managerpack):
        return worker_managerpack[0]

    @funcnodes_test
    async def test_ping_pong(worker_manager, worker_manager_port):
        """
        Test that sending 'ping' returns 'pong'.
        """
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"ws://127.0.0.1:{worker_manager_port}"
            ) as ws:
                await ws.send_str("ping")
                resp = await ws.receive()
                assert resp.type == WSMsgType.TEXT
                assert resp.data == "pong"

    @funcnodes_test
    async def test_identify(worker_manager, worker_manager_port):
        """
        Test that sending 'identify' returns the correct WorkerManager identity JSON.
        """
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"ws://127.0.0.1:{worker_manager_port}"
            ) as ws:
                await ws.send_str("identify")
                resp = await ws.receive()
                assert resp.type == WSMsgType.TEXT
                data = json.loads(resp.data)
                assert data.get("class") == "WorkerManager"

    @funcnodes_test
    async def test_worker_status_empty(worker_manager, worker_manager_port):
        """
        Test that 'worker_status' initially returns empty lists for active/inactive.
        """
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"ws://127.0.0.1:{worker_manager_port}"
            ) as ws:
                await ws.send_str("worker_status")
                resp = await ws.receive()
                assert resp.type == WSMsgType.TEXT
                data = json.loads(resp.data)
                assert data["type"] == "worker_status"
                assert len(data["active"]) == 0
                assert len(data["inactive"]) == 0

    @funcnodes_test
    async def test_stop_manager(worker_manager, worker_manager_port):
        """
        Test sending 'stop' causes the worker manager to shut down.
        """
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"ws://127.0.0.1:{worker_manager_port}"
            ) as ws:
                await ws.send_str("stop")
                # Wait briefly for the manager to process the command
                await asyncio.sleep(1)

        # Now the manager should have set _is_running = False
        assert not worker_manager._is_running

    @funcnodes_test
    async def test_handle_unknown_message(worker_manager, worker_manager_port):
        """
        Test that sending an unrecognized command logs a warning and doesn't crash.
        """
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"ws://127.0.0.1:{worker_manager_port}"
            ) as ws:
                await ws.send_str("some_unknown_command")
                # The manager logs a warning, but doesn't close the connection.

                # Verify it hasn't closed:
                await asyncio.sleep(0.2)
                assert not ws.closed

                # We can still ping
                await ws.send_str("ping")
                resp = await ws.receive()
                assert resp.type == WSMsgType.TEXT
                assert resp.data == "pong"

    @funcnodes_test
    async def test_new_worker(worker_manager, worker_manager_port):
        """
        Test creating a new worker, mocking environment creation calls.
        """

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"ws://127.0.0.1:{worker_manager_port}"
            ) as ws:
                t = time.time()
                await ws.send_str(json.dumps({"type": "new_worker"}))
                while time.time() - t < 40:
                    try:
                        resp = await ws.receive(timeout=3)
                    except asyncio.TimeoutError:
                        continue
                    assert resp.type == WSMsgType.TEXT
                    data = json.loads(resp.data)
                    print(time.time() - t, "\n", data, "\n\n")

                    if data["type"] == "worker_status":
                        continue
                    elif data["type"] == "progress":
                        continue
                    else:
                        break
                assert data["type"] == "worker_created"
                # Check that a 'uuid' is returned
                assert "uuid" in data

    @funcnodes_test
    async def test_delete_worker_traceless(worker_manager, worker_manager_port):
        """
        Create a worker, then delete it and verify all related files are gone.
        """
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"ws://127.0.0.1:{worker_manager_port}"
            ) as ws:
                # Create new worker
                t = time.time()
                await ws.send_str(json.dumps({"type": "new_worker"}))
                uuid = None
                while time.time() - t < 60:
                    try:
                        resp = await ws.receive(timeout=3)
                    except asyncio.TimeoutError:
                        continue
                    assert resp.type == WSMsgType.TEXT
                    data = json.loads(resp.data)
                    if data.get("type") in {"progress", "worker_status"}:
                        continue
                    if data.get("type") == "worker_created":
                        uuid = data["uuid"]
                        break
                assert uuid is not None

                confdir = fn.config.get_config_dir()

                # Locate worker files to verify deletion later
                workers_dir = os.path.join(confdir, "workers")
                json_file = os.path.join(workers_dir, f"worker_{uuid}.json")
                p_file = os.path.join(workers_dir, f"worker_{uuid}.p")
                runstate_file = os.path.join(workers_dir, f"worker_{uuid}.runstate")

                # Read config to know data_path and env_path
                # Wait briefly for file to be written
                for _ in range(30):
                    if os.path.exists(json_file):
                        break
                    await asyncio.sleep(0.1)
                assert os.path.exists(json_file), "Worker config file missing"

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
                        os.path.exists(p) for p in [json_file, p_file, runstate_file]
                    ):
                        if (not data_path or not os.path.exists(data_path)) and (
                            not env_path or not os.path.exists(env_path)
                        ):
                            deleted = True
                            break

                assert deleted, "Did not receive deletion confirmation in time"

                # Final assertions that everything is removed
                assert not os.path.exists(json_file)
                assert not os.path.exists(p_file)
                assert not os.path.exists(runstate_file)
                if data_path:
                    assert not os.path.exists(data_path)
                if env_path:
                    assert not os.path.exists(env_path)

    @funcnodes_test
    async def test_activate_unknown_worker(worker_manager_port):
        """
        Test that activating an unknown worker returns an error message.
        """
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"ws://127.0.0.1:{worker_manager_port}"
            ) as ws:
                await ws.send_str(
                    json.dumps({"type": "set_active", "workerid": "does-not-exist"})
                )
                t = time.time()
                while time.time() - t < 20:
                    resp = await ws.receive()
                    assert resp.type == WSMsgType.TEXT
                    data = json.loads(resp.data)
                    if data["type"] == "progress":
                        continue
                    else:
                        break
                assert data["type"] == "error"
                assert "not found" in data["message"]

    @funcnodes_test
    async def test_stop_unknown_worker(worker_manager_port):
        """
        Test stopping an unknown worker returns gracefully (no crash).
        """
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"ws://127.0.0.1:{worker_manager_port}"
            ) as ws:
                await ws.send_str(
                    json.dumps({"type": "stop_worker", "workerid": "does-not-exist"})
                )
                # The code checks for a target_worker; if None, it just returns.
                # We'll wait a moment to see if it closes or errors:
                await asyncio.sleep(0.2)
                assert not ws.closed
