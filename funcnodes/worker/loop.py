from __future__ import annotations
from abc import ABC, abstractmethod
import asyncio
from typing import List, Optional
import logging
from funcnodes_core import NodeSpace
import time

MIN_DELAY = 0.1
MIN_DEF = 0.1


class CustomLoop(ABC):
    def __init__(self, delay=0.1, logger: logging.Logger | None = None) -> None:
        if delay < MIN_DELAY:
            delay = MIN_DELAY
        self._delay = delay
        if logger is None:
            logger = logging.getLogger(f"{self.__class__.__name__}")
        self._logger = logger
        self._running = False
        self._stopped = False
        self._manager: Optional[LoopManager] = None
        self._stop_event = asyncio.Event()

    @property
    def manager(self) -> Optional[LoopManager]:
        return self._manager

    @manager.setter
    def manager(self, manager: Optional[LoopManager]):
        if manager is not None and self._manager is not None:
            raise ValueError("Loop already has a manager")

        if manager is None and self._manager is not None:
            self._manager.remove_loop(self)

        if manager is self._manager:
            return

        self._manager = manager

    @abstractmethod
    async def loop(self):
        """This method is called in a loop every <self.delay> seconds ."""

    async def _loop(self):
        return await self.loop()

    async def stop(self):
        self._running = False
        self.manager = None
        await asyncio.sleep(min(self._delay, MIN_DEF) * 1.25)
        self._stopped = True

    @property
    def running(self):
        return self._running

    @property
    def stopped(self):
        return self._stopped and not self._running

    async def continuous_run(self):
        last_run = 0
        self._running = True
        while self.running:
            try:
                if time.time() - self._delay > last_run:
                    await self._loop()
                    last_run = time.time()
            except Exception as exc:  # pylint: disable=broad-except
                self._logger.exception(exc)

            await asyncio.sleep(min(self._delay, MIN_DEF))


class LoopManager:
    def __init__(self, worker) -> None:
        self._loops: List[CustomLoop] = []
        self._loop: asyncio.AbstractEventLoop = None  # type: ignore
        self._worker = worker
        self.reset_loop()
        self._tasks: List[asyncio.Task] = []
        self._running = False
        self._loops_to_add = []

    def reset_loop(self):
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError as e:
            if str(e).startswith("There is no current event loop in thread"):
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            else:
                raise

    def add_loop(self, loop: CustomLoop):
        if self._running:
            self._loops.append(loop)
            loop.manager = self

            async def looprunner():
                await loop.continuous_run()
                self.remove_loop(loop)

            t = self._loop.create_task(looprunner())
            self._tasks.append(t)
            return t
        else:
            self._loops_to_add.append(loop)

    def remove_loop(self, loop: CustomLoop):
        # check if self._loop is running as the current loop
        is_running = (
            self._loop.is_running()
        )  # and asyncio.get_event_loop() == self._loop

        if loop.running:
            loop._running = False  # set this to false prevent recursion
            try:
                if not is_running:
                    self._loop.run_until_complete(loop.stop())
                else:
                    _ = self._loop.create_task(loop.stop())
            except Exception as e:
                raise e

        if loop in self._loops:
            idx = self._loops.index(loop)
            task = self._tasks.pop(idx)
            self._loops.pop(idx)
            task.cancel()

    def async_call(self, croutine: asyncio.Coroutine):
        return self._loop.create_task(croutine)

    def __del__(self):
        self.stop()

    def stop(self):
        self._running = False
        for task in self._tasks:
            task.cancel()

        for loop in list(self._loops):
            self.remove_loop(loop)

    @property
    def running(self):
        return self._running

    def _prerun(self):
        self._worker.logger.info("Setup loop manager to run")
        self._running = True
        loops2add = list(self._loops_to_add)
        self._loops_to_add = []
        for loop in loops2add:
            self.add_loop(loop)
        self._worker.logger.info("Starting loop manager")

    def run_forever(self):
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        asyncio.set_event_loop(self._loop)
        self._prerun()

        async def _rf():
            while self.running:
                await asyncio.sleep(1)

        try:
            self._loop.run_until_complete(_rf())
        except KeyboardInterrupt:
            print("Interrupt received, shutting down.")
            self._worker.stop()
        except Exception as e:
            raise e
        finally:
            self.stop()
            if running_loop is not None:
                asyncio.set_event_loop(running_loop)

    async def run_forever_async(self):
        self._prerun()

        while self.running:
            await asyncio.sleep(1)


class NodeSpaceLoop(CustomLoop):
    def __init__(self, nodespace: NodeSpace, delay=0.005) -> None:
        super().__init__(delay)
        self._nodespace = nodespace

    async def loop(self):
        await self._nodespace.await_done()
