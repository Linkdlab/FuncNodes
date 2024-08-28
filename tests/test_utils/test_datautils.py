import unittest
from funcnodes_core.utils.data import deep_fill_dict, deep_remove_dict_on_equal

# Assuming the functions deep_fill_dict and deep_remove_dict_on_equal are defined as provided


class TestDictFunctions(unittest.TestCase):
    def test_deep_fill_basic(self):
        """Test basic functionality of deep_fill_dict."""
        target = {"a": 1}
        source = {"b": 2}
        expected = {"a": 1, "b": 2}
        self.assertEqual(deep_fill_dict(target, source), expected)
        self.assertEqual(target, expected)

    def test_deep_fill_basic2(self):
        """Test basic functionality of deep_fill_dict."""
        target = {}
        source = {"b": {"c": [2]}}
        expected = {"b": {"c": [2]}}
        self.assertEqual(
            deep_fill_dict(target, source, inplace=False, overwrite_existing=True),
            expected,
        )
        self.assertEqual(target, {})

    def test_deep_fill_overwrite(self):
        """Test overwriting existing keys in deep_fill_dict."""
        target = {"a": 1}
        source = {"a": 2}
        deep_fill_dict(target, source, True)
        self.assertEqual(target, {"a": 2})
        target = {"a": 1}
        deep_fill_dict(target, source, False)

        self.assertEqual(target, {"a": 1})
        self.assertEqual(source, {"a": 2})

    def test_deep_fill_overwrite_not_inplace(self):
        """Test overwriting existing keys in deep_fill_dict."""
        target = {"a": 1}
        source = {"a": 2}
        res = deep_fill_dict(target, source, True, inplace=False)
        self.assertEqual(target, {"a": 1})
        self.assertEqual(source, {"a": 2})
        self.assertEqual(res, {"a": 2})

        res = deep_fill_dict(target, source, False, inplace=False)
        self.assertEqual(target, {"a": 1})
        self.assertEqual(source, {"a": 2})
        self.assertEqual(res, {"a": 1})

    def test_deep_fill_nested(self):
        """Test nested dictionaries in deep_fill_dict."""
        target = {"a": {"b": 1}}
        source = {"a": {"c": 2}, "d": 3}
        expected = {"a": {"b": 1, "c": 2}, "d": 3}
        self.assertEqual(deep_fill_dict(target, source), expected)

    def test_deep_remove_basic(self):
        """Test basic functionality of deep_remove_dict_on_equal."""
        target = {"a": 1, "b": 2}
        remove = {"b": 2}
        expected = {"a": 1}
        self.assertEqual(deep_remove_dict_on_equal(target, remove), expected)

    def test_deep_remove_nested(self):
        """Test nested dictionaries in deep_remove_dict_on_equal."""
        target = {"a": {"b": 1, "c": 2}, "d": 3}
        remove = {"a": {"b": 1}}
        expected = {"a": {"c": 2}, "d": 3}
        self.assertEqual(deep_remove_dict_on_equal(target, remove), expected)

    def test_edge_case_empty_dicts(self):
        """Test edge case with empty dictionaries."""
        self.assertEqual(deep_fill_dict({}, {}), {})
        self.assertEqual(deep_remove_dict_on_equal({}, {}), {})

    def test_corner_case_non_dict_values(self):
        """Test handling of non-dict values."""
        target = {"a": [1, 2], "b": "string"}
        source = {"a": [3, 4], "c": "new"}
        remove = {"b": "string", "c": "new"}
        filled = deep_fill_dict(target, source, True)
        expected_fill = {"a": [3, 4], "b": "string", "c": "new"}
        self.assertEqual(filled, expected_fill)
        cleaned = deep_remove_dict_on_equal(filled, remove)
        expected_clean = {"a": [3, 4]}
        self.assertEqual(cleaned, expected_clean)


if __name__ == "__main__":
    unittest.main()
