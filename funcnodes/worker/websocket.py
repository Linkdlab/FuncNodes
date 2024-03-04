from __future__ import annotations
from typing import List, Optional
import websockets
from funcnodes import NodeSpace, JSONEncoder
from funcnodes.worker import RemoteWorker, CustomLoop
from funcnodes.worker.worker import CmdMessage, ErrorMessage, ResultMessage
from exposedfunctionality import get_exposed_methods
import json
import traceback
import asyncio


class WSLoop(CustomLoop):
    def __init__(
        self, host: str, port: int, worker: WSWorker, delay=5, *args, **kwargs
    ) -> None:
        super().__init__(*args, delay=delay, **kwargs)
        self._host = host
        self._port = port
        self.ws_server: websockets.WebSocketServer | None = None
        self._worker = worker
        self.clients: List[websockets.WebSocketServerProtocol] = []

    async def _handle_connection(
        self, websocket: websockets.WebSocketServerProtocol, path
    ):
        self.clients.append(websocket)
        try:
            async for message in websocket:
                json_msg = json.loads(message)
                if "type" not in json_msg:
                    continue
                if json_msg["type"] == "cmd":
                    try:
                        await self._worker._handle_cmd_msg(json_msg, websocket)
                    except Exception as e:
                        await self._send_error(websocket, e, id=json_msg.get("id"))
        finally:
            self.clients.remove(websocket)

    async def _send_error(
        self,
        websocket: websockets.WebSocketServerProtocol,
        error: Exception,
        id: Optional[str] = None,
    ):
        await websocket.send(
            json.dumps(
                ErrorMessage(
                    type="error",
                    error=str(error),
                    tb=traceback.format_exception(error),
                    id=id,
                )
            )
        )

    async def _assert_connection(self):
        if self.ws_server is None:
            self.ws_server = await websockets.serve(
                self._handle_connection, self._host, self._port
            )

    async def loop(self):
        await self._assert_connection()

    async def stop(self):
        if self.ws_server is None:
            self.ws_server.stop()
        await super().stop()


class WSWorker(RemoteWorker):
    def __init__(
        self,
        data_path,
        host="localhost",
        port=9382,
    ) -> None:
        super().__init__(data_path=data_path)
        self.ws_loop = WSLoop(host=host, port=port, worker=self)
        self.loop_manager.add_loop(self.ws_loop)

        self._exposed_methods = get_exposed_methods(self)

    async def _handle_cmd_msg(
        self, json_msg: CmdMessage, websocket: websockets.WebSocketServerProtocol
    ):
        cmd = json_msg["cmd"]
        if cmd not in self._exposed_methods:
            raise Exception(f"Unknown command {cmd}")
        kwargs = json_msg["kwargs"] or {}
        func = self._exposed_methods[cmd][0]
        if asyncio.iscoroutinefunction(func):
            result = await func(**kwargs)
        else:
            result = func(**kwargs)

        await self.send(
            ResultMessage(type="result", result=result, id=json_msg.get("id")),
            websocket=websocket,
        )

    async def sendmessage(
        self, msg: str, websocket: Optional[websockets.WebSocketServerProtocol] = None
    ):
        """send a message to the frontend"""
        if websocket:
            await websocket.send(msg)
        else:
            clients = self.ws_loop.clients

            if len(clients) > 0:
                await asyncio.gather(
                    *[ws.send(msg) for ws in clients],
                    return_exceptions=False,
                )

    def _on_nodespaceerror(self, error: Exception, src: NodeSpace):
        return super()._on_nodespaceerror(error, src)

    def _on_nodespaceevent(self, event: str, src: NodeSpace, **kwargs):
        return super()._on_nodespaceevent(event, src, **kwargs)

    def stop(self):
        super().stop()
