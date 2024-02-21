import unittest
from unittest.mock import Mock
from funcnodes import (
    NodeInput,
    NodeOutput,
    NodeConnectionError,
    MultipleConnectionsError,
)

from funcnodes.io import raise_allow_connections, NodeAlreadyDefinedError, NoValue


class TestNodeIO(unittest.TestCase):
    def setUp(self):
        self.input_1 = NodeInput(id="input1")
        self.output_1 = NodeOutput(id="output1")
        self.input_2 = NodeInput(id="input2")
        self.output_2 = NodeOutput(id="output2")

    def test_create_node_io(self):
        self.assertEqual(self.input_1.name, "input1")
        self.assertEqual(self.output_1.name, "output1")

    def test_connections(self):
        self.assertEqual(len(self.output_1.connections), 0)
        self.assertEqual(self.output_1.connections, self.output_1._connected)

    def test_serialize_node_io(self):
        serialized_input = self.input_1.serialize()
        self.assertEqual(
            serialized_input,
            {
                "name": "input1",
                "id": "input1",
                "is_input": True,
                "type": "Any",
                "render_options": {},
                "value_options": {},
            },
        )
        serialized_output = self.output_1.serialize()
        self.assertEqual(
            serialized_output,
            {
                "name": "output1",
                "type": "Any",
                "id": "output1",
                "is_input": False,
                "render_options": {},
                "value_options": {},
            },
        )

    def test_connect_input_to_output(self):
        self.input_1.connect(self.output_1)
        self.assertIn(self.output_1, self.input_1.connections)
        self.assertIn(self.input_1, self.output_1.connections)

    def test_connect_output_to_input(self):
        self.output_1.connect(self.input_1)
        self.assertIn(self.input_1, self.output_1.connections)
        self.assertIn(self.output_1, self.input_1.connections)

    def test_connection_exceptions(self):
        with self.assertRaises(NodeConnectionError):
            self.input_1.connect(self.input_2)
        with self.assertRaises(NodeConnectionError):
            self.output_1.connect(self.output_2)

    def test_multiple_connections_error(self):
        self.input_1.connect(self.output_1)
        with self.assertRaises(MultipleConnectionsError):
            self.input_1.connect(self.output_2)

    def test_allow_multiple_connections(self):
        self.input_1._allow_multiple = True
        self.input_1.connect(self.output_1)
        self.input_1.connect(self.output_2)  # Should not raise an exception
        self.assertEqual(len(self.input_1.connections), 2)

    def test_connect_same_multiple_times(self):
        self.input_1.connect(self.output_1)
        self.input_1.connect(self.output_1)
        self.assertEqual(len(self.input_1.connections), 1)

    def test_disconnect(self):
        self.input_1.connect(self.output_1)
        self.input_1.disconnect(self.output_1)
        self.assertNotIn(self.output_1, self.input_1.connections)
        self.assertNotIn(self.input_1, self.output_1.connections)

        self.input_1.connect(self.output_1)
        self.input_1.d(self.output_1)
        self.assertNotIn(self.output_1, self.input_1.connections)
        self.assertNotIn(self.input_1, self.output_1.connections)

    def test_disconnect_all(self):
        self.output_1.connect(self.input_1)
        self.output_1.connect(self.input_2)
        self.output_1.disconnect()
        self.assertEqual(len(self.output_1.connections), 0)
        self.assertEqual(len(self.input_1.connections), 0)
        self.assertEqual(len(self.input_2.connections), 0)

    def test_set_value(self):
        test_value = 123
        self.input_1.value = test_value
        self.assertEqual(self.input_1.value, test_value)

    def test_connect_with_replace(self):
        self.input_1.connect(self.output_1)
        self.input_1.connect(self.output_2, replace=True)
        self.assertEqual(len(self.input_1.connections), 1)
        self.assertEqual(len(self.output_1.connections), 0)
        self.assertEqual(len(self.output_2.connections), 1)

    def test_set_node(self):
        node = Mock()
        self.input_1.node = node
        self.assertEqual(self.input_1.node, node)

    def test_double_set_node(self):
        node = Mock()
        self.input_1.node = node
        self.assertEqual(self.input_1.node, node)
        self.input_1.node = (
            node  # should not raise an exception since it's the same node
        )
        self.assertEqual(self.input_1.node, node)

        node2 = Mock()

        with self.assertRaises(NodeAlreadyDefinedError):
            self.input_1.node = node2

    def test_trigger_input(self):
        # mock with a trigger functan that returs the input
        node = Mock(trigger=Mock())

        self.input_1.value = 123
        stack = self.input_1.trigger()
        self.assertEqual(len(stack), 0)

        self.input_1.node = node

        ts = Mock()
        self.input_1.trigger(triggerstack=ts)

        node.trigger.assert_called_once_with(triggerstack=ts)

    def test_trigger_output(self):
        node = Mock(trigger=Mock())
        self.assertEqual(len(self.output_1.trigger()), 0)
        self.output_1.node = node
        self.input_1.node = node
        self.output_1.value = 123
        self.input_1.connect(self.output_1)

        ts = Mock()
        self.output_1.trigger(triggerstack=ts)

        node.trigger.assert_called_once_with(triggerstack=ts)


class RaiseAllowConnectionsTest(unittest.TestCase):
    def setUp(self):
        self.ip1 = NodeInput(name="ip1")
        self.ip2 = NodeInput(name="ip2")
        self.op1 = NodeOutput(name="op1")
        self.op2 = NodeOutput(name="op2")

    def test_ip2ip(self):
        with self.assertRaises(NodeConnectionError):
            raise_allow_connections(self.ip1, self.ip2)

    def test_op2op(self):
        with self.assertRaises(NodeConnectionError):
            raise_allow_connections(self.op1, self.op2)

    def test_ip2op(self):
        raise_allow_connections(self.ip1, self.op1)

    def test_double_connect(self):
        self.ip1.connect(self.op1)
        raise_allow_connections(self.ip1, self.op1)

    def test_forbidden_multiple_connections(self):
        self.ip1.connect(self.op1)
        # by default inputs do not allow multiple connections
        with self.assertRaises(MultipleConnectionsError):
            raise_allow_connections(self.ip1, self.op2)
        with self.assertRaises(MultipleConnectionsError):
            raise_allow_connections(self.op2, self.ip1)

        # but outputs do
        raise_allow_connections(self.ip2, self.op1)
        raise_allow_connections(self.op1, self.ip2)
