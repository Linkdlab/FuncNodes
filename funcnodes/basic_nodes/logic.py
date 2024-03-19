"""Logic Nodes for control flow and decision making."""

from funcnodes.node import Node, TriggerStack
from typing import Any, List
from funcnodes.io import NodeInput, NodeOutput, NoValue
import asyncio
from funcnodes.lib import module_to_shelf
import sys


class IfNode(Node):
    node_id = "if_node"
    node_name = "If"
    on_true = NodeOutput(id="on_true", type=Any)
    on_false = NodeOutput(id="on_false", type=Any)
    condition = NodeInput(id="condition", type=bool)
    input = NodeInput(id="input", type=Any)

    async def func(self, condition: bool, input: Any) -> None:
        if condition:
            self.outputs["on_true"].value = input
        else:
            self.outputs["on_false"].value = input


class WhileNode(Node):
    node_id = "while_node"
    node_name = "While"
    condition = NodeInput(id="condition", type=bool)
    input = NodeInput(id="input", type=Any)
    do = NodeOutput(id="do", type=Any)
    done = NodeOutput(id="done", type=Any)

    async def func(self, condition: bool, input: Any) -> None:
        if condition:
            self.outputs["do"].value = input
            self.request_trigger()
        else:
            self.outputs["done"].value = input


class WaitNode(Node):
    node_id = "wait_node"
    node_name = "Wait"
    delay = NodeInput(
        id="delay",
        type=float,
        required=True,
        default=1.0,
        does_trigger=False,
        render_options={"step": "0.1"},
        value_options={"min": 0.0},
    )
    input = NodeInput(id="input", type=Any)
    output = NodeOutput(id="output", type=Any)

    async def func(self, delay: float, input: Any) -> None:
        await asyncio.sleep(delay)
        self.outputs["output"].value = input


class ForNode(Node):
    node_id = "for_node"
    node_name = "For"
    input = NodeInput(id="input", type=List[Any])
    do = NodeOutput(id="do", type=Any)
    collector = NodeInput(id="collector", type=Any, does_trigger=False, required=False)
    done = NodeOutput(id="done", type=List[Any])

    async def func(self, input: list) -> None:
        results = []
        for i in input:
            self.outputs["do"].set_value(i, does_trigger=False)
            triggerstack = TriggerStack()

            await self.outputs["do"].trigger(triggerstack)
            await triggerstack
            results.append(self.inputs["collector"].value)
        self.outputs["done"].value = results


class CollectorNode(Node):
    node_id = "collector_node"
    node_name = "Collector"

    reset = NodeInput(id="reset", type=Any, does_trigger=True, required=False)
    input = NodeInput(id="input", type=Any)

    output = NodeOutput(id="output", type=List[Any])
    default_reset_inputs_on_trigger = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection = []

    async def func(self, input: Any, reset: Any = NoValue) -> None:
        if reset != NoValue:
            self.collection = []

        self.collection.append(input)
        self.outputs["output"].value = self.collection


NODE_SHELFE = module_to_shelf(sys.modules[__name__], name="logic")
