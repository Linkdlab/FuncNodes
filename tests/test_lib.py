"""Tests for the lib module."""

import unittest
import sys
from funcnodes.nodemaker import NodeDecorator
from funcnodes.lib import module_to_shelf, serialize_shelfe, get_node_in_shelf


@NodeDecorator("test_lib_testfunc")
def testfunc(int: int, str: str) -> str:
    """Test function for testing the lib module.
    Args:
        int (int): An integer.
        str (str): A string.

    Returns:
        str: A string.
    """
    return str * int


class TestLib(unittest.TestCase):
    def test_module_to_shelf(self):
        expected = {
            "description": "Tests for the lib module.",
            "name": "test_lib",
            "nodes": [
                {
                    "node_id": "test_lib_testfunc",
                    "description": "Test function for testing the lib module.",
                    "node_name": "testfunc",
                    "inputs": [
                        {
                            "description": "An integer.",
                            "name": "int",
                            "type": "int",
                            "uuid": "int",
                        },
                        {
                            "description": "A string.",
                            "name": "str",
                            "type": "str",
                            "uuid": "str",
                        },
                    ],
                    "outputs": [
                        {
                            "description": "A string.",
                            "name": "out",
                            "type": "str",
                            "uuid": "out",
                        }
                    ],
                }
            ],
            "subshelves": [],
        }
        self.maxDiff = None
        from pprint import pprint

        self.assertEqual(
            expected, serialize_shelfe(module_to_shelf(sys.modules[self.__module__]))
        )
