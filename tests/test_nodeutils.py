import unittest

from funcnodes.utils.nodeutils import (
    get_deep_connected_nodeset,
    run_until_complete,
)

from funcnodes.nodemaker import NodeDecorator


@NodeDecorator("dummy_nodefor testnodeutils")
def identity(input: int) -> int:
    return input


class TestNodeUtils(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Create mock nodes with output connections to simulate a graph.
        self.node1 = identity()
        self.node2 = identity()
        self.node3 = identity()
        # Create connections between nodes.
        self.node1.outputs["out"].connect(self.node2.inputs["input"])
        self.node2.outputs["out"].connect(self.node3.inputs["input"])
        self.node1.inputs["input"].value = 10

    async def test_get_deep_connected_nodeset(self):
        # Test the deep collection of connected nodes.
        nodeset = get_deep_connected_nodeset(self.node1)
        self.assertIn(self.node1, nodeset)
        self.assertIn(self.node2, nodeset)
        self.assertIn(self.node3, nodeset)

    async def test_get_deep_connected_nodeset_with_node_in(self):
        nodeset = get_deep_connected_nodeset(self.node1, {self.node2})
        self.assertIn(self.node1, nodeset)
        self.assertIn(self.node2, nodeset)
        self.assertNotIn(self.node3, nodeset)

        nodeset = get_deep_connected_nodeset(self.node1, {self.node1})
        self.assertIn(self.node1, nodeset)
        self.assertNotIn(self.node2, nodeset)
        self.assertNotIn(self.node3, nodeset)

    async def test_run_until_complete_all_triggered(self):
        # Run the function until all nodes are no longer triggering.
        await run_until_complete(self.node1, self.node2, self.node3)
        self.assertEqual(self.node1.outputs["out"].value, 10)
        self.assertEqual(self.node2.outputs["out"].value, 10)
        self.assertEqual(self.node3.outputs["out"].value, 10)
