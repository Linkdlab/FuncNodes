from ...nodespace import LibShelf
from ...node import Node
from ...io import NodeInput, NodeOutput
from datetime import datetime


class IntegerInputNode(Node):
    node_id = "intip"
    input = NodeInput(type=int, required=True)
    output = NodeOutput(type=int)

    async def on_trigger(self):
        self.output.value = self.input.value
        return True


class FloatInputNode(Node):
    node_id = "floatip"
    input = NodeInput(type=float, required=True)
    output = NodeOutput(type=float)

    async def on_trigger(self):
        self.output.value = self.input.value
        return True


class StringInputNode(Node):
    node_id = "strip"
    input = NodeInput(type=str, required=True)
    output = NodeOutput(type=str)

    async def on_trigger(self):
        self.output.value = self.input.value
        return True


class BooleanInputNode(Node):
    node_id = "boolip"
    input = NodeInput(type=bool, required=True)
    output = NodeOutput(type=bool)

    async def on_trigger(self):
        self.output.value = self.input.value
        return True


try:
    import numpy as np

    dt_type = np.ndarray

    def now_getter():
        return np.datetime64(datetime.now())

except ImportError:
    dt_type = datetime
    now_getter = datetime.now


class DateTimeInputNode(Node):
    node_id = "datetimeip"
    input = NodeInput(type=datetime, required=True)
    output = NodeOutput(type=dt_type)

    async def on_trigger(self):
        self.output.value = self.input.value
        return True


class NowNode(Node):
    node_id = "now"

    output = NodeOutput(type=dt_type, trigger_on_get=True)

    async def on_trigger(self):
        self.output.value = now_getter()
        return True


LIB = LibShelf(
    name="input",
    nodes=[
        IntegerInputNode,
        FloatInputNode,
        StringInputNode,
        BooleanInputNode,
        DateTimeInputNode,
        NowNode,
    ],
    shelves=[],
)
