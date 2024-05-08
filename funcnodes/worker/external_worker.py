from __future__ import annotations
from typing import Dict, List
from funcnodes.worker.loop import CustomLoop
from funcnodes import NodeClassMixin  # , instance_nodefunction
from weakref import WeakValueDictionary


class FuncNodesExternalWorker(NodeClassMixin, CustomLoop):
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
        return list(FuncNodesExternalWorker.RUNNING_WORKERS[cls.NODECLASSID].values())


__all__ = [
    "FuncNodesExternalWorker",
    # "instance_nodefunction"
]
