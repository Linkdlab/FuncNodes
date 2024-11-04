from typing import Optional, Type
from aiohttp import (
    web,
    log as aiohttp_log,
    web_log as aiohttp_web_log,
    abc as aiohttp_abc,
)
from aiohttp.typedefs import Handler
from enum import Enum
import funcnodes as fn
import ssl
import os
import logging
import asyncio
import subprocess_monitor
import threading
import webbrowser
import time


class Methods(Enum):
    GET = "GET"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"
    POST = "POST"
    PUT = "PUT"


def _open_browser(port: int, host: str = "localhost", delay=1.0):
    time.sleep(delay)
    webbrowser.open(f"http://{host}:{port}")


class BaseServer:
    STATIC_PATH = None
    STATIC_URL = "/static"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        worker_manager_host: Optional[str] = None,
        worker_manager_port: Optional[int] = None,
        worker_manager_ssl: Optional[bool] = None,
        start_worker_manager=True,
        static_path: Optional[str] = None,
        static_url: Optional[str] = None,
    ) -> None:
        if worker_manager_host is None:
            worker_manager_host = fn.config.CONFIG["worker_manager"]["host"]

        if worker_manager_port is None:
            worker_manager_port = fn.config.CONFIG["worker_manager"]["port"]

        if worker_manager_ssl is None:
            worker_manager_ssl = fn.config.CONFIG["worker_manager"].get("ssl", False)

        self.start_worker_manager = start_worker_manager
        self.worker_manager_ssl = worker_manager_ssl
        self.worker_manager_host = worker_manager_host
        self.worker_manager_port = worker_manager_port
        self.host = host
        self.port = port
        self.app = web.Application()
        self.ssl_context = None
        self._is_running_lock = asyncio.Lock()
        self._shutdown_signal = asyncio.Event()
        self._is_running = False
        self.runner = None
        self.site = None

        if static_path is not None:
            self.static_path = static_path
        else:
            self.static_path = self.STATIC_PATH

        if static_url is not None:
            self.static_url = static_url
        else:
            self.static_url = self.STATIC_URL

        self.add_route(Methods.GET, "/worker_manager", self.get_worker_manager)

        self.add_route(Methods.GET, "/", self.index)

        if self.static_path:
            self.add_route(
                Methods.GET, self.static_url + "/{filename:.*}", self.serve_static_file
            )

    def add_route(self, method: Methods, path: str, handler: Handler):
        if method == Methods.GET:
            self.app.router.add_get(path, handler)
        elif method == Methods.POST:
            self.app.router.add_post(path, handler)
        elif method == Methods.PUT:
            self.app.router.add_put(path, handler)

        elif method == Methods.DELETE:
            self.app.router.add_delete(path, handler)

        elif method == Methods.PATCH:
            self.app.router.add_patch(path, handler)

    def set_ssl_context(self, certfile, keyfile):
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ssl_context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    async def shutdown(self):
        print("Shutting down server")
        async with self._is_running_lock:
            self._is_running = False
            self._shutdown_signal.set()

    async def _run(
        self,
        *,
        shutdown_timeout: float = 60.0,
        keepalive_timeout: float = 75.0,
        backlog: int = 128,
        access_log_class: Type[
            aiohttp_abc.AbstractAccessLogger
        ] = aiohttp_web_log.AccessLogger,
        access_log_format: str = aiohttp_web_log.AccessLogger.LOG_FORMAT,
        access_log: Optional[logging.Logger] = aiohttp_log.access_logger,
        handle_signals: bool = True,
        reuse_address: Optional[bool] = None,
        reuse_port: Optional[bool] = None,
        handler_cancellation: bool = False,
    ):
        self.runner = web.AppRunner(
            self.app,
            handle_signals=handle_signals,
            access_log_class=access_log_class,
            access_log_format=access_log_format,
            access_log=access_log,
            keepalive_timeout=keepalive_timeout,
            shutdown_timeout=shutdown_timeout,
            handler_cancellation=handler_cancellation,
        )

        await self.runner.setup()

        try:
            self.site = web.TCPSite(
                self.runner,
                host=self.host,
                port=self.port,
                ssl_context=self.ssl_context,
                backlog=backlog,
                reuse_address=reuse_address,
                reuse_port=reuse_port,
            )

            await self.site.start()
            async with self._is_running_lock:
                self._is_running = True
                self._shutdown_signal.clear()
            print(f"Server started at http://{ self.host or '127.0.0.1' }:{self.port}")

            try:
                await self._shutdown_signal.wait()
            except (
                KeyboardInterrupt,
                asyncio.CancelledError,
                asyncio.TimeoutError,
            ):
                print("AAAA")
                await self.shutdown()
            while self._is_running:
                try:
                    await asyncio.sleep(1)
                except (
                    KeyboardInterrupt,
                    asyncio.CancelledError,
                    asyncio.TimeoutError,
                ):
                    await self.shutdown()
        finally:
            await self.runner.cleanup()

    def run(self, loop=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()

        loop.run_until_complete(self._run(**kwargs))

    async def get_worker_manager(self, request):
        if self.start_worker_manager:
            await fn.worker.worker_manager.assert_worker_manager_running(
                host=self.worker_manager_host,
                port=self.worker_manager_port,
                ssl=self.worker_manager_ssl,
            )

        return web.Response(
            text=(
                f"ws{'s' if self.worker_manager_ssl else ''}://"
                f"{self.worker_manager_host}:{self.worker_manager_port}"
            )
        )

    async def serve_static_file(self, request):
        if self.static_path is None:
            return web.Response(text="No static path set.", status=404)
        filename = request.match_info["filename"]
        path = os.path.join(self.static_path, filename)
        return web.FileResponse(path)

    async def index(self, request):
        return web.Response(text="No index route set.", status=404)

    @classmethod
    def run_server(
        cls,
        port=8029,
        open_browser=True,
        worker_manager_host: Optional[str] = None,
        worker_manager_port: Optional[int] = None,
        worker_manager_ssl: Optional[bool] = None,
        start_worker_manager=True,
    ):
        ins = cls(
            port=port,
            worker_manager_host=worker_manager_host,
            worker_manager_port=worker_manager_port,
            worker_manager_ssl=worker_manager_ssl,
            start_worker_manager=start_worker_manager,
        )

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        def _shutdown():
            async def __shutdown():
                await asyncio.sleep(5)
                await ins.shutdown()

            loop.create_task(__shutdown())

        if os.environ.get("SUBPROCESS_MONITOR_PORT", None) is not None:
            if not os.environ.get("SUBPROCESS_MONITOR_KEEP_RUNNING"):
                subprocess_monitor.call_on_manager_death(
                    _shutdown,
                )

        if open_browser:
            threading.Thread(target=_open_browser, args=(port,), daemon=True).start()

        ins.run(loop=loop)
