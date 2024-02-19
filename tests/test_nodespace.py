import unittest
from funcnodes import NodeSpace, Node, NodeInput, NodeOutput
import gc


class DummyNode(Node):
    node_id = "ns_dummy_node"
    node_name = "Dummy Node"
    myinput = NodeInput(id="input", type=int, default=1)
    myoutput = NodeOutput(id="output", type=int)

    async def func(self, input: int) -> int:
        return input


class TestNodeSpace(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.nodespace = NodeSpace()
        self.nodespace.lib.add_node(DummyNode, "basic")

    def test_add_node_instance(self):
        node = DummyNode()
        self.nodespace.add_node_instance(node)
        self.assertIn(node, self.nodespace.nodes)

    def test_add_node_by_id(self):
        node_id = "ns_dummy_node"
        nodeuuid = self.nodespace.add_node_by_id(node_id).uuid
        self.assertIn(nodeuuid, [node.uuid for node in self.nodespace.nodes])

    def test_get_node_by_id(self):
        node_id = "ns_dummy_node"
        nodeuuid = self.nodespace.add_node_by_id(node_id).uuid
        node = self.nodespace.get_node_by_id(nodeuuid)
        self.assertEqual(nodeuuid, node.uuid)
        self.assertEqual(node_id, node.node_id)

    def test_serialize_nodes(self):
        node = DummyNode()
        self.nodespace.add_node_instance(node)
        serialized_nodes = self.nodespace.serialize_nodes()
        self.assertEqual(len(serialized_nodes), 1)

    def test_deserialize_nodes(self):
        node = DummyNode()
        self.nodespace.add_node_instance(node)
        self.assertEqual(len(self.nodespace.nodes), 1)
        serialized_nodes = self.nodespace.serialize_nodes()
        print(serialized_nodes)
        self.nodespace._nodes = {}
        self.nodespace.deserialize_nodes(serialized_nodes)
        self.assertEqual(len(self.nodespace.nodes), 1)

    def test_serialize(self):
        node = DummyNode()
        self.nodespace.add_node_instance(node)
        serialized_nodespace = self.nodespace.serialize()
        self.assertIn("nodes", serialized_nodespace)
        self.assertIn("edges", serialized_nodespace)
        self.assertIn("prop", serialized_nodespace)

    def test_deserialize(self):
        node = DummyNode()
        self.nodespace.add_node_instance(node)
        serialized_nodespace = self.nodespace.serialize()
        self.nodespace._nodes = {}
        self.nodespace.deserialize(serialized_nodespace)
        self.assertEqual(len(self.nodespace.nodes), 1)

    def test_remove_node(self):
        gc.collect()
        gc.set_debug(gc.DEBUG_LEAK)
        node1 = DummyNode()
        node2 = DummyNode()

        self.nodespace.add_node_instance(node1)
        self.nodespace.add_node_instance(node2)
        self.assertEqual(len(self.nodespace.nodes), 2)
        self.assertEqual(
            len(gc.get_referrers(node1)), 3, gc.get_referrers(node1)
        )  # 3 because of the nodespace, the input and the output

        self.assertTrue(
            self.nodespace._nodes in gc.get_referrers(node1),
            gc.get_referrers(node1),
        )
        self.nodespace.remove_node_by_id(self.nodespace.nodes[0].uuid)
        self.assertEqual(len(self.nodespace.nodes), 1)

        gc.collect()
        node1.__del__()
        self.assertEqual(len(gc.get_referrers(node1)), 0, gc.get_referrers(node1))
        del node1
        gc.collect()
        garb = gc.garbage
        gc.set_debug(0)

        self.assertEqual(garb, [])
