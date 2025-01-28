from __future__ import annotations
from typing import List, Optional, Tuple, Dict
from aiohttp import web, WSCloseCode
from pathlib import Path

try:
    import aiohttp_cors
except (ImportError, ModuleNotFoundError):
    aiohttp_cors = None

from funcnodes import NodeSpace, JSONDecoder
from funcnodes.worker import CustomLoop
from .remote_worker import RemoteWorker, RemoteWorkerJson

import json
import asyncio
from funcnodes import FUNCNODES_LOGGER
import os
import uuid
import time
import io


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

MESSAGE_SIZE_BEFORE_REQUEST = 1024 * 1024 * 1  # 1MB
LARGE_MESSAGE_MEMORY_TIMEOUT = 60  # 1 minute


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
        self.app = web.Application(client_max_size=1 * 1024 * 1024 * 1024)
        # A store for large messages that cannot be sent directly over WebSocket
        self.message_store: Dict[str, Tuple[str, float]] = {}

        # WebSocket endpoint
        self.app.router.add_get("/", self._handle_connection)

        # Endpoint for retrieving large messages
        self.app.router.add_get("/message/{msg_id}", self._handle_get_message)

        # Endpoint for uploading large messages
        self.app.router.add_post("/message/", self._handle_post_message)
        self.app.router.add_post("/upload/", self._handle_upload)

        # Enable CORS
        if aiohttp_cors is not None:
            cors = aiohttp_cors.setup(
                self.app,
                defaults={
                    "*": aiohttp_cors.ResourceOptions(
                        allow_credentials=True,
                        expose_headers="*",
                        allow_headers="*",
                    )
                },
            )

            # Apply CORS to all routes
            for route in list(self.app.router.routes()):
                cors.add(route)

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

    async def _handle_get_message(self, request: web.Request):
        """
        Handle GET requests to retrieve large messages that were previously stored.
        """
        msg_id = request.match_info["msg_id"]
        if msg_id in self.message_store:
            msg = self.message_store[msg_id][
                0
            ]  # Remove after retrieval : self.message_store.pop(msg_id)[0]
            return web.Response(text=msg, status=200, content_type="application/json")
        return web.Response(text="Message not found", status=404)

    async def _handle_post_message(self, request: web.Request):
        """
        Handle POST requests to store large incoming messages on the server.

        Clients can use this endpoint to upload large messages, and the server
        will return a unique ID that can be shared over WebSocket.
        """
        try:
            data = await request.read()
            # Here we assume the incoming data is JSON text.
            # If it's not JSON, you may need additional processing/validation.
            msg = data.decode("utf-8")
            json_msg = json.loads(msg, cls=JSONDecoder)

            await self._worker.recieve_message(json_msg)
            return web.Response(text="Message received", status=200)
        except Exception as e:
            FUNCNODES_LOGGER.exception(e)
            return web.Response(text="Error processing message", status=400)

    async def _handle_upload(self, request: web.Request):
        """
        Handles file upload via POST request.
        Clients can upload files, which will be saved to the server's file system.

        The request must include a multipart form with a file field.
        """
        try:
            reader = await request.multipart()
            files_uploaded = []

            while True:
                # Process each field in the multipart request
                field = await reader.next()
                if field is None:
                    break

                # Ensure the field contains a file
                if field.name != "file":
                    continue

                filename = field.filename
                if not filename:
                    continue

                # Create in-memory storage for the file
                with io.BytesIO() as filebytes:
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        filebytes.write(chunk)

                    # Save the file using the worker, preserving folder structure
                    local_filename = self._worker.upload(
                        filebytes.getvalue(),
                        Path(filename),
                    )
                    files_uploaded.append(local_filename)

            if len(files_uploaded) == 0:
                return web.Response(text="No files uploaded", status=400)

            if len(files_uploaded) == 1:
                responefile = files_uploaded[0]
            else:
                # get the most common path
                # Convert paths to parts and zip them to find the common prefix
                parts = [p.parts for p in files_uploaded]
                common_parts = []

                for components in zip(*parts):
                    # Check if all parts are the same at this level
                    if all(component == components[0] for component in components):
                        common_parts.append(components[0])
                    else:
                        break

                # Construct the common ancestor as a relative path
                responefile = Path(*common_parts)

            return web.Response(
                text=json.dumps({"file": responefile.as_posix()}),
                status=200,
                content_type="application/json",
            )

        except Exception as e:
            FUNCNODES_LOGGER.exception(e)
            return web.Response(text="Error processing folder upload", status=500)

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

    async def clear_old_messages(self):
        """
        Clears old messages from the message store.
        """
        now = time.time()
        for msg_id, (msg, timestamp) in list(self.message_store.items()):
            if now - timestamp > LARGE_MESSAGE_MEMORY_TIMEOUT:
                self.message_store.pop(msg_id)

    async def loop(self):
        """
        The main loop for the WebSocket server.
        """
        await self._assert_connection()
        await self.clear_old_messages()

    async def stop(self):
        """
        Stops the WebSocket server.
        """

        # close all clients
        for client in self.clients:
            await client.close(
                code=WSCloseCode.GOING_AWAY, message="Server shutting down"
            )

        self.message_store.clear()

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
        if not msg:
            return

        if len(msg) > MESSAGE_SIZE_BEFORE_REQUEST:
            msg_id = str(uuid.uuid4())
            self.ws_loop.message_store[msg_id] = (msg, time.time())
            # Construct a URL for the client to retrieve the message
            link = f"http://{self.host}:{self.port}/message/{msg_id}"
            wrapped_msg = json.dumps(
                {"type": "large_message", "url": link, "msg_id": msg_id}
            )
            msg_to_send = wrapped_msg
        else:
            msg_to_send = msg

        if websocket:
            try:
                await websocket.send_str(msg_to_send)
            except Exception as exc:
                self.logger.exception(exc)
        else:
            if self.ws_loop.clients:
                ans = await asyncio.gather(
                    *[client.send_str(msg_to_send) for client in self.ws_loop.clients],
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
