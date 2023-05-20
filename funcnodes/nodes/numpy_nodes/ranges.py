import numpy as np

from funcnodes.io import NodeInput, NodeOutput
from funcnodes.node import Node
from ...nodespace import LibShelf
from .types import NdArrayType


class ARangeNode(Node):
    node_id = "np.arange"
    start = NodeInput(type=float, default=0, positional=True)
    stop = NodeInput(type=float, default=1, positional=True)
    step = NodeInput(type=float, default=1, positional=True)

    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.arange(self.start.value, self.stop.value, self.step.value)
        return True


class LinspaceNode(Node):
    node_id = "np.linspace"
    start = NodeInput(type=float, default=0, positional=True)
    stop = NodeInput(type=float, default=1, positional=True)
    num = NodeInput(type=int, default=50, positional=True)

    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.linspace(self.start.value, self.stop.value, self.num.value)
        return True


LIB = LibShelf(
    name="ranges",
    nodes=[ARangeNode, LinspaceNode],
    shelves=[],
)
