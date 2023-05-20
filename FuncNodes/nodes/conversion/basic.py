from ...nodespace import LibShelf
from ...node import Node
from ...io import NodeInput, NodeOutput


class Byte2StringNode(Node):
    node_id = "byte2str"
    input = NodeInput(type=bytes, required=True)
    output = NodeOutput(type=str)

    async def on_trigger(self):
        self.output.value = self.input.value.decode("utf-8")
        return True


LIB = LibShelf(
    name="basic",
    nodes=[Byte2StringNode],
    shelves=[],
)
