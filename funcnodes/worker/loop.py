from __future__ import annotations
from abc import ABC, abstractmethod
import asyncio
from typing import List
import logging
from funcnodes import NodeSpace


class CustomLoop(ABC):
    def __init__(self, delay=0.1, logger: logging.Logger | None = None) -> None:
        self._delay = delay
        if logger is None:
            logger = logging.getLogger(f"{self.__class__.__name__}")
        self._logger = logger
        self._running = True
        self._manager: LoopManager | None = None

    @property
    def manager(self) -> LoopManager | None:
        return self._manager

    @manager.setter
    def manager(self, manager: LoopManager):
        self._manager = manager

    @abstractmethod
    async def loop(self):
        """This method is called in a loop every <self.delay> seconds ."""

    async def _loop(self):
        return await self.loop()

    async def stop(self):
        self._running = False

    async def continuous_run(self):
        while self._running:
            try:
                # st = time.time()
                await self._loop()
                # t= time.time()-st
                # if t > 0.01:
                #    print(f"{self.__class__.__name__} took {t} seconds")
            except Exception as exc:  # pylint: disable=broad-except
                self._logger.exception(exc)
            await asyncio.sleep(self._delay)


class LoopManager:
    def __init__(self, worker) -> None:
        self._loops: List[CustomLoop] = []
        self._loop = asyncio.get_event_loop()
        self._worker = worker
        asyncio.set_event_loop(self._loop)
        self._tasks: List[asyncio.Task] = []
        self._running = False

    def add_loop(self, loop: CustomLoop):
        self._loops.append(loop)
        loop.manager = self
        t = self._loop.create_task(loop.continuous_run())
        self._tasks.append(t)
        return t

    def remove_loop(self, loop: CustomLoop):
        if loop in self._loops:
            idx = self._loops.index(loop)
            task = self._tasks.pop(idx)
            loop = self._loops.pop(idx)
            asyncio.run(loop.stop())
            task.cancel()

    def async_call(self, croutine: asyncio.Coroutine):
        return self._loop.create_task(croutine)

    def __del__(self):
        self.stop()

    def stop(self):

        for task in self._tasks:
            task.cancel()

        for loop in list(self._loops):
            self.remove_loop(loop)
        self._running = False

    def run_forever(self):
        asyncio.set_event_loop(self._loop)
        self._running = True

        async def _rf():
            while self._running:
                await asyncio.sleep(1)

        try:
            self._loop.run_until_complete(_rf())
        except KeyboardInterrupt:
            print("Interrupt received, shutting down.")
        finally:
            self.stop()


class NodeSpaceLoop(CustomLoop):
    def __init__(self, nodespace: NodeSpace, delay=0.005) -> None:
        super().__init__(delay)
        self._nodespace = nodespace

    async def loop(self):
        await self._nodespace.await_done()
