"""
Test examples
"""
import unittest


class TestExamples(unittest.IsolatedAsyncioTestCase):
    async def test_if_node_simple(self):
        from funcnodes.nodes.progflow import IfNode

        if_node = IfNode(
            {
                "id": "test_if_node",
                "io": {
                    "condition": {"default_value": True},
                    "input": {"default_value": "True result"},
                },
            }
        )
        if_node.initialize()

        await if_node.await_done()

        # check that the outputs are correct
        assert if_node.io("then").value == "True result"
        assert if_node.io("else_").value_or_none is None

        # switch the input condition and check the outputs again
        if_node.condition.value = False
        if_node.trigger()
        await if_node.await_done()

        assert if_node.io("then").value_or_none is None
        assert if_node.io("else_").value == "True result"

    async def test_merge_input_node(self):
        from funcnodes.nodes.progflow import MergeInputNode

        # Create a MergeInputNode instance
        merge_node = MergeInputNode()
        merge_node.initialize()

        # Add inputs to the MergeInputNode
        merge_node.add_mergeinput()
        merge_node.add_mergeinput()
        merge_node.add_mergeinput()

        # Set values for the inputs
        merge_node.get_inputs()[0].value = [1, 2, 3]
        merge_node.get_inputs()[1].value = "hello"

        # Trigger the MergeInputNode
        merge_node.trigger()
        await merge_node.await_done()

        # Check if the output is the merged list
        self.assertEqual(merge_node.out.value, [[1, 2, 3], "hello"])

        # Remove an input
        merge_node.remove_mergeinput(0)

        # Check if the input was removed
        self.assertEqual(len(merge_node.get_inputs()), 2)

        # Test serialization
        serialized_data = merge_node.serialize()
        print(serialized_data)
        self.assertEqual(len(serialized_data), 3)
        self.assertListEqual(
            sorted(list(serialized_data.keys())), sorted(["nid", "io", "id"])
        )

        self.assertEqual(serialized_data["nid"], "mergeip")
        self.assertListEqual(sorted(list(serialized_data["io"].keys())), ["ip"])
        self.assertDictEqual(
            list(serialized_data["io"]["ip"].values())[0], {"required": False}
        )
        # Test deserialization
        new_merge_node = MergeInputNode(serialized_data)

        self.assertEqual(len(new_merge_node.get_inputs()), 2)

    async def test_for_node(self):
        import logging

        logging.basicConfig(level=logging.DEBUG)

        from funcnodes.nodes.progflow import ForNode
        from funcnodes.nodes.numpy_nodes.ufunc import AddNode

        fornode = ForNode().initialize()
        addnode = AddNode().initialize()

        fornode.input.value = [1, 2, 3, 4, 5]
        addnode.x2.value = 10

        fornode.do.c(addnode.x1)
        addnode.out.c(fornode.collector)

        await fornode.trigger()
        await fornode.await_done(timeout=1)

        self.assertEqual(fornode.output.value, [11, 12, 13, 14, 15])

        print(fornode.get_state())
