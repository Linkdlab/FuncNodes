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
        node.sep.value = " "
        node.initialize()
        node.trigger()

        await node.await_done()

        self.assertEqual(node.before.value, "Hello")
        self.assertEqual(node.after.value, "World")
