from ...nodespace import LibShelf
from ...node import Node
from ...io import NodeInput, NodeOutput
from .inputnodes import LIB as INPUT_LIB


class LengthNode(Node):
    node_id = "length"
    input = NodeInput(type=list, required=True)
    output = NodeOutput(type=int)

    async def on_trigger(self):
        self.output.value = len(self.input.value)
        return True


LIB = LibShelf(
    name="basic",
    nodes=[LengthNode],
    shelves=[INPUT_LIB],
)
