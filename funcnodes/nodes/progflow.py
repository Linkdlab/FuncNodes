from typing import Any, List
from ..node import Node, NodeInput, NodeOutput, TriggerQueue
from ..nodespace import LibShelf
import asyncio
from time import perf_counter as _deltatimer


class IfNode(Node):

    """Node that implements an if-statement"""

    node_id = "if"
    condition = NodeInput(type=bool)
    input = NodeInput(required=True)
    then = NodeOutput()
    else_ = NodeOutput()

    async def on_trigger(self):
        if self.condition.value:
            self.then.value = self.input.value
            self.else_.value = None

        else:
            self.then.value = None
            self.else_.value = self.input.value
        return True


class WaitNode(Node):
    node_id = "wait"
    delay = NodeInput(type=float, required=True, default_value=1.0, does_trigger=False)
    input = NodeInput(required=True)
    output = NodeOutput()

    async def on_trigger(self):
        delay = self.delay.value
        if delay > 0:
            if delay > 1:
                start = _deltatimer()
                remaining = delay
                while remaining > 0 and self.enabled:
                    await asyncio.sleep(min(remaining, 0.1))
                    remaining = delay - (_deltatimer() - start)
            else:
                await asyncio.sleep(self.delay.value)
        self.output.value = self.input.value
        self.output.mark_for_trigger()
        return True


class WhileNode(Node):
    node_id = "while"
    condition = NodeInput(
        type=bool, required=True, default_value=False, does_trigger=False
    )
    input = NodeInput(required=True)
    output = NodeOutput()

    async def on_trigger(self):
        while self.condition.value and self.enabled:
            self.output.value = self.input.value
            tq = TriggerQueue()
            self.output.trigger(trigger_queue=tq)
            await tq.await_done()
            await asyncio.sleep(0.05)
        return True


class ManyInEachOutNode(Node):
    node_id = "manyineachout"
    manyins: List[NodeInput] = []
    out = NodeOutput(type=Any)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manyins = [ip for ip in self.get_inputs()]

    async def on_trigger(self):
        input_values = []
        for input in self.manyins:
            v = input.value_or_none
            if v is not None:
                input_values.append(v)
                input.set_value(None, quiet=True, mark_for_trigger=False)
        for v in input_values:
            if self.disabled:
                break

            self.out.value = v
            tq = TriggerQueue()
            self.out.trigger(trigger_queue=tq)
            await tq.await_done()
            # self.out.trigger()
            # tasklist = []
            # for node in self.out.get_other_nodes():
            #    tasklist.append(node.await_done())
            # await asyncio.gather(*tasklist)

        return True


class MergeInputNode(Node):
    node_id = "mergeip"
    mergeinputs: List[NodeInput] = []
    out = NodeOutput(type=list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mergeinputs = [ip for ip in self.get_inputs()]

    async def on_trigger(self):
        merged_list = []
        for input in self.mergeinputs:
            if self.disabled:
                break
            v = input.value_or_none
            if v is not None:
                merged_list.append(v)
        self.out.value = merged_list

        return True

    def add_mergeinput(
        self,
    ):
        ip = NodeInput(type=Any, required=False)
        self.add_input(ip)
        self.mergeinputs.append(ip)

    def remove_mergeinput(self, index: int):
        ip = self.mergeinputs.pop(index)
        self.remove_input(ip)


class ForNode(Node):
    node_id = "fornode"

    input = NodeInput(required=True, type=list)
    collector = NodeInput(type=Any, requeired=True, does_trigger=False)
    do = NodeOutput(type=Any)
    output = NodeOutput(type=list)

    async def on_trigger(self):
        outputs = []
        for v in self.input.value:
            if self.disabled:
                break
            self.do.value = v
            tq = TriggerQueue()
            self.do.trigger(trigger_queue=tq)
            await tq.await_done()
            outputs.append(self.collector.value)
        self.output.value = outputs
        return True


class CollectorNode(Node):
    node_id = "collectornode"
    input = NodeInput(required=True, type=Any)
    reset = NodeInput(type=Any, default_value=None)
    output = NodeOutput(type=list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collected = []

    async def on_trigger(self):
        if self.reset.value_or_none is not None:
            self.collected = []
            self.reset.value = None
        self.collected.append(self.input.value)
        self.output.value = self.collected
        return True

    async def clear(self):
        self.output.value = []


LIB = LibShelf(
    name="ProgFlow",
    nodes=[
        IfNode,
        MergeInputNode,
        ManyInEachOutNode,
        ForNode,
        WaitNode,
        WhileNode,
        CollectorNode,
    ],
    shelves=[],
)
