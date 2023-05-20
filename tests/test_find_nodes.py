"""
Test the autodetectio0n of nodes by id
"""
from FuncNodes.nodespace import NodeSpace
import unittest


class TesFindNodes(unittest.TestCase):
    """Test TesFindNodes"""

    def test_find_np_nodes(self):
        """Test the creation of a NodeSpace"""
        ns = NodeSpace()
        self.assertListEqual(ns.lib.shelves, [])
        n1 = ns.new_node("np.random.random_sample")
        assert n1.node_id == "np.random.random_sample", "The node should be created"

        assert len(ns.lib.shelves) == 1, "The numpy shelf should be added"
        npshelf = ns.lib.shelves[0]
        assert npshelf["name"] == "numpy", "The numpy shelf should be added"
        rand_shelf = None
        for shelf in npshelf["shelves"]:
            if shelf["name"] == "random":
                rand_shelf = shelf
                break
        assert rand_shelf is not None, "The random shelf should be added"

        sampling_shelf = None
        for shelf in rand_shelf["shelves"]:
            if shelf["name"] == "sampling":
                sampling_shelf = shelf
                break
        assert sampling_shelf is not None, "The sampling shelf should be added"

        random_sample_node = None
        for node in sampling_shelf["nodes"]:
            if node.node_id == "np.random.random_sample":
                random_sample_node = node
                break
        assert random_sample_node is not None, "The random_sample node should be added"

        assert isinstance(
            n1, random_sample_node
        ), "The node should be an instance of the random_sample node"
