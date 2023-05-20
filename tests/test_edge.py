"""
Test the Edge class
"""
from typing import cast
import unittest
from funcnodes.errors import DisabledException, TriggerException
from funcnodes.node import (
    Node,
    NodeInput,
    NodeOutput,
    NodeIOError,
)
from funcnodes.nodespace import NodeSpace
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)


class DummyNode(Node):
    """Dummy node for testing"""

    node_id = "dummy_node"
    right = NodeInput(required=True)
    left = NodeInput(required=True)
    output = NodeOutput()

    async def on_trigger(self):
        self.output.value = self.left.value + self.right.value
        return True


class TestEdge(unittest.IsolatedAsyncioTestCase):
    """Test the Edge class"""

    def test_edge_creations(self) -> None:
        """Test the creation of edges"""
        input_node = DummyNode()
        output_node = DummyNode()

        input_node.io.output.connect_to(output_node.io.left)

    async def test_simple_add(self):
        """Test a simple addition"""
        # create 2 nodes
        node_1 = DummyNode(id="dn1").initialize()
        node_2 = DummyNode(id="dn2").initialize()

        # connect the output of node_1 to the left input of node_2
        node_1.io.output.connect_to(node_2.io.left)

        # set some values
        node_1.io.left.value = 1
        node_1.io.right.value = 2
        node_2.io.right.value = 3

        # trigger the node
        node_1.trigger()

        # wait for it to finish
        await node_1.await_done()

        # check the value
        assert (
            node_2.io.output.value == 6
        ), f"NodeIO value is '{node_2.io.output.value}' instead of 5"

    async def test_circular(self):
        """
        Test that a circular connection also works
        Including timeout and breaking the loop
        """
        node_1 = DummyNode(id="node_1").initialize()
        node_2 = DummyNode(id="node_2").initialize()

        # Connect the left input of node_1 to the output of node_2
        node_1.output.connect_to(node_2.left)
        # Connect the left input of node_2 to the output of node_1
        node_2.output.connect_to(node_1.left)
        # Set the left input of node_1 to 1
        node_1.left.value = 1
        # Set the right input of node_1 to 1
        node_1.right.value = 1
        # Set the right input of node_2 to 1
        node_2.right.value = 1

        # Trigger node_1
        node_1.trigger()
        # Expect a timeout error
        with self.assertRaises(TimeoutError):
            await Node.await_all(node_1, node_2, timeout=1)

        # Disable the nodes
        node_1.disabled = True
        node_2.disabled = True
        # Wait for the nodes to finish
        try:
            await Node.await_all(node_1, node_2, timeout=1)
        except DisabledException:
            pass
        # Set the right input of node_2 to 0
        node_2.right.value = 0
        # Set the left input of node_2 to 1
        node_2.left.value = 1
        # Set the left input of node_1 to 0
        node_1.left.value = 0
        # Set the right input of node_1 to 1
        node_1.right.value = 1

        # Create a list to store the values from the output of node_1
        data = []

        # Define a function to store the values from the output of node_1
        def sd(name, new, old, **kwargs):
            if name == "output":
                data.append(new)
                if new == 50:
                    node_1.disable()
                    node_2.disable()

        # Subscribe to the set data event
        node_1.on("set.data", sd)
        # Enable the nodes
        node_1.enable()
        node_2.enable()

        # Wait for the nodes to finish
        with self.assertRaises(DisabledException):
            await Node.await_all(node_1, node_2, timeout=2)

        # Check if the values from the output of node_1 are correct
        self.assertListEqual(data, list(range(1, 51)))

    async def test_remove_edge(self):
        node_1 = DummyNode(id="node_1").initialize()
        node_2 = DummyNode(id="node_2").initialize()

        # Connect the left input of node_1 to the output of node_2
        node_1.output.connect_to(node_2.left)
        # Connect the left input of node_2 to the output of node_1
        node_2.output.connect_to(node_1.left)
        # Set the left input of node_1 to 1
        node_1.left.value = 1
        # Set the right input of node_1 to 1
        node_1.right.value = 1
        # Set the right input of node_2 to 1
        node_2.right.value = 1

        with self.assertRaises(TimeoutError):
            await Node.await_all(node_1, node_2, timeout=0.5)

        with self.assertRaises(NodeIOError):
            node_2.output.disconnect_from(node_1.right)

        node_2.output.disconnect_from(node_1.left)
        try:
            await Node.await_all(node_1, node_2, timeout=0.5)
        except TriggerException:
            # TODO: handle diconnection while in waiting for trigger,
            #  which would raise an error since the check happens before
            #  maybe it can stay as it is
            pass

    async def test_self_connect_fail(self):
        """a node should not be able to connect to itself"""
        node = DummyNode()
        with self.assertRaises(NodeIOError):
            node.io.output.connect_to(node.io.left)

    async def test_replace_edge(self):
        node_1 = DummyNode(id="node_1").initialize()
        node_2 = DummyNode(id="node_2").initialize()
        node_3 = DummyNode(id="node_3").initialize()

        node_1.output.connect_to(node_2.left)
        with self.assertRaises(NodeIOError):
            node_3.output.connect_to(node_2.left)

        node_3.output.connect_to(node_2.left, replace_if_necessary=True)

        other_nodes = node_2.left.get_other_nodes()
        assert len(other_nodes) == 1
        assert other_nodes[0] == node_3
        assert len(node_1.node_output_bound_nodes()) == 0

    async def test_connect_io_fail(self):
        """Test that connecting 2 IOs of same type fails"""
        node1 = DummyNode()
        node2 = DummyNode()

        with self.assertRaises(NodeIOError):
            node1.io.output.connect_to(node2.io.output)

        with self.assertRaises(NodeIOError):
            node1.io.left.connect_to(node2.io.right)

    async def test_branching(self):
        from funcnodes.nodes.numpy_nodes.ranges import LinspaceNode  # noqa: E402
        from funcnodes.nodes.numpy_nodes.ufunc import AddNode

        node_1 = DummyNode(id="node_1").initialize()
        node_2 = DummyNode(id="node_2").initialize()
        node_3 = DummyNode(id="node_3").initialize()
        node_4 = DummyNode(id="node_4").initialize()

        node_1.output.connect_to(node_2.left)
        node_1.output.connect_to(node_3.left)
        node_3.output.connect_to(node_4.left)
        node_4.output.connect_to(node_2.right)
        node_4.right.value = 1
        node_3.right.value = 1
        node_1.left.value = 1
        node_1.right.value = 1

        await Node.await_all(node_1, node_2, node_3, node_4, timeout=0.5)

        assert (
            node_1.output.value == 2
        ), f"NodeIO value is '{node_1.output.value}' instead of 2"
        assert (
            node_3.output.value == 3
        ), f"NodeIO value is '{node_3.output.value}' instead of 3"
        assert (
            node_4.output.value == 4
        ), f"NodeIO value is '{node_4.output.value}' instead of 4"
        assert (
            node_2.output.value == 6
        ), f"NodeIO value is '{node_2.output.value}' instead of 6"

        # lin1 ---------------> add2
        #   |------------> add1--|
        #   |-> l1 -> rand1--|

        # no trigger approach
        data = {
            "nodes": [
                {
                    "id": "lin1",
                    "io": {
                        "ip": {
                            "num": {"default_value": 10},
                            "stop": {"default_value": 10.0},
                        }
                    },
                    "nid": "np.linspace",
                },
                {
                    "id": "add2",
                    "nid": "np.add",
                    "io": {
                        "ip": {
                            "x1": {"does_trigger": False},
                        }
                    },
                },
                {
                    "id": "add1",
                    "name": "AddNode1",
                    "nid": "np.add",
                    "io": {
                        "ip": {
                            "x1": {"does_trigger": False},
                        }
                    },
                },
                {"id": "l1", "nid": "length"},
                {
                    "id": "rand1",
                    "nid": "np.random.random_sample",
                },
            ],
            "edges": [
                [
                    "lin1",
                    "out",
                    "add2",
                    "x1",
                ],
                [
                    "lin1",
                    "out",
                    "add1",
                    "x1",
                ],
                [
                    "add1",
                    "out",
                    "add2",
                    "x2",
                ],
                [
                    "l1",
                    "output",
                    "rand1",
                    "size",
                ],
                [
                    "lin1",
                    "out",
                    "l1",
                    "input",
                ],
                [
                    "rand1",
                    "out",
                    "add1",
                    "x2",
                ],
            ],
            "prop": {},
        }

        ns = NodeSpace()

        ns.deserialize(data)  # type: ignore
        print("#" * 10)
        print(
            ns.get_node("lin1").start.default_value,
            ns.get_node("lin1").start.value_or_none,
        )
        await ns.await_done()
        add2 = cast(AddNode, ns.get_node("add2"))

        assert add2.out.value.shape == (10,), add2.out.value.shape
        assert np.all(add2.out.value > np.linspace(0, 20, 10))
        assert np.all(add2.out.value < np.linspace(1, 21, 10))
        lin1 = cast(LinspaceNode, ns.get_node("lin1"))
        lin1.num.value = 21
        await ns.await_done()
        assert add2.out.value.shape == (21,)
        assert np.all(add2.out.value > np.linspace(0, 20, 21))
        assert np.all(add2.out.value < np.linspace(1, 21, 21))

        # error catching
        data = {
            "nodes": [
                {
                    "id": "lin1",
                    "nid": "np.linspace",
                    "io": {
                        "ip": {
                            "num": {"default_value": 10},
                            "stop": {"default_value": 10.0},
                        }
                    },
                },
                {
                    "id": "add2",
                    "nid": "np.add",
                },
                {
                    "id": "add1",
                    "name": "AddNode1",
                    "nid": "np.add",
                },
                {"id": "l1", "nid": "length"},
                {
                    "id": "rand1",
                    "nid": "np.random.random_sample",
                },
            ],
            "edges": [
                [
                    "lin1",
                    "out",
                    "add2",
                    "x1",
                ],
                [
                    "lin1",
                    "out",
                    "add1",
                    "x1",
                ],
                [
                    "add1",
                    "out",
                    "add2",
                    "x2",
                ],
                [
                    "l1",
                    "output",
                    "rand1",
                    "size",
                ],
                [
                    "lin1",
                    "out",
                    "l1",
                    "input",
                ],
                [
                    "rand1",
                    "out",
                    "add1",
                    "x2",
                ],
            ],
            "prop": {},
        }

        ns.deserialize(data)  # type: ignore
        lin1 = ns.get_node("lin1")

        await ns.await_done()
        add2 = cast(AddNode, ns.get_node("add2"))

        assert add2.out.value.shape == (10,), add2.out.value.shape
        assert np.all(add2.out.value > np.linspace(0, 20, 10))
        assert np.all(add2.out.value < np.linspace(1, 21, 10))
        print(add2.out.value.shape)
        lin1 = cast(LinspaceNode, ns.get_node("lin1"))
        lin1.num.value = 21
        with self.assertRaises(TriggerException):
            await ns.await_done()

        ns.on_error(lambda error, src: print(f"Error in {error.node}: {error}"))
        ns.deserialize(data)  # type: ignore
        lin1 = cast(LinspaceNode, ns.get_node("lin1"))
        await ns.await_done()
        lin1.num.value = 21
        await ns.await_done()
        add2 = cast(AddNode, ns.get_node("add2"))
        assert add2.out.value.shape == (21,)
        assert np.all(add2.out.value > np.linspace(0, 20, 21))
        assert np.all(add2.out.value < np.linspace(1, 21, 21))
