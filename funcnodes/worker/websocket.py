from __future__ import annotations
from typing import List, Optional
import websockets
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


STARTPORT = os.environ.get("FUNCNODES_WS_WORKER_STARTPORT", 9382)
ENDPORT = os.environ.get("FUNCNODES_WS_WORKER_ENDPORT", 9582)


class WSLoop(CustomLoop):
    """
    Custom loop for WebSocket worker.

    Args:
      worker (WSWorker): The WebSocket worker.
      host (str): The host address for the WebSocket server.
      port (int): The port number for the WebSocket server.
      delay (int): The delay between loop iterations.
      *args: Additional arguments.
      **kwargs: Additional keyword arguments.

    Attributes:
      ws_server (websockets.WebSocketServer | None): The WebSocket server.
      clients (List[websockets.WebSocketServerProtocol]): The list of connected clients.

    Methods:
      loop: The main loop for the WebSocket server.
      stop: Stops the WebSocket server.
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
        """
        Initializes a new WSLoop instance.

        Args:
          worker (WSWorker): The WebSocket worker.
          host (str): The host address for the WebSocket server.
          port (int): The port number for the WebSocket server.
          delay (int): The delay between loop iterations.
          *args: Additional arguments.
          **kwargs: Additional keyword arguments.
        """
        super().__init__(*args, delay=delay, **kwargs)
        self._host = host or os.environ.get("FUNCNODES_HOST", "localhost")
        self._port = port
        self.ws_server: websockets.WebSocketServer | None = None
        self._worker = worker
        self.clients: List[websockets.WebSocketServerProtocol] = []
        self._use_ssl: bool = False

    async def _handle_connection(
        self, websocket: websockets.WebSocketServerProtocol, *args, **kwargs
    ):
        """
        Handles a new client connection.

        Args:
          websocket (websockets.WebSocketServerProtocol): The WebSocket connection.
        """
        self.clients.append(websocket)
        try:
            async for message in websocket:
                print(f"Recieved message: {message}")
                json_msg = json.loads(message, cls=JSONDecoder)
                await self._worker.recieve_message(json_msg, websocket=websocket)

        except websockets.exceptions.WebSocketException as e:
            FUNCNODES_LOGGER.exception(e)
        finally:
            print("Client disconnected")
            self.clients.remove(websocket)

    async def _assert_connection(self):
        """
        Asserts that the WebSocket server is running.
        """
        while True:
            try:
                if self.ws_server is None:
                    self.ws_server = await websockets.serve(
                        self._handle_connection,
                        self._host,
                        self._port,
                        max_size=int(
                            os.environ.get("FUNCNODES_WS_WORKER_MAX_SIZE", 2**32)
                        ),
                    )
                    self._worker.write_config()
                return
            except OSError:
                self._port += 1
                if self._port > ENDPORT:
                    self._port = STARTPORT
                    raise Exception("No free ports available")

    def change_port(self, port: Optional[int] = None):
        """
        Changes the port number for the WebSocket server.
        If no port number is provided, the port number will be incremented by 1.

        Args:
          port (int, optional): The new port number. Defaults to None.
        """
        if port is not None:
            self._port = port
        else:
            self._port += 1
            if self._port > ENDPORT:
                self._port = STARTPORT
        if self.ws_server is not None:
            self.ws_server.close()
            self.ws_server = None

    async def loop(self):
        """
        The main loop for the WebSocket server.
        """
        await self._assert_connection()

    async def stop(self):
        """
        Stops the WebSocket server.
        """
        if self.ws_server is not None:
            self.ws_server.close()
            await self.ws_server.wait_closed()
        await super().stop()


class WSWorker(RemoteWorker):
    """
    Remote worker for WebSocket connections.
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
        self, msg: str, websocket: Optional[websockets.WebSocketServerProtocol] = None
    ):
        """send a message to the frontend"""
        if websocket:
            try:
                await websocket.send(msg)
            except websockets.exceptions.WebSocketException:
                pass
        else:
            clients = self.ws_loop.clients

            if len(clients) > 0:
                await asyncio.gather(
                    *[ws.send(msg) for ws in clients],
                    return_exceptions=True,
                )

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
