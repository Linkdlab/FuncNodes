"""
Test examples
"""

import unittest
from funcnodes.utils import run_until_complete
from funcnodes.io import NoValue
import asyncio


class TestExamples(unittest.IsolatedAsyncioTestCase):
    async def test_if_node(self):
        from funcnodes.basic_nodes.logic import IfNode

        ifnode = IfNode()
        ifnode.inputs["condition"].value = True
        ifnode.inputs["input"].value = 1

        await run_until_complete(ifnode)

        self.assertEqual(ifnode.outputs["on_true"].value, 1)
        self.assertEqual(ifnode.outputs["on_false"].value, NoValue)

        ifnode.inputs["condition"].value = False
        ifnode.inputs["input"].value = 2

        await run_until_complete(ifnode)
        self.assertEqual(ifnode.outputs["on_true"].value, 1)
        self.assertEqual(ifnode.outputs["on_false"].value, 2)

    async def test_while_node(self):
        from funcnodes.basic_nodes.logic import WhileNode
        from funcnodes.basic_nodes.math import add_node

        while_node = WhileNode()
        while_node.inputs["input"].value = 1
        addnode = add_node()
        addnode.inputs["a"].value = 1
        addnode.inputs["b"].c(while_node.outputs["do"])
        addnode.outputs["out"].c(while_node.inputs["input"])
        while_node.inputs["condition"].value = True
        results = []

        async def _t():
            await asyncio.sleep(0.5)
            while_node.inputs["condition"].value = False

        while_node.on(
            "after_trigger",
            lambda **msg: results.append(while_node.outputs["do"].value),
        )
        await _t()
        await run_until_complete(while_node)

        self.assertGreater(len(results), 5)
        for i, r in enumerate(results):
            self.assertEqual(r, i + 1)

    async def test_for_node(self):
        from funcnodes.basic_nodes.logic import ForNode

        for_node = ForNode()

        for_node.inputs["input"].value = [1, 2, 3, 4, 5]
        for_node.inputs["collector"].c(for_node.outputs["do"])
        await for_node.triggerstack

        self.assertEqual(for_node.outputs["done"].value, [1, 2, 3, 4, 5])
