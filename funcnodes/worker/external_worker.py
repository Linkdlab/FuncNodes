from __future__ import annotations
from typing import Dict, List, TypedDict
from funcnodes.worker.loop import CustomLoop
from funcnodes import NodeClassMixin, JSONEncoder, Encdata, EventEmitterMixin
from weakref import WeakValueDictionary


class FuncNodesExternalWorker(NodeClassMixin, EventEmitterMixin, CustomLoop):
    """
    A class that represents an external worker with a loop and nodeable methods.
    """

    RUNNING_WORKERS: Dict[str, WeakValueDictionary[str, FuncNodesExternalWorker]] = {}
    IS_ABSTRACT = True

    def __init__(self, workerid) -> None:
        """
        Initializes the FuncNodesExternalWorker class.

        Args:
          workerid (str): The id of the worker.
        """
        super().__init__(
            delay=1,
        )
        self.uuid = workerid
        if self.NODECLASSID not in FuncNodesExternalWorker.RUNNING_WORKERS:
            FuncNodesExternalWorker.RUNNING_WORKERS[self.NODECLASSID] = (
                WeakValueDictionary()
            )
        FuncNodesExternalWorker.RUNNING_WORKERS[self.NODECLASSID][self.uuid] = self

    @classmethod
    def running_instances(cls) -> List[FuncNodesExternalWorker]:
        """
        Returns a list of running instances of FuncNodesExternalWorker.

        Returns:
          List[FuncNodesExternalWorker]: A list of running instances of FuncNodesExternalWorker.

        Examples:
          >>> FuncNodesExternalWorker.running_instances()
          [FuncNodesExternalWorker("worker1"), FuncNodesExternalWorker("worker2")]
        """
        if cls.NODECLASSID not in FuncNodesExternalWorker.RUNNING_WORKERS:
            return []

        res = []

        for ins in FuncNodesExternalWorker.RUNNING_WORKERS[cls.NODECLASSID].values():
            if ins.running:
                res.append(ins)
        return res

    async def stop(self):
        self.emit("stopping")
        self.cleanup()
        await super().stop()


class FuncNodesExternalWorkerJson(TypedDict):
    """
    A class that represents a JSON object for FuncNodesExternalWorker.
    """

    uuid: str
    nodeclassid: str
    running: bool
    name: str


def encode_external_worker(obj, preview=False):  # noqa: F841
    if isinstance(obj, FuncNodesExternalWorker):
        return Encdata(
            data=FuncNodesExternalWorkerJson(
                uuid=obj.uuid,
                nodeclassid=obj.NODECLASSID,
                running=obj.running,
                name=obj.name,
            ),
            handeled=True,
            done=True,
            continue_preview=False,
        )
    return Encdata(data=obj, handeled=False)


JSONEncoder.add_encoder(encode_external_worker, [FuncNodesExternalWorker])


__all__ = [
    "FuncNodesExternalWorker",
    # "instance_nodefunction"
]
