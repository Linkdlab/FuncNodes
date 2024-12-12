from __future__ import annotations
from typing import List, Optional
from aiohttp import web, WSCloseCode
from funcnodes import NodeSpace, JSONDecoder
from funcnodes.worker import CustomLoop
from .remote_worker import RemoteWorker, RemoteWorkerJson

import json
import asyncio
from funcnodes import FUNCNODES_LOGGER
import os


class WSWorkerJson(RemoteWorkerJson):
    """
    TypedDict for WebSocket worker configuration.

    Attributes:
      host (str): The host address for the WebSocket server.
      port (int): The port number for the WebSocket server.
      ssl (bool): Whether to use SSL for the WebSocket server.
    """

    host: str
    port: int
    ssl: bool


STARTPORT = int(os.environ.get("FUNCNODES_WS_WORKER_STARTPORT", 9382))
ENDPORT = int(os.environ.get("FUNCNODES_WS_WORKER_ENDPORT", 9582))


class WSLoop(CustomLoop):
    """
    Custom loop for WebSocket worker using aiohttp.
    """

    def __init__(
        self,
        worker: WSWorker,
        host: str = None,
        port: int = STARTPORT,
        delay=5,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, delay=delay, **kwargs)
        self._host = host or os.environ.get("FUNCNODES_HOST", "localhost")
        self._port = port
        self._use_ssl: bool = False
        self._worker = worker
        self.clients: List[web.WebSocketResponse] = []
        self.app = web.Application()
        self.app.router.add_get("/", self._handle_connection)
        self.site: Optional[web.TCPSite] = None
        self.runner = None

    async def _handle_connection(self, request: web.Request):
        """
        Handles a new client connection.
        """
        websocket = web.WebSocketResponse(
            max_msg_size=int(os.environ.get("FUNCNODES_WS_WORKER_MAX_SIZE", 2**32 - 1))
        )
        await websocket.prepare(request)
        self.clients.append(websocket)
        self._worker.logger.debug("Client connected")

        try:
            async for message in websocket:
                if message.type == web.WSMsgType.TEXT:
                    self._worker.logger.debug(f"Received message: {message.data}")
                    json_msg = json.loads(message.data, cls=JSONDecoder)
                    await self._worker.recieve_message(json_msg, websocket=websocket)
                elif message.type == web.WSMsgType.ERROR:
                    exc = websocket.exception()
                    if exc is not None:
                        FUNCNODES_LOGGER.error(f"WebSocket error: {exc}")
                        raise exc
                elif message.type == web.WSMsgType.CLOSE:
                    self._worker.logger.debug("Client closed connection")
                    break
                else:
                    print(f"Received unknown message type: {message.type}")
        except Exception as e:
            FUNCNODES_LOGGER.exception(e)
        finally:
            self._worker.logger.debug("Client disconnected")
            self.clients.remove(websocket)

        return websocket

    async def _assert_connection(self):
        """
        Starts the aiohttp WebSocket server if not already running.
        """
        if self.site is not None:
            return

        while True:
            try:
                self.runner = web.AppRunner(self.app)
                await self.runner.setup()
                self.site = web.TCPSite(self.runner, self._host, self._port)
                await self.site.start()
                self._worker.write_config()
                self._worker.logger.info(
                    f"WebSocket server running on {self._host}:{self._port}"
                )
                return
            except OSError:
                self._port += 1
                if self._port > ENDPORT:
                    self._port = STARTPORT
                    raise Exception("No free ports available")

    async def change_port(self, port: Optional[int] = None):
        """
        Changes the port number for the WebSocket server.
        """
        if port is not None:
            self._port = port
        else:
            self._port += 1
            if self._port > ENDPORT:
                self._port = STARTPORT
        if self.site is not None:
            await self.site.stop()
            self.site = None
        if self.runner is not None:
            await self.runner.cleanup()
            self.runner = None

    async def loop(self):
        """
        The main loop for the WebSocket server.
        """
        await self._assert_connection()

    async def stop(self):
        """
        Stops the WebSocket server.
        """

        # close all clients
        for client in self.clients:
            await client.close(
                code=WSCloseCode.GOING_AWAY, message="Server shutting down"
            )

        if self.site is not None:
            await self.site.stop()
            self.site = None
        if self.runner is not None:
            await self.runner.cleanup()
            self.runner = None
        await super().stop()


class WSWorker(RemoteWorker):
    """
    Remote worker for WebSocket connections using aiohttp.
    """

    def __init__(
        self,
        host=None,
        port=None,
        **kwargs,
    ) -> None:
        """
        Initializes a new WSWorker object.

        Args:
          host (str, optional): The host to connect to. Defaults to None.
          port (int, optional): The port to connect to. Defaults to None.
          **kwargs: Additional keyword arguments.

                  Notes:
          If host or port are not provided, they will be retrieved from the config dictionary if available.

        Examples:
          >>> worker = WSWorker(host='127.0.0.1', port=9382)
          >>> worker = WSWorker()
        """
        super().__init__(**kwargs)
        c = self.config
        if c is None:
            c = {}

        if host is None:
            host = c.get("host", os.environ.get("FUNCNODES_HOST", "localhost"))
        if port is None:
            port = c.get("port", STARTPORT)
        self.ws_loop = WSLoop(host=host, port=port, worker=self)
        self.loop_manager.add_loop(self.ws_loop)

    async def sendmessage(
        self, msg: str, websocket: Optional[web.WebSocketResponse] = None
    ):
        """send a message to the frontend"""
        if websocket:
            try:
                await websocket.send_str(msg)
            except Exception as exc:
                self.logger.exception(exc)
        else:
            if self.ws_loop.clients:
                ans = await asyncio.gather(
                    *[client.send_str(msg) for client in self.ws_loop.clients],
                    return_exceptions=True,
                )
                for a in ans:
                    if isinstance(a, Exception):
                        self.logger.exception(a)

    def _on_nodespaceerror(self, error: Exception, src: NodeSpace):
        """
        Handles an error that occurred in a NodeSpace.

        Args:
          error (Exception): The error that occurred.
          src (NodeSpace): The NodeSpace where the error occurred.

        Returns:
          None.

        Examples:
          >>> worker._on_nodespaceerror(Exception('Error'), NodeSpace())
        """
        return super()._on_nodespaceerror(error, src)

    def _on_nodespaceevent(self, event: str, src: NodeSpace, **kwargs):
        """
        Handles an event that occurred in a NodeSpace.

        Args:
          event (str): The event that occurred.
          src (NodeSpace): The NodeSpace where the event occurred.
          **kwargs: Additional keyword arguments.

        Returns:
          None.

        Examples:
          >>> worker._on_nodespaceevent('event', NodeSpace(), arg1='value1', arg2='value2')
        """
        return super()._on_nodespaceevent(event, src, **kwargs)

    def stop(self):
        """
        Stops the WSWorker.

        Returns:
          None.

        Examples:
          >>> worker.stop()
        """
        super().stop()

    def update_config(self, config: RemoteWorkerJson) -> WSWorkerJson:
        """
        Updates a configuration dictionary for the WSWorker.

        Returns:
          WSWorkerJson: The configuration dictionary for the WSWorker.

        Examples:
          >>> worker.update_config()
        """

        d = WSWorkerJson(
            **{
                **super().update_config(config),
                **dict(
                    host=os.environ.get("FUNCNODES_HOST", "localhost"),
                    port=STARTPORT,
                    ssl=False,
                ),
            }
        )
        if hasattr(self, "ws_loop"):
            d["host"] = self.ws_loop._host
            d["port"] = self.ws_loop._port
            d["ssl"] = self.ws_loop._use_ssl

        return d

    def exportable_config(self) -> dict:
        conf = super().exportable_config()
        conf.pop("host", None)
        conf.pop("port", None)
        conf.pop("ssl", None)
        return conf

    @property
    def host(self) -> Optional[str]:
        """
        The host address for the WebSocket server.

        Returns:
          str: The host address for the WebSocket server.

        Examples:
          >>> worker.host
        """
        if hasattr(self, "ws_loop"):
            return self.ws_loop._host
        return None

    @property
    def port(self) -> Optional[int]:
        """
        The port number for the WebSocket server.

        Returns:
          int: The port number for the WebSocket server.

        Examples:
          >>> worker.port
        """
        if hasattr(self, "ws_loop"):
            return self.ws_loop._port
        return None
