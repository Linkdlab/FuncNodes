from __future__ import annotations
from typing import List, Optional

# import socket
import json

# import traceback
import asyncio
from funcnodes import NodeSpace, FUNCNODES_LOGGER
from funcnodes.worker import CustomLoop
from .remote_worker import RemoteWorker, RemoteWorkerJson

STARTPORT = 9382
ENDPORT = 9482


class SocketWorkerJson(RemoteWorkerJson):
    """
    TypedDict for TCP socket worker configuration.

    Attributes:
      host (str): The host address for the TCP socket server.
      port (int): The port number for the TCP socket server.
    """

    host: str
    port: int


class SocketLoop(CustomLoop):
    """
    Custom loop for TCP socket worker.

    Args:
      worker (SocketWorker): The TCP socket worker.
      host (str): The host address for the socket server.
      port (int): The port number for the socket server.
      delay (int): The delay between loop iterations.
      *args: Additional arguments.
      **kwargs: Additional keyword arguments.

    Attributes:
      server (asyncio.Server | None): The TCP socket server.
      clients (List[asyncio.StreamWriter]): The list of connected clients.

    Methods:
      loop: The main loop for the TCP socket server.
      stop: Stops the TCP socket server.
    """

    def __init__(
        self,
        worker: SocketWorker,
        host: str = "127.0.0.1",
        port: int = STARTPORT,
        delay=5,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, delay=delay, **kwargs)
        self._host = host
        self._port = port
        self.server: Optional[asyncio.Server] = None
        self._worker = worker
        self.clients: List[asyncio.StreamWriter] = []

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """
        Handles a new client connection.

        Args:
          reader (asyncio.StreamReader): The stream reader for the client.
          writer (asyncio.StreamWriter): The stream writer for the client.
        """
        self.clients.append(writer)
        try:
            buffer = b""
            while True:
                data = await reader.read(1024)  # Read up to 1024 bytes
                if not data:
                    break  # Client disconnected
                buffer += data
                while self._worker.DELIMITER in buffer:
                    message, buffer = buffer.split(self._worker.DELIMITER, 1)

                    try:
                        json_msg = json.loads(message.decode())  # Decode JSON data
                    except json.JSONDecodeError:
                        continue
                    await self._worker.recieve_message(json_msg, writer=writer)

        except Exception as e:
            FUNCNODES_LOGGER.exception(e)
        finally:
            print("Client disconnected")
            self.clients.remove(writer)
            writer.close()
            await writer.wait_closed()

    async def _assert_connection(self):
        """
        Asserts that the TCP socket server is running.
        """
        while True:
            try:
                if self.server is None:
                    self.server = await asyncio.start_server(
                        self._handle_connection, self._host, self._port
                    )
                    self._worker.write_config()
                return
            except OSError:
                self._port += 1
                if self._port > ENDPORT:
                    self._port = STARTPORT
                    raise Exception("No free ports available")

    async def loop(self):
        """
        The main loop for the TCP socket server.
        """
        await self._assert_connection()

    async def stop(self):
        """
        Stops the TCP socket server.
        """
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
        await super().stop()


class SocketWorker(RemoteWorker):
    """
    Remote worker for TCP socket connections.
    """

    DELIMITER = b"\x00\x00\x00\x00\x00\x00\x00\x00"

    def __init__(
        self,
        host=None,
        port=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        c = self.config
        if c is None:
            c = {}

        if host is None:
            host = c.get("host", "127.0.0.1")
        if port is None:
            port = c.get("port", STARTPORT)
        self.socket_loop = SocketLoop(host=host, port=port, worker=self)
        self.loop_manager.add_loop(self.socket_loop)

    async def sendmessage(
        self, msg: str, writer: Optional[asyncio.StreamWriter] = None
    ):
        """Sends a message to the frontend."""
        bytemessage = msg.encode()

        async def _send(writer):
            writer.write(bytemessage + self.DELIMITER)
            await writer.drain()

        if writer:
            try:
                await _send(writer)
            except Exception:
                pass
        else:
            clients = self.socket_loop.clients

            if clients:
                await asyncio.gather(
                    *[_send(client) for client in clients],
                    return_exceptions=True,
                )

    def _on_nodespaceerror(self, error: Exception, src: NodeSpace):
        """Handles an error in a NodeSpace."""
        return super()._on_nodespaceerror(error, src)

    def _on_nodespaceevent(self, event: str, src: NodeSpace, **kwargs):
        """Handles an event in a NodeSpace."""
        return super()._on_nodespaceevent(event, src, **kwargs)

    def stop(self):
        """Stops the SocketWorker."""
        super().stop()

    def update_config(self, config: RemoteWorkerJson) -> SocketWorkerJson:
        """
        Updates a configuration dictionary for the SocketWorker.

        Returns:
          SocketWorkerJson: The configuration dictionary for the SocketWorker.
        """
        d = SocketWorkerJson(
            **{
                **super().update_config(config),
                **dict(
                    host="127.0.0.1",
                    port=STARTPORT,
                ),
            }
        )
        if hasattr(self, "socket_loop"):
            d["host"] = self.socket_loop._host
            d["port"] = self.socket_loop._port

        return d

    def exportable_config(self) -> dict:
        conf = super().exportable_config()
        conf.pop("host", None)
        conf.pop("port", None)
        return conf

    @staticmethod
    def init_and_run_forever(
        *args,
        **kwargs,
    ):
        worker = SocketWorker(*args, **kwargs)
        worker.run_forever()
