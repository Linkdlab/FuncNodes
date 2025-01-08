import asyncio
from unittest import IsolatedAsyncioTestCase
from funcnodes import (
    WSWorker,
    config,
)
import aiohttp
import time

config.IN_NODE_TEST = True


class TestWSWorker(IsolatedAsyncioTestCase):
    async def test_ws_worker(self):
        ws_worker = WSWorker(uuid="test_ws_worker")

        ws_worker.run_forever_threaded()

        port = ws_worker.port
        host = ws_worker.host

        # make a connection to the websocket server
        MAXTIME = 10
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(f"ws://{host}:{port}") as ws:

                async def listentask():
                    async for msg in ws:
                        print(msg)

                await ws.send_json({"type": "cmd", "cmd": "stop_worker"})
                asyncio.create_task(listentask())

                stime = time.time()
                self.assertFalse(ws.closed)
                while not ws.closed and time.time() - stime < MAXTIME:
                    await asyncio.sleep(
                        0.5
                    )  # Poll until the connection is fully closed
                self.assertTrue(ws.closed)

                # Wait for WebSocket to fully close
