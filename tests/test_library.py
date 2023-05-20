"""
Test the Node Library
"""
import unittest
from FuncNodes.node import Node
from FuncNodes.nodespace import Library

import logging

logging.basicConfig(level=logging.INFO)


class DummyNode(Node):
    """Dummy node for testing"""

    node_id = "lib_dummy_node"

    async def on_trigger(self):
        return True


class TestLibrary(unittest.TestCase):
    """Test the Node Library"""

    def test_lib_create(self):
        """Test the creation of a library"""
        lib = Library()
        self.assertListEqual(lib._shelves, [])

    def test_node_to_baseshelf(self):
        """Test the addition of a node to the base shelf"""
        lib = Library()
        lib.add_nodeclass(Node)
        self.assertListEqual(
            lib._shelves, [{"name": "default", "nodes": [Node], "shelves": []}]
        )

        lib.add_nodeclass(Node, shelf="shelf1")
        print(lib._shelves)
        self.assertListEqual(
            lib._shelves,
            [
                {"name": "default", "nodes": [Node], "shelves": []},
                {"name": "shelf1", "nodes": [Node], "shelves": []},
            ],
        )

    def test_node_to_deep_shelf(self):
        lib = Library()
        lib.add_nodeclass(Node, shelf=["a", "b", "c"])
        self.assertListEqual(
            lib._shelves,
            [
                {
                    "name": "a",
                    "nodes": [],
                    "shelves": [
                        {
                            "name": "b",
                            "nodes": [],
                            "shelves": [
                                {
                                    "name": "c",
                                    "nodes": [Node],
                                    "shelves": [],
                                }
                            ],
                        }
                    ],
                }
            ],
        )

    def test_nodes_to_baseshelf(self):
        lib = Library()
        lib.add_nodeclasses([Node, DummyNode])
        self.assertListEqual(
            lib._shelves,
            [
                {
                    "name": "default",
                    "nodes": [Node, DummyNode],
                    "shelves": [],
                }
            ],
        )

        lib.add_nodeclasses([Node, DummyNode], shelf="shelf1")
        self.assertListEqual(
            lib._shelves,
            [
                {
                    "name": "default",
                    "nodes": [Node, DummyNode],
                    "shelves": [],
                },
                {
                    "name": "shelf1",
                    "nodes": [Node, DummyNode],
                    "shelves": [],
                },
            ],
        )

    def test_nodes_to_deep_shelf(self):
        lib = Library()
        lib.add_nodeclasses([Node, DummyNode], shelf=["a", "b", "c"])
        self.assertListEqual(
            lib._shelves,
            [
                {
                    "name": "a",
                    "nodes": [],
                    "shelves": [
                        {
                            "name": "b",
                            "nodes": [],
                            "shelves": [
                                {
                                    "name": "c",
                                    "nodes": [Node, DummyNode],
                                    "shelves": [],
                                }
                            ],
                        }
                    ],
                }
            ],
        )

    def test_add_nodes_as_shelves(self):
        lib = Library()

        s = {
            "name": "a",
            "nodes": [Node],
            "shelves": [
                {
                    "name": "b",
                    "nodes": [],
                    "shelves": [
                        {"name": "c", "nodes": [Node, DummyNode], "shelves": []},
                    ],
                }
            ],
        }
        lib.add_nodeclasses(s)
        self.maxDiff = None
        self.assertListEqual(lib._shelves, [s])

        s1 = {"name": "b1", "nodes": [Node], "shelves": []}
        lib.add_nodeclasses(s1, ["a", "b"])

        s["shelves"][0]["shelves"].append(s1)
        self.assertListEqual(lib._shelves, [s])
