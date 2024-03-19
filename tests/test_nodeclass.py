import unittest
import gc
from unittest.mock import patch
from funcnodes.node import (
    Node,
    AsyncEventManager,
    InTriggerError,
    NodeIdAlreadyExistsError,
    register_node,
    NodeInput,
    NodeOutput,
    TriggerStack,
    NodeMeta,
    NodeKeyError,
    get_nodeclass,
)


class DummyNode(Node):
    node_id = "dummy_node"
    input = NodeInput(id="input", type=int, default=1)
    output = NodeOutput(id="output", type=int)

    async def func(self, input: int) -> int:
        return input


class TestNodeClass(unittest.IsolatedAsyncioTestCase):
    async def test_nodeclass_initialization(self):
        """Test if the NodeClass initializes its properties correctly."""
        # test for abstaract class initialization
        with self.assertRaises(TypeError):
            test_node = Node()  # type: ignore
        test_node = DummyNode()
        self.assertIsInstance(test_node.asynceventmanager, AsyncEventManager)
        self.assertIsNotNone(test_node.uuid)
        self.assertFalse(test_node._reset_inputs_on_trigger)

    async def test_node_add_input_output(self):
        """Test adding inputs and outputs to the node."""
        test_node = DummyNode()
        test_input = NodeInput(id="test_input")
        test_output = NodeOutput(id="test_output")
        test_node.add_input(test_input)
        test_node.add_output(test_output)
        self.assertIn("test_input", test_node.inputs)
        self.assertIn("test_output", test_node.outputs)

        self.assertEqual(len(test_node.inputs), 3)  # input and test_input and trigger
        self.assertEqual(len(test_node.outputs), 2)

    async def test_node_ready_to_trigger(self):
        """Test if the node correctly reports its readiness to trigger."""
        test_node = DummyNode()
        await test_node
        self.assertTrue(test_node.ready_to_trigger())

    async def test_node_trigger(self):
        """Test triggering a node."""
        test_node = DummyNode()
        await test_node
        trigger_stack = test_node.trigger()
        self.assertIsInstance(trigger_stack, TriggerStack)

    async def test_node_trigger_when_already_triggered_raises_error(self):
        """Test triggering a node that is already in trigger raises InTriggerError."""
        test_node = DummyNode()
        with self.assertRaises(InTriggerError):
            test_node.trigger()
            test_node.trigger()

    async def test_double_node_id(self):
        with self.assertRaises(NodeIdAlreadyExistsError):

            class DoubleNode(Node):
                node_id = "dummy_node"

    async def test_await_trigger(self):
        """Test awaiting a trigger."""
        test_node = DummyNode()
        await test_node.await_trigger()
        test_node.trigger()
        await test_node.await_trigger()

    async def test_trigger_stack(self):
        """Test the trigger stack."""
        test_node = DummyNode()
        await test_node
        trigger_stack = test_node.trigger()
        await trigger_stack
        self.assertTrue(trigger_stack.done())
        new_trigger_stack = test_node.trigger(triggerstack=trigger_stack)
        self.assertEqual(trigger_stack, new_trigger_stack)
        self.assertFalse(trigger_stack.done())

    def test_nodeclass_string(self):
        """Test the string representation of the node."""
        test_node = DummyNode(uuid="test_uuid")
        self.assertEqual(str(test_node), "DummyNode(test_uuid)")

    def test_node_status(self):
        test_node = DummyNode()
        self.maxDiff = None
        self.assertEqual(
            test_node.status(),
            {
                "ready": True,
                "in_trigger": False,
                "requests_trigger": False,
                "inputs": {
                    "input": {
                        "connected": False,
                        "has_node": True,
                        "has_value": True,
                        "ready": True,
                        "required": True,
                    },
                    "_triggerinput": {
                        "connected": False,
                        "has_node": True,
                        "has_value": True,
                        "ready": True,
                        "required": False,
                    },
                },
                "outputs": {
                    "output": {
                        "connected": False,
                        "has_node": True,
                        "has_value": False,
                        "ready": True,
                    }
                },
            },
        )

    def test_get_unregistered_nodeclass(self):
        with self.assertRaises(NodeKeyError):
            get_nodeclass("unregistered_nodeclass")

    async def test_delete_node(self):
        gc.collect()
        gc.set_debug(gc.DEBUG_LEAK)

        test_node = DummyNode()
        await test_node
        tnid = id(test_node)
        del test_node
        gc.collect()
        garb = gc.garbage
        gc.set_debug(0)

        from pprint import pprint

        for g in garb:
            if id(g) == tnid:
                print("=" * 60)
                print(g, hex(id(g)))
                for ref in gc.get_referrers(g):
                    print("-" * 60)
                    print(ref)
                    if hasattr(ref, "__dict__"):
                        pprint(vars(ref))
                print(len(gc.get_referrers(g)))
        self.assertEqual(garb, [])


class NodeClassMetaTest(unittest.TestCase):
    """
    Test suite for the NodeClassMeta metaclass.

    This suite tests the custom behavior of NodeClassMeta, ensuring that new classes
    are correctly instantiated, registered, and exceptions are raised as expected.
    """

    def test_meta_creates_new_class_correctly(self):
        """
        Test that NodeClassMeta creates a new class correctly and that
        it is an instance of the meta's own base class.
        """

        # Mock register_node to prevent actual registration during test.
        with patch("funcnodes.node.register_node") as mock_register_node:

            class BaseNodeClass(Node):
                async def func(self, *args, **kwargs):
                    """The function to be executed when the node is triggered."""

            NewNodeClass = NodeMeta(
                "NewNodeClass", (BaseNodeClass,), {"node_id": "new_node_class"}
            )
            self.assertTrue(issubclass(NewNodeClass, BaseNodeClass))
            mock_register_node.assert_called_with(NewNodeClass)

    def test_meta_raises_type_error_for_non_nodeclass_subclass(self):
        """
        Test that NodeClassMeta raises a TypeError when trying to create a class
        that is not a subclass of NodeClass.
        """
        with self.assertRaises(TypeError):

            class InvalidNodeClass(metaclass=NodeMeta):
                pass

    def test_meta_catches_name_error_for_base_nodeclass_definition(self):
        """
        Test that NodeClassMeta catches the NameError when the base NodeClass itself
        is being created. This is expected behavior and should not propagate the exception.
        """
        with self.assertRaises(TypeError):

            class NodeClass(metaclass=NodeMeta):
                pass

    def test_meta_registers_class(self):
        """
        Test that NodeClassMeta attempts to register the new class in the global registry.
        """

        class BaseNodeClass(Node):
            node_id = "test_meta_registers_class"

        # Mock register_node to check that it's being called correctly.
        with patch(
            "funcnodes.node.register_node", side_effect=register_node
        ) as mock_register_node:
            NewNodeClass = NodeMeta(
                "NewNodeClass", (BaseNodeClass,), {"node_id": "new_node_class"}
            )
            mock_register_node.assert_called_once_with(NewNodeClass)

    def test_meta_raises_error_on_duplicate_registration(self):
        """
        Test that NodeClassMeta raises a NodeIdAlreadyExistsError when attempting
        to register a class with a node_id that already exists.
        """

        class BaseNodeClass(Node):
            node_id = "test_meta_raises_error_on_duplicate_registration"

        with self.assertRaises(NodeIdAlreadyExistsError):

            class AnotherBaseNodeClass(BaseNodeClass):
                node_id = "test_meta_raises_error_on_duplicate_registration"
