from __future__ import annotations
from abc import abstractmethod
from typing import (
    List,
    Callable,
    Tuple,
    Awaitable,
)
import json

from funcnodes import (
    NodeSpace,
    JSONEncoder,
)
import traceback
from .worker import (
    Worker,
    ProgressStateMessage,
    NodeSpaceEvent,
    ErrorMessage,
    CmdMessage,
    ResultMessage,
    WorkerJson,
)


class RemoteWorkerJson(WorkerJson):
    pass


class RemoteWorker(Worker):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._messagehandlers: List[
            Callable[[dict], Awaitable[Tuple[bool | None, str]]]
        ] = []

    async def set_progress_state(self, *args, **kwargs):
        await super().set_progress_state(*args, **kwargs)
        await self.send(ProgressStateMessage(type="progress", **self._progress_state))

    async def send(self, data, **kwargs):
        if not isinstance(data, str):
            data = json.dumps(data, cls=JSONEncoder)
        # self.logger.debug(f"Sending message {data}")
        await self.sendmessage(data, **kwargs)

    @abstractmethod
    async def sendmessage(self, msg: str, **kwargs):
        """send a message to the frontend"""

    def _on_nodespaceevent(self, event, src: NodeSpace, **kwargs):
        if event in {
            "before_set_value",
            "before_request_trigger",
            "after_request_trigger",
            "before_disconnect",
            "before_connect",
            "before_trigger",
            "after_trigger",
            "before_unforward",
            "before_forward",
        }:
            return
        if event == "node_trigger_error":
            self.logger.exception(kwargs["error"])
        event_bundle: NodeSpaceEvent = {
            "type": "nsevent",
            "event": event,
            "data": kwargs,
        }
        if event in ("after_set_value", "before_set_value"):
            event_bundle = JSONEncoder.apply_custom_encoding(event_bundle, preview=True)

        self.loop_manager.async_call(self.send(event_bundle))
        return event_bundle

    def _on_nodespaceerror(
        self,
        error: Exception,
        src: NodeSpace,
    ):
        """handle nodespace errors"""
        error_bundle = {
            "type": "error_event",
            "error": repr(error),
            "tb": list(traceback.TracebackException.from_exception(error).format()),
        }
        self.logger.exception(error)
        self.loop_manager.async_call(self.send(error_bundle))

    async def recieve_message(self, json_msg: dict, **sendkwargs):
        self.logger.debug(f"Recieved message {json_msg}")
        if "type" not in json_msg:
            return
        try:
            if json_msg["type"] == "cmd":
                await self._handle_cmd_msg(json_msg, **sendkwargs)
        except Exception as e:
            self.logger.exception(e)
            await self.send(
                ErrorMessage(
                    type="error",
                    error=str(e),
                    tb=traceback.format_exception(e),
                    id=json_msg.get("id"),
                )
            )

    async def _handle_cmd_msg(self, json_msg: CmdMessage, **sendkwargs):
        result = await self.run_cmd(json_msg)
        await self.send(
            ResultMessage(type="result", result=result, id=json_msg.get("id")),
            **sendkwargs,
        )

    def update_config(self, config: WorkerJson) -> RemoteWorkerJson:
        return super().update_config(config)
