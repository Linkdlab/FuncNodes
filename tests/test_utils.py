import unittest
import logging

logging.basicConfig(level=logging.INFO)
from FuncNodes.utils import flatten_dict


class TestUtils(unittest.TestCase):
    def test_flatten_dict(self):
        """Test the flatten_dict function"""
        d = {
            "a": {"b": {"c": 1}, "d": 2, "e": [1, 2, 3]},
            "f": [[1, 2], [3, [4, 5]]],
            "g": "test",
            "h": [1, {"i": 7, "j": [8, 9]}],
        }

        er = {
            "a__b__c": 1,
            "a__d": 2,
            "a__e__0": 1,
            "a__e__1": 2,
            "a__e__2": 3,
            "f__0__0": 1,
            "f__0__1": 2,
            "f__1__0": 3,
            "f__1__1__0": 4,
            "f__1__1__1": 5,
            "g": "test",
            "h__0": 1,
            "h__1__i": 7,
            "h__1__j__0": 8,
            "h__1__j__1": 9,
        }

        assert flatten_dict(d) == er, f"flatten_dict failed is {flatten_dict(d)}"
