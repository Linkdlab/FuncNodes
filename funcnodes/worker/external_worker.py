from __future__ import annotations
from typing import Dict, List
from funcnodes.worker.loop import CustomLoop
from funcnodes.nodes.node_creator import (  # pylint: disable=unused-import
    NodeClassMixin,
    instance_nodefunction,
)

from weakref import WeakValueDictionary


class FuncNodesExternalWorker(NodeClassMixin, CustomLoop):
    RUNNING_WORKERS: Dict[str, WeakValueDictionary[str, FuncNodesExternalWorker]] = {}
    IS_ABSTRACT = True

    def __init__(self, workerid) -> None:
        super().__init__(delay=1)
        self.uuid = workerid
        if self.NODECLASSID not in FuncNodesExternalWorker.RUNNING_WORKERS:
            FuncNodesExternalWorker.RUNNING_WORKERS[
                self.NODECLASSID
            ] = WeakValueDictionary()
        FuncNodesExternalWorker.RUNNING_WORKERS[self.NODECLASSID][self.uuid] = self

    @classmethod
    def running_instances(cls) -> List[FuncNodesExternalWorker]:
        if cls.NODECLASSID not in FuncNodesExternalWorker.RUNNING_WORKERS:
            return []
        return list(FuncNodesExternalWorker.RUNNING_WORKERS[cls.NODECLASSID].values())
    