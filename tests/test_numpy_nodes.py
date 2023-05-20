"""
This file contains the tests the numpy nodes
"""
import unittest
import logging
import numpy as np
from FuncNodes.node import Node
from FuncNodes.nodes.node_creator import FunctionBasedNode
from FuncNodes.nodes.numpy_nodes.ufunc import UFUNC_NODES


logging.basicConfig(level=logging.INFO)


class TestNumpyNodes(unittest.IsolatedAsyncioTestCase):
    def test_basic_create(self):
        from FuncNodes.nodes import numpy_nodes

        AddNode = numpy_nodes.ufunc.AddNode  # type: ignore
        assert issubclass(AddNode, Node), f"AddNode is not a Node but a {type(AddNode)}"

        addnode: Node = AddNode().initialize()
        assert (
            len(addnode.get_inputs()) == 2
        ), f"AddNode has {len(addnode.get_inputs())} inputs instead of 2"
        assert (
            len(addnode.get_outputs()) == 1
        ), f"AddNode has {len(addnode.get_outputs())} outputs instead of 1"

    async def test_trigger(self):
        from FuncNodes.nodes import numpy_nodes

        AddNode = numpy_nodes.ufunc.AddNode  # type: ignore
        addnode: Node = AddNode().initialize()

        addnode.io.x1.value = 1
        addnode.io.x2.value = 2
        addnode.trigger()
        await addnode.await_done()
        assert (
            addnode.io.out.value == 3
        ), f"AddNode output is {addnode.io.out.value} instead of 3"

    async def test_all_ufunc(self):
        assert len(UFUNC_NODES) > 80, f"UFUNC_NODES has only {len(UFUNC_NODES)} nodes"
        for k, v in UFUNC_NODES.items():
            print(f"Testing {k}")
            assert issubclass(
                v, FunctionBasedNode
            ), f"{k} is not a Node but a {type(v)}"
            node = v().initialize()
            assert (
                len(node.get_inputs()) == node.func.nin
            ), f"{k} has {len(node.get_inputs())} inputs instead of {node.func.nin}"
            assert (
                len(node.get_outputs()) == node.func.nout
            ), f"{k} has {len(node.get_outputs())} outputs instead of {node.func.nout}"

            if k in ["IsnatNode", "MatmulNode"]:
                continue

            for i in range(node.func.nin):
                node.get_inputs()[i].value = i + 1
            node.trigger()
            await node.await_done()
            if node.func.nout == 1:
                assert node.get_outputs()[0].value == node.func(
                    *(i + 1 for i in range(node.func.nin))
                ), (
                    f"{k} output is {node.get_outputs()[0].value} "
                    f"instead of {node.func(*(i+1 for i in range(node.func.nin)))}"
                )
            else:
                for i in range(node.func.nout):
                    assert (
                        node.get_outputs()[i].value
                        == node.func(*(i + 1 for i in range(node.func.nin)))[i]
                    ), (
                        f"{k} output {i} is {node.get_outputs()[i].value} "
                        f"instead of {node.func(*(i+1 for i in range(node.func.nin)))[i]}"
                    )
        k, v = "IsnatNode", UFUNC_NODES["IsnatNode"]
        assert issubclass(v, FunctionBasedNode), f"{k} is not a Node but a {type(v)}"
        node = v().initialize()
        for i in range(node.func.nin):
            node.get_inputs()[i].value = np.datetime64("2016-01-01")
        node.trigger()
        await node.await_done()
        self.assertFalse(
            node.get_outputs()[0].value,
            f"{k} output is {node.get_outputs()[0].value} instead of False",
        )

        k, v = "MatmulNode", UFUNC_NODES["MatmulNode"]
        assert issubclass(v, FunctionBasedNode), f"{k} is not a Node but a {type(v)}"
        node: Node = v().initialize()
        for i in range(node.func.nin):
            node.get_inputs()[i].value = np.array([[1, 0], [0, 1]])
        node.trigger()
        await node.await_done()

        assert np.array_equal(
            node.get_outputs()[0].value, np.array([[1, 0], [0, 1]])
        ), f"{k} output is {node.get_outputs()[0].value} instead of np.array([[1, 0], [0, 1]])"

    async def test_example_add_greater(self):
        from FuncNodes.nodes.numpy_nodes.ufunc import AddNode, GreaterNode

        # Define two add nodes, one for each pair of numbers you want to add
        add_node1 = AddNode(
            {
                "id": "add1",
                "io": {"x1": {"default_value": 1}, "x2": {"default_value": 3}},
            }
        ).initialize()

        add_node2 = AddNode(
            {
                "id": "add2",
                "io": {"x1": {"default_value": 2}, "x2": {"default_value": 5}},
            }
        ).initialize()

        # Define a greater node to compare the two sums
        greater_node = GreaterNode({"id": "greater"}).initialize()
        greater_node2 = GreaterNode({"id": "greater"}).initialize()

        # Connect the nodes
        add_node1.io.out.connect_to(greater_node.io.x1)
        add_node2.io.out.connect_to(greater_node.io.x2)
        add_node1.io.out.c(greater_node2.io.x2)
        add_node2.io.out.c(greater_node2.io.x1)

        await add_node1.await_done()
        await add_node2.await_done()
        await greater_node.await_done()
        await greater_node2.await_done()
        # Evaluate the nodes and print the results

        assert (
            add_node1.out.value == 4
        ), f"add_node1 output is {add_node1.out.value} instead of 4"
        assert (
            add_node2.out.value == 7
        ), f"add_node2 output is {add_node2.out.value} instead of 7"
        assert (
            greater_node.out.value == False
        ), f"greater_node output is {greater_node.out.value} instead of False"
        assert (
            greater_node2.out.value == True
        ), f"greater_node2 output is {greater_node2.out.value} instead of True"

        print(
            add_node1.serialize(),
        )
