from __future__ import annotations
from abc import ABC, abstractmethod
import asyncio
from typing import List
import logging
from funcnodes.nodespace import NodeSpace


class CustomLoop(ABC):
    def __init__(self, delay=0.1, logger: logging.Logger | None = None) -> None:
        self._delay = delay
        if logger is None:
            logger = logging.getLogger(f"{self.__class__.__name__}")
        self._logger = logger
        self._running = True

    @abstractmethod
    async def loop(self):
        """This method is called in a loop every <self.delay> seconds ."""

    async def _loop(self):
        return await self.loop()

    def stop(self):
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
    def __init__(self) -> None:
        self._loops: List[CustomLoop] = []
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

    def add_loop(self, loop: CustomLoop):
        self._loops.append(loop)
        self._loop.create_task(loop.continuous_run())

    def remove_loop(self, loop: CustomLoop):
        self._loops.remove(loop)
        loop.stop()

    def run_forever(self):
        asyncio.set_event_loop(self._loop)

        async def _rf():
            while True:
                await asyncio.sleep(1)

        try:
            self._loop.run_until_complete(_rf())
        except KeyboardInterrupt:
            print("Interrupt received, shutting down.")
        finally:
            self._loop.close()


class NodeSpaceLoop(CustomLoop):
    def __init__(self, nodespace: NodeSpace, delay=0.005) -> None:
        super().__init__(delay)
        self._nodespace = nodespace

    async def loop(self):
        await self._nodespace.await_done()
