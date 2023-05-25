"""
This file contains the tests for the node class.
"""
import unittest
import asyncio
import logging
from funcnodes.errors import TriggerException
from funcnodes.node import (
    Node,
    NodeStructureError,
    NodeInput,
    NodeOutput,
    NodeInitalizationError,
    NodeIO,
    NodeDataName,
    Any,
)

logging.basicConfig(level=logging.INFO)


def patch_init(cls):
    node_init = cls.__init__

    def new_nn(self, *args, **kwargs):
        self.n_calls = {}

        def _wrap_method(method):
            def _wrapped_method(*args, **kwargs):
                if method.__name__ not in self.n_calls:
                    self.n_calls[method.__name__] = 0
                self.n_calls[method.__name__] += 1
                return method(*args, **kwargs)

            return _wrapped_method

        # iterate over all methods and wrap them
        for name in dir(self):
            try:
                method = getattr(self, name)
            except AttributeError:
                continue
            if not name.startswith("__") and callable(method):
                setattr(self, name, _wrap_method(method))

        node_init(self, *args, **kwargs)

    cls.__init__ = new_nn


patch_init(Node)
patch_init(NodeIO)


class TestNode(unittest.IsolatedAsyncioTestCase):
    """Test the Node class"""

    def test_node_properties(self):
        """
        This code tests if the properties of the node are set correctly.
        It also tests if the code can change the name of the node correctly.
        """

        class DummyNode(Node):  # pylint: disable=C0115,W0223,W0612, E0102
            node_id = "dummy_nodea"

            async def on_trigger(
                self,
            ):
                return True

        node = DummyNode()
        print(node.n_calls)

        assert "id" in node.properties, "Node properties are missing 'id'"
        assert "name" in node.properties, "Node properties are missing 'name'"
        assert "disabled" in node.properties, "Node properties are missing 'disabled'"
        assert "io" in node.properties, "Node properties are missing 'io'"
        assert "ip" in node.properties["io"], "Node properties are missing 'io__ip'"
        assert "op" in node.properties["io"], "Node properties are missing 'io__op'"

        assert (
            node.id == node.properties["id"]
        ), f"Node id is '{node.id}' instead of '{node.properties['id']}'"
        assert (
            len(node.id) == 32
        ), f"Node id is '{node.id}' instead of 32 characters long"
        assert (
            node.name == node.properties["name"]
        ), f"Node properties are '{node.properties}'"
        assert (
            node.disabled == node.properties["disabled"]
        ), f"Node properties are '{node.properties}'"
        assert (
            node.properties["io"]["ip"] == {}
        ), f"Node properties are '{node.properties}'"
        assert (
            node.properties["io"]["op"] == {}
        ), f"Node properties are '{node.properties}'"

        node.properties["name"] = "test"
        assert (
            node.name == "DummyNode"
        ), f"Node name is '{node.name}' instead of 'DummyNode'"
        node.name = "test"
        assert node.name == "test", f"Node name is '{node.name}' instead of 'test'"

        print(node.n_calls)

    def test_no_id(self):
        """Test that a node without an ID raises a NodeStructureError"""
        with self.assertRaises(NodeStructureError):

            class DummyNode(Node):  # pylint: disable=C0115,W0223,W0612
                pass

    def test_id_alredy_taken(self):
        """Test that a node with an ID that is already taken raises a NodeStructureError"""
        from funcnodes import node

        node.ERROR_ON_DOUBLE_ID = True

        class DummyNode1(Node):  # pylint: disable=C0115,W0223,W0612, E0102
            node_id = "dummy_node_test_id_alredy_taken"

        with self.assertRaises(NodeStructureError):

            class DummyNode2(Node):  # pylint: disable=C0115,W0223,W0612, E0102
                node_id = "dummy_node_test_id_alredy_taken"

    def test_id_alredy_taken2(self):
        """Test that a node with an ID that is already taken raises a NodeStructureError"""
        from funcnodes import node

        node.ERROR_ON_DOUBLE_ID = False

        class DummyNode1(Node):  # pylint: disable=C0115,W0223,W0612, E0102
            node_id = "dummy_node_test_id_alredy_taken"

        with self.assertLogs("funcnodes", level="INFO") as cm:

            class DummyNode2(Node):  # pylint: disable=C0115,W0223,W0612, E0102
                node_id = "dummy_node_test_id_alredy_taken"

            self.assertEqual(len(cm.output), 1)
            self.assertEqual(len(cm.records), 1)
            self.assertIn("has the same node_id as", cm.output[0])

    def test_node_default_io(self):
        """Test that the default IO is set correctly"""

        class DummyNode(Node):  # pylint: disable=C0115,W0223,W0612, E0102
            left = NodeInput()
            right = NodeInput()
            out = NodeOutput()
            node_id = "test_node_default_io"

            async def on_trigger(self):
                return True

        node = DummyNode()
        properties = node.properties
        assert "io" in properties
        assert "ip" in properties["io"]
        assert "left" in properties["io"]["ip"]
        assert "id" in properties["io"]["ip"]["left"]

        assert properties["io"]["ip"]["left"]["id"] == "left"
        assert node.io.left.id == "left"
        assert node.left.id == "left"
        assert node.io.left.name == "left"

        node2 = DummyNode()
        assert node2.id != node.id
        assert node2.left != node.left
        assert node2.io.left != node.io.left
        assert node2.io.left == node2.left

    def test_node_serialization(self):
        """Test that the node can be serialized correctly"""

        class DummyNode(Node):  # pylint: disable=C0115,W0223,W0612, E0102
            left = NodeInput()
            right = NodeInput()
            out = NodeOutput()
            node_id = "test_node_serialization"

            async def on_trigger(self):
                return True

        node = DummyNode()

        ser = node.serialize()

        sercomp = {"id": node.id, "nid": "test_node_serialization"}
        self.assertDictEqual(
            ser,
            sercomp,
        )

        node2 = DummyNode()
        node2.left.set_default_value(42)
        ser2 = node2.serialize()
        sercomp2 = {
            "id": "3cf952ea6d57493288d2aa32f43b2899",
            "nid": "test_node_serialization",
            "io": {"ip": {"left": {"default_value": 42}}},
        }
        sercomp2["id"] = node2.id
        self.assertDictEqual(
            ser2,
            sercomp2,
        )

    async def test_node_deserialization(self):
        """Test that the node can be deserialized correctly"""

        class DummyNode(Node):  # pylint: disable=C0115,W0223,W0612, E0102
            left = NodeInput()
            right = NodeInput()
            out = NodeOutput()
            node_id = "test_node_deserialization"

            async def on_trigger(self):
                self.out.value = self.left.value + self.right.value
                return True

        node_data = {
            "id": "3cf952ea6d57493288d2aa32f43b2899",
            "io": {"ip": {"left": {"default_value": 4}, "right": {"default_value": 6}}},
        }
        node = DummyNode(node_data).initialize()
        print(node.n_calls)
        print(node.left.n_calls)
        self.assertEqual(node.left.n_calls["set_value"], 1)

        await node.await_done()

        assert node.left.value == 4
        assert node.right.value == 6
        assert node.out.value == 10

    def test_nodeio_default_value(self):
        """Test that the default value of a NodeIO is set correctly"""

        class DummyNode(Node):  # pylint: disable=C0115,W0223,W0612, E0102
            left = NodeInput(default_value=1)
            node_id = "test_nodeio_default_value"

            async def on_trigger(self):
                return True

        dummy_node = DummyNode()
        dummy_node.initialize()
        assert (
            dummy_node.io.left.value == 1
        ), f"NodeIO value is '{dummy_node.io.left.value}' instead of 1"

    def test_nodeio_value_set(self):
        """Test that the value of a NodeIO can be set correctly"""

        class DummyNode(Node):  # pylint: disable=C0115,W0223,W0612, E0102
            left = NodeInput()
            node_id = "test_nodeIO_value_set"

            async def on_trigger(self):
                return True

        node = DummyNode()
        node.initialize()
        node.io.left.value = 1
        assert (
            node.io.left.value == 1
        ), f"NodeIO value is '{node.io.left.value}' instead of 1"

    async def test_node_trigger(self):
        """Test that the node can be triggered correctly"""

        class DummyNode(Node):  # pylint: disable=C0115,W0223,W0612, E0102
            left = NodeInput(default_value=1)
            right = NodeInput(default_value=2)
            out = NodeOutput()
            node_id = "test_node_trigger"

            async def on_trigger(
                self,
            ):
                self.io.out.value = self.io.left.value + self.io.right.value
                return True

        node = DummyNode()
        with self.assertRaises(NodeInitalizationError):
            node.trigger()

        node.initialize()

        await node.await_done()
        assert (
            node.io.out.value == 3
        ), f"NodeIO value is '{node.io.out.value}' instead of 3"

    async def test_node_delaytrigger(self):
        """Test that the node can be triggered correctly even if it takes a while"""

        class DummyNode(Node):  # pylint: disable=C0115,W0223,W0612, E0102
            left = NodeInput(default_value=1)
            right = NodeInput(default_value=2)
            out = NodeOutput()
            node_id = "test_node_delaytrigger"

            async def on_trigger(
                self,
            ):
                await asyncio.sleep(1)
                self.io.out.value = self.io.left.value + self.io.right.value
                return True

        node = DummyNode()
        with self.assertRaises(NodeInitalizationError):
            node.trigger()

        node.initialize()

        await node.await_done()
        assert (
            node.io.out.value == 3
        ), f"NodeIO value is '{node.io.out.value}' instead of 3"

    async def test_error_in_callback(self):
        """Test that an error in the callback is handled correctly"""

        class DummyNode(Node):  # pylint: disable=C0115,W0223,W0612, E0102
            left = NodeInput(default_value=1)
            right = NodeInput(default_value=2)
            output = NodeOutput()
            node_id = "test_error_in_callback"

            async def on_trigger(
                self,
            ):
                self.output.value = self.left.value + self.right.value
                return True

        node_1 = DummyNode(id="node_1").initialize()
        node_2 = DummyNode(id="node_2").initialize()

        node_1.output.connect_to(node_2.left)
        node_2.output.connect_to(node_1.left)
        node_1.left.value = 1
        node_1.right.value = 1
        node_2.right.value = 1

        class TestError(Exception):  # pylint: disable=C0115
            pass

        def setddata_cb(name: NodeDataName, new: Any, old: Any, src: Node):
            if new >= 5:
                raise TestError("Test")

        node_1.on("set.data", setddata_cb)

        node_1.trigger()
        with self.assertRaises(TriggerException):
            await Node.await_all(node_1, node_2, timeout=0.2)

    async def test_sync_trigger_func(self):
        """Test that the on_trigger method can be sync"""

        class DummyNode(Node):  # pylint: disable=C0115,W0223,W0612, E0102
            left = NodeInput(default_value=1)
            right = NodeInput(default_value=2)
            output = NodeOutput()
            node_id = "test_sync_on_trigger"

            def on_trigger(self):  # pylint: disable=W0236
                self.output.value = self.left.value + self.right.value
                return True

        node_1 = DummyNode(id="node_1").initialize()
        node_1.left.value = 1
        node_1.right.value = 1
        node_1.trigger()
        await node_1.await_done()
        assert node_1.output.value == 2

    def test_node_remove(self):
        """Test that the node can be removed correctly"""

        class DummyNode(Node):
            node_id = "test_node_remove"

            async def on_trigger(self):
                return True

        node = DummyNode().initialize()
        node.disable()

    def test_node_repr(self):
        """Test that the node repr is correct"""

        class DummyNode(Node):
            node_id = "test_node_repr"
            ip1 = NodeInput()
            ip2 = NodeInput()
            op1 = NodeOutput()

            async def on_trigger(self):
                return True

        node = DummyNode(id="n1").initialize()
        self.assertEqual(repr(node), "DummyNode(n1): ip1, ip2 --> op1")
