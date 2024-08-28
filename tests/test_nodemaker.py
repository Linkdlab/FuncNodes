"""
Test examples
"""

import unittest
from typing import Tuple
from funcnodes_core.nodemaker import (
    NodeDecorator,
    node_class_maker,
)
from funcnodes import get_nodeclass
import asyncio


class TestNodeClassMaker(unittest.IsolatedAsyncioTestCase):
    """
    Test suite for the node_class_maker function.

    The node_class_maker function creates a new NodeClass type given an identifier and a callable.
    It also decorates the callable if it's not already exposed as a method.
    """

    def test_node_class_maker_creates_class_with_correct_attributes(self):
        # Test if node_class_maker correctly creates a NodeClass with expected attributes
        def sync_func(ip: int) -> int:
            return ip

        NodeClassType = node_class_maker(
            "test_node_class_maker_creates_class_with_correct_attributes", sync_func
        )
        self.assertTrue(hasattr(NodeClassType, "input_ip"))
        self.assertTrue(hasattr(NodeClassType, "output_out"))
        self.assertTrue(hasattr(NodeClassType, "func"))
        self.assertEqual(
            NodeClassType.node_id,
            "test_node_class_maker_creates_class_with_correct_attributes",
        )

    def test_node_class_maker_async_function_wrapping(self):
        # Test if node_class_maker correctly wraps a non-async function into an async one
        def sync_func():
            return "sync_result"

        NodeClassType = node_class_maker("test_id", sync_func)
        self.assertTrue(asyncio.iscoroutinefunction(NodeClassType.func))

    async def test_node_decorator_registers_node_class(self):
        # Test if the Node decorator registers the created NodeClass

        @NodeDecorator(id="test_node_decorator_registers_node_class")
        async def sample_func(input1: int) -> int:
            return input1

        nodecls = get_nodeclass("test_node_decorator_registers_node_class")

        node = nodecls()
        self.assertEqual(node.node_id, "test_node_decorator_registers_node_class")
        self.assertEqual(len(node._inputs), 2)  # input1 and trigger
        self.assertEqual(len(node._outputs), 1)

        self.assertEqual(node.get_input("input1").name, "input1")
        self.assertEqual(node.get_output("out").name, "out")

        node.get_input("input1").value = 1
        await node
        self.assertEqual(node.get_output("out").value, 1)

    async def test_node_decorator_registers_node_class_multiple_outs(self):
        # Test if the Node decorator registers the created NodeClass

        @NodeDecorator(id="test_node_decorator_registers_node_class_multiple_outs")
        async def sample_func(input1: int) -> Tuple[int, int]:
            return input1, 2

        node = sample_func()
        self.assertEqual(
            node.node_id, "test_node_decorator_registers_node_class_multiple_outs"
        )
        self.assertEqual(node.get_input("input1").name, "input1")
        self.assertEqual(node.get_output("out0").name, "out0")
        self.assertEqual(node.get_output("out1").name, "out1")

        node.get_input("input1").value = 1
        await node
        self.assertEqual(node.get_output("out0").value, 1)
        self.assertEqual(node.get_output("out1").value, 2)

    async def test_node_decorator_registers_node_class_no_outs(self):
        # Test if the Node decorator registers the created NodeClass

        @NodeDecorator(id="test_node_decorator_registers_node_class_no_outs")
        async def sample_func(input1: int):
            pass

        node = sample_func()
        self.assertEqual(
            node.node_id, "test_node_decorator_registers_node_class_no_outs"
        )
        self.assertEqual(node.get_input("input1").name, "input1")
        self.assertEqual(len(node._outputs), 0)

        node.get_input("input1").value = 1
        await node


if __name__ == "__main__":
    unittest.main()
