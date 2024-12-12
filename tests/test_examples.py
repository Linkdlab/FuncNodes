import unittest
import funcnodes as fn
from funcnodes_basic.math_nodes import add_node

fn.config.IN_NODE_TEST = True


class TestExamples(unittest.IsolatedAsyncioTestCase):
    async def test_simple_node_creation(self):
        add_node_ins = add_node()  # basically lambda a, b: a+b

        add_node_ins.inputs["a"].value = 2  # sets the input of a to 1
        self.assertFalse(add_node_ins.in_trigger)
        self.assertFalse(add_node_ins.ready_to_trigger())

        add_node_ins.inputs["b"].value = 3  # sets the input of a to 1
        self.assertFalse(add_node_ins.ready_to_trigger())
        self.assertTrue(add_node_ins.in_trigger)

        self.assertEqual(add_node_ins.outputs["out"].value, fn.NoValue)
        await add_node_ins
        self.assertEqual(add_node_ins.outputs["out"].value, 5)

    async def test_simple_connection(self):
        add_node1 = add_node()
        add_node2 = add_node()

        add_node1.outputs["out"].connect(add_node2.inputs["a"])
        add_node1.o["out"].c(add_node2.i["a"])
        add_node1.outputs["out"] > add_node2.inputs["a"]
