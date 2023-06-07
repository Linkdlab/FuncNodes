"""
This file contains the tests for textnodes
"""
import unittest
import logging


logging.basicConfig(level=logging.INFO)


class TestTextNodes(unittest.IsolatedAsyncioTestCase):
    async def test_TextSplitNode(self):
        from funcnodes.nodes.basic.textnodes import TextSplitNode

        node = TextSplitNode()
        node.text.value = "Hello World"
        node.sep.set_value_and_default(" ")
        node.initialize()
        node.trigger()

        await node.await_done()

        self.assertEqual(node.before.value, "Hello")
        self.assertEqual(node.after.value, "World")

        ser = node.serialize()

        node2 = TextSplitNode(ser)

        node2json = node2._repr_json_()

        for io in node2json["io"]:
            self.assertEqual(io["type"], "str", f"Type of {io['name']} is not str")
