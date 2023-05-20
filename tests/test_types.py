import unittest
import logging
from funcnodes.iotypes import IOType
import numpy as np

logging.basicConfig(level=logging.INFO)


class TestUtils(unittest.TestCase):
    def test_numpy_io_types(self):
        from funcnodes.nodes.numpy_nodes.types import (
            ArrayLikeType,
            NdArrayType,
            ndarray_type_creator,
        )

        assert issubclass(
            ArrayLikeType, IOType
        ), f"NumpyArray is not a IOType but a {type(ArrayLikeType)}"
        assert issubclass(
            NdArrayType, IOType
        ), f"NumpyArrayIOType is not a IOType but a {type(NdArrayType)}"

        new_type = ndarray_type_creator()

        assert issubclass(
            new_type, IOType
        ), f"ndarray_type_creator is not a IOType but a {type(new_type)}"

        assert (
            new_type == NdArrayType
        ), f"ndarray_type_creator is not a NdArrayType but {new_type}"

        new_type = ndarray_type_creator(np.uint8)

        assert (
            new_type.cast_value(1.1) == 1
        ), f"cast_value(1.1) is not 1 but {new_type.cast_value(1.1)}"
        assert (
            new_type.cast_value(2) == 2
        ), f"cast_value(2) is not 2 but {new_type.cast_value(2)}"
        assert (
            new_type.cast_value(-2) == 254
        ), f"cast_value(-2) is not 254 but {new_type.cast_value(-2)}"
        assert (
            new_type.cast_value(np.nan) == 0
        ), f"cast_value(np.nan) is not 0 but {new_type.cast_value(np.nan)}"
        print()

        new_type = ndarray_type_creator(np.uint8, (2, 2))
        self.assertRaises(ValueError, new_type.cast_value, 1.1)

        assert np.array_equal(
            new_type.cast_value([1.1, 2, -2, np.nan]), [[1, 2], [254, 0]]
        )

        # IOType._type_graph
        # import networkx as nx
        # import matplotlib.pyplot as plt

        # nx.draw(IOType._type_graph, with_labels=True)
        # plt.show()
