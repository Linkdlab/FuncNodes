"""
Test the NodeSpace
"""
from funcnodes.io import NodeInput, NodeOutput
from funcnodes.nodespace import NodeSpace
from funcnodes.node import Node
import unittest
import logging

logging.basicConfig(level=logging.INFO)


class DummyNode(Node):
    """Dummy node for testing"""

    node_id = "dummy_node_test_nodespace"
    right = NodeInput()
    left = NodeInput()
    output = NodeOutput()

    async def on_trigger(self):
        self.output.value = self.left.value + self.right.value
        return True


class TestNodeSpace(unittest.TestCase):
    """Test NodeSpace"""

    def test_create(self):
        """Test the creation of a NodeSpace"""
        ns = NodeSpace()
        self.assertListEqual(ns.nodes, [])
        self.assertListEqual(ns.edges, [])

    def test_add_node(self):
        """Test adding a node"""
        ns = NodeSpace()
        ns.lib.add_nodeclass(DummyNode)
        ns.add_node(DummyNode())
        self.assertEqual(len(ns.nodes), 1)

    def test_remove_node(self):
        """Test removing a node"""
        ns = NodeSpace()
        ns.lib.add_nodeclass(DummyNode)
        ns.add_node(DummyNode(id="n_0"))
        ns.add_node(DummyNode(id="n_1"))
        ns.get_node("n_0").io.output.connect_to(ns.get_node("n_1").io.left)

        import gc

        # node = ns.get_node("n_0")
        self.assertEqual(len(ns.nodes), 2)
        self.assertEqual(len(ns.edges), 1)

        gc.disable()
        gc.collect()
        #
        n = ns.nodes[0]
        # refered by the line, node space, the logger (sometimes not?), left, right and output

        assert (
            5 <= len(gc.get_referrers(n)) <= 6
        ), f"{len(gc.get_referrers(n))} referrers: {gc.get_referrers(n)}"
        ns.remove_node(ns.nodes[0])
        # only the logger(or not) should be referencing the node and the line
        assert (
            1 <= len(gc.get_referrers(n)) <= 2
        ), f"{len(gc.get_referrers(n))} referrers: {gc.get_referrers(n)}"
        n = None
        gc.collect()
        gc.enable()

        self.assertEqual(len(ns.nodes), 1)
        self.assertEqual(len(ns.edges), 0)

    def test_add_connected(self):
        ns = NodeSpace()
        ns.lib.add_nodeclass(DummyNode)
        n_0 = DummyNode(id="n_0")
        n_1 = DummyNode(id="n_1")
        n_2 = DummyNode(id="n_2")
        n_3 = DummyNode(id="n_3")
        n_4 = DummyNode(id="n_4")

        n_0.io.output.connect_to(n_1.io.left)
        n_1.io.output.connect_to(n_2.io.left)
        n_2.io.output.connect_to(n_3.io.left)
        n_3.io.output.connect_to(n_4.io.left)
        added: list = ns.add_node(n_1) or []
        self.assertEqual(len(added), 5, "Should have added 3 nodes")
        self.assertEqual(len(ns.edges), 4, "Should have added 2 edges")
        self.assertEqual(len(ns.nodes), 5, "Should have added 3 nodes")
        self.assertEqual(len(ns.add_node(n_4) or []), 0, "Should have added 0 nodes")

    def test_connection(self):
        ns = NodeSpace()
        ns.lib.add_nodeclass(DummyNode)
        ns.add_node(DummyNode(id="n_0"))
        ns.add_node(DummyNode(id="n_1"))
        ns.connect_by_id("n_0", "output", "n_1", "right")
        self.assertEqual(len(ns.edges), 1)
        ns.disconnect_by_id("n_0", "output", "n_1", "right")
        self.assertEqual(len(ns.edges), 0)

    def test_serialize(self):
        ns = NodeSpace()
        ns.lib.add_nodeclass(DummyNode)
        ns.add_node(DummyNode(id="n_0"))
        ns.add_node(DummyNode(id="n_1"))
        ns.get_node("n_0").io.output.connect_to(ns.get_node("n_1").io.left)

        ser = ns.serialize()
        self.maxDiff = None
        self.assertDictEqual(
            ser,
            {
                "nodes": [
                    {"id": "n_0", "nid": "dummy_node_test_nodespace"},
                    {"id": "n_1", "nid": "dummy_node_test_nodespace"},
                ],
                "edges": [["n_0", "output", "n_1", "left"]],
                "prop": {},
            },
        )

    def test_deserialize(self):
        ns = NodeSpace()
        ns.lib.add_nodeclass(DummyNode)
        d1 = {
            "nodes": [
                {
                    "id": "n_0",
                    "nid": "dummy_node_test_nodespace",
                    "io": {
                        "ip": {"right": {"default_value": 0}},
                    },
                },
                {"id": "n_1", "nid": "dummy_node_test_nodespace"},
            ],
            "edges": [["n_0", "output", "n_1", "left"]],
            "prop": {},
        }
        ns.deserialize(d1)

        d2 = ns.serialize()
        print(d2)
        self.maxDiff = None
        self.assertDictEqual(d1, d2)
