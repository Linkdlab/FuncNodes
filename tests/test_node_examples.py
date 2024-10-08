"""
Test examples
"""

import unittest
from funcnodes_core import run_until_complete
from funcnodes_basic.math_nodes import (
    value_node,
    add_node,
    greater_node,
    mod_node,
    equal_node,
    div_node,
    mul_node,
)
from funcnodes_basic.logic import IfNode, WhileNode
from funcnodes_core import get_deep_connected_nodeset


class TestExamples(unittest.IsolatedAsyncioTestCase):
    async def test_linear_add(self):
        N = 3
        preadd = add_node()
        preadd.inputs["a"].value = 1
        preadd.inputs["b"].value = 1
        adds = [preadd]

        for i in range(N):
            nadd = add_node()
            nadd.inputs["a"].c(preadd.outputs["out"])
            nadd.inputs["b"].value = 1
            preadd = nadd
            adds.append(nadd)

        await run_until_complete(*adds)

        self.assertEqual(adds[-1].outputs["out"].value, N + 2)

    async def test_3np1(self):
        N = 27
        n = N

        steps = []
        while n > 1:
            steps.append(n)
            if n % 2 == 0:
                n = int(n / 2)
            else:
                n = 3 * n + 1
        steps.append(1)

        start = value_node()

        greater_node_ins = greater_node()
        greater_node_ins.inputs["a"].c(start.outputs["out"])
        greater_node_ins.inputs["b"].value = 1

        while_node = WhileNode(
            reset_inputs_on_trigger=True,
            io_options={
                "condition": {"does_trigger": False},
            },
        )
        while_node.inputs["condition"].c(greater_node_ins.outputs["out"])
        while_node.inputs["input"].c(start.outputs["out"])

        mod = mod_node()
        mod.inputs["a"].c(while_node.outputs["do"])
        mod.inputs["b"].value = 2

        eq = equal_node()
        eq.inputs["a"].c(mod.outputs["out"])
        eq.inputs["b"].value = 0

        if_node = IfNode(
            reset_inputs_on_trigger=True,
            io_options={
                "condition": {"does_trigger": False},
            },
        )
        if_node.inputs["condition"].c(eq.outputs["out"])
        if_node.inputs["input"].c(while_node.outputs["do"])

        div = div_node()
        div.inputs["a"].c(if_node.outputs["on_true"])
        div.inputs["b"].value = 2

        start.inputs["value"].c(div.outputs["out"])

        mul = mul_node()
        mul.inputs["a"].c(if_node.outputs["on_false"])
        mul.inputs["b"].value = 3

        add = add_node()
        add.inputs["a"].c(mul.outputs["out"])
        add.inputs["b"].value = 1

        start.inputs["value"].c(add.outputs["out"])

        await run_until_complete(start)

        nodeteps = []

        def _add_step(src, result):
            if not nodeteps or nodeteps[-1] != result:
                nodeteps.append(result)
            if len(nodeteps) > len(steps):
                raise ValueError(f"done too many steps: {nodeteps}")

        start.outputs["out"].on("after_set_value", _add_step)

        start.inputs["value"].value = N
        await run_until_complete(*get_deep_connected_nodeset(start))

        self.assertEqual(nodeteps, steps)
