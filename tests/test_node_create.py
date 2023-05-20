"""
This file contains the tests the automatic node creation
"""
import unittest
import random
import warnings
from funcnodes.errors import NotOperableException
from funcnodes.node import Node
from funcnodes.nodes.node_creator import (
    func_to_node,
    func_to_node_decorator,
    FuncNodeReservedNameError,
    FuncNodeUnserializableDefaultError,
    FuncNodeWarning,
)

from funcnodes.nodespace import NodeSpace
from funcnodes.errors import LibraryError


class TestNodeCreate(unittest.IsolatedAsyncioTestCase):
    def test_simple_func_to_node(self):
        """Test the creation of a node from a function"""

        def testfunc():
            pass

        NodeClass = func_to_node(testfunc, node_id=str(random.randint(0, 1000000)))
        assert issubclass(NodeClass, Node), "NodeClass is not a subclass of Node"
        node = NodeClass()
        assert isinstance(node, Node), "node is not an instance of Node"

    async def test_func_to_node_w_trigger_wo_args(self):
        """Test the creation of a node from a function"""

        def testfunc():
            return 1

        NodeClass = func_to_node(testfunc, node_id=str(random.randint(0, 1000000)))

        node = NodeClass().initialize()
        node.trigger()
        await node.await_done()
        assert node.out.value == 1, "node.out.value != 1"  # type: ignore

    async def test_simple_func_to_node_with_args(self):
        """Test the creation of a node from a function"""

        with self.assertRaises(FuncNodeReservedNameError):

            def testfunc1(_io: int):
                pass

            func_to_node(testfunc1, node_id=str(random.randint(0, 1000000)))

        with self.assertRaises(FuncNodeUnserializableDefaultError):

            def testfunc2(ip1=Node):
                pass

            func_to_node(testfunc2, node_id=str(random.randint(0, 1000000)))

        def testfunc3(ip1: int = 1):
            return ip1 + 1

        NC3 = func_to_node(testfunc3, node_id=str(random.randint(0, 1000000)))
        node3 = NC3().initialize()
        node3.trigger()
        await node3.await_done()
        assert node3.out.value == 2, "node3.out.value != 2"

        def testfunc4(ip1=1):
            return ip1 + 1

        with warnings.catch_warnings(record=True) as w:
            NC4 = func_to_node(testfunc4, node_id=str(random.randint(0, 1000000)))
            assert len(w) == 1, "No warning was raised"
            assert issubclass(w[-1].category, FuncNodeWarning)
        node4 = NC4().initialize()
        node4.trigger()
        await node4.await_done()
        assert node4.out.value == 2, "node4.out.value != 2"

        def testfunc5(ip1):
            return ip1 + 1

        NC5 = func_to_node(testfunc5, node_id=str(random.randint(0, 1000000)))
        node5 = NC5().initialize()
        with self.assertRaises(NotOperableException):
            node5.trigger()
            await node5.await_done()
        node5.ip1.value = 1
        node5.trigger()
        await node5.await_done()
        assert node5.out.value == 2, "node5.out.value != 2"

    async def test_func_to_node_decorator(self):
        @func_to_node_decorator(node_id=str(random.randint(0, 1000000)))
        def testfunc():
            return 1

        node = testfunc().initialize()
        node.trigger()
        await node.await_done()
        assert node.out.value == 1, "node.out.value != 1"

        assert node() == 1, "node() != 1"

    async def test_classdecorator(self):
        from funcnodes.nodes.node_creator import NodeClassMixin, instance_nodefunction

        class TestNodeCarrier(NodeClassMixin):
            testfunccallled = False
            NODECLASSID = "testnodecarrier"
            INSTANCES = 0

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.uuid = str(TestNodeCarrier.INSTANCES)
                TestNodeCarrier.INSTANCES += 1

            @instance_nodefunction()
            def testfunc(self):
                print("testfunc called")
                TestNodeCarrier.testfunccallled = True

            @instance_nodefunction()
            def testfunc2(self, a=1):
                return a + 1

            @instance_nodefunction()
            def testfunc3(self, a):
                return a + 1

        nc = TestNodeCarrier()
        print("\n######")
        print(nc.get_all_nodeclasses())
        print(nc.testfunc.get_node())

        testfuncnode = nc.testfunc.get_node()().initialize()
        testfuncnode.trigger()
        await testfuncnode.await_done()
        assert (
            TestNodeCarrier.testfunccallled
        ), "TestNodeCarrier.testfunccallled did not change"

        testfunc2node = nc.testfunc2.get_node()().initialize()
        testfunc2node.trigger()
        await testfunc2node.await_done()

        testfunc2node.a.value = 2
        testfunc2node.trigger()
        await testfunc2node.await_done()
        assert testfunc2node.out.value == 3, "testfunc2node.out.value != 3"

        testfunc3node = nc.testfunc3.get_node()().initialize()
        with self.assertRaises(NotOperableException):
            testfunc3node.trigger()
        await testfunc3node.await_done()

        nc2 = TestNodeCarrier()

        ns = NodeSpace()
        ns.lib.add_nodeclass(nc.testfunc.get_node())
        ns.lib.add_nodeclass(nc.testfunc2.get_node())
        ns.lib.add_nodeclass(nc2.testfunc3.get_node())
        self.assertEqual(
            list(ns.lib.available_nodes.keys()),
            [
                "testnodecarrier.0.testfunc",
                "testnodecarrier.0.testfunc2",
                "testnodecarrier.1.testfunc3",
            ],
        )
        ns.add_node(testfuncnode)
        ns.add_node(testfunc2node)
        with self.assertRaises(LibraryError):
            ns.add_node(testfunc3node)
        ns.add_node(nc2.testfunc3.get_node()())

        print(ns.serialize())
