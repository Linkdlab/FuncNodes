from funcnodes.node import Node, TriggerStack
from typing import Any
from funcnodes.io import NodeInput, NodeOutput


class IfNode(Node):
    node_id = "if_node"
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


class ForNode(Node):
    node_id = "for_node"
    input = NodeInput(id="input", type=list)
    do = NodeOutput(id="do", type=Any)
    collector = NodeInput(id="collector", type=Any, does_trigger=False, required=False)
    done = NodeOutput(id="done", type=Any)

    async def func(self, input: list) -> None:
        results = []
        for i in input:
            self.outputs["do"].set_value(i, does_trigger=False)
            triggerstack = TriggerStack()

            await self.outputs["do"].trigger(triggerstack)
            await triggerstack
            results.append(self.inputs["collector"].value)
        self.outputs["done"].value = results
