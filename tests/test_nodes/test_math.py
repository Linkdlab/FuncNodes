import unittest
import sys
import math

from funcnodes import Node
from funcnodes.lib import get_node_in_shelf


_CONSTANTS = ["e", "pi", "inf", "nan", "tau"]
_FLOAT_FUNCTIONS = [
    "acos",
    "acosh",
    "asin",
    "asinh",
    "atan",
    "atanh",
    "ceil",
    "cos",
    "cosh",
    "degrees",
    "erf",
    "erfc",
    "exp",
    "expm1",
    "fabs",
    "floor",
    "gamma",
    "lgamma",
    "log",
    "log10",
    "log1p",
    "log2",
    "modf",
    "radians",
    "sin",
    "sinh",
    "sqrt",
    "tan",
    "tanh",
]
_FLOAT_FUNCTIONS_INT = ["trunc"]

_FLOAT_FUNCTIONS_BOOL = [
    "isfinite",
    "isinf",
    "isnan",
]

_FLOAT_FLOAT_FUNCTIONS = [
    "atan2",
    "copysign",
    "fmod",
    "hypot",
    "pow",
    "remainder",
]
_FLOAT_FLOAT_FUNCTIONS_BOOL = ["isclose"]

_INT_FUNCTIONS = ["factorial"]

_INT_INT_FUNCTIONS = [
    "gcd",
]


_FLOAT_INT_FUNCTIONS = ["ldexp"]
_VEC_FUNCTIONS = ["fsum"]
_VEC_VEC_FUNCTIONS = []

if sys.version_info >= (3, 8):
    _VEC_VEC_FUNCTIONS.append("dist")
    _VEC_FUNCTIONS.append("prod")
    _INT_INT_FUNCTIONS.append("comb")
    _INT_INT_FUNCTIONS.append("perm")
    _INT_FUNCTIONS.append("isqrt")

if sys.version_info >= (3, 9):
    _INT_INT_FUNCTIONS.append("lcm")
    _FLOAT_FLOAT_FUNCTIONS.append("nextafter")

if sys.version_info >= (3, 11):
    _FLOAT_FUNCTIONS.append("exp2")
    _FLOAT_FUNCTIONS.append("cbrt")


if sys.version_info >= (3, 12):
    _VEC_VEC_FUNCTIONS.append("sumprod")


class TestMathNodes(unittest.IsolatedAsyncioTestCase):
    async def test_constants(self):
        from funcnodes.basic_nodes import math as math_nodes

        for name in _CONSTANTS:
            _, nodeclass = get_node_in_shelf(math_nodes.NODE_SHELFE, "math." + name)

            assert issubclass(nodeclass, Node)
            node: Node = nodeclass()
            await node
            r = getattr(math, name)
            v = node.outputs["out"].value
            if math.isnan(r):
                self.assertTrue(math.isnan(v))
            else:
                self.assertEqual(v, r)

    async def test_float_functions(self):
        from funcnodes.basic_nodes import math as math_nodes

        for name in _FLOAT_FUNCTIONS + _FLOAT_FUNCTIONS_BOOL + _FLOAT_FUNCTIONS_INT:
            _, nodeclass = get_node_in_shelf(math_nodes.NODE_SHELFE, "math." + name)
            assert issubclass(nodeclass, Node)
            node: Node = nodeclass()
            await node

            _f = getattr(math, name)
            r = None
            for v in [0.5, 1.5]:
                try:
                    r = _f(v)
                    break
                except ValueError:
                    continue
            if r is None:
                raise ValueError(f"could not find valid input for {name}")

            node.inputs["a"].value = v
            await node
            self.assertEqual(node.outputs["out"].value, r)

    async def test_float_float_functions(self):
        from funcnodes.basic_nodes import math as math_nodes

        for name in _FLOAT_FLOAT_FUNCTIONS + _FLOAT_FLOAT_FUNCTIONS_BOOL:
            _, nodeclass = get_node_in_shelf(math_nodes.NODE_SHELFE, "math." + name)
            assert issubclass(nodeclass, Node)
            node: Node = nodeclass()
            await node
            _f = getattr(math, name)

            r = None
            for v1 in [0.5, 1.5]:
                for v2 in [0.5, 1.5]:
                    try:
                        r = _f(v1, v2)
                        break
                    except ValueError:
                        continue
                if r is not None:
                    break
            if r is None:
                raise ValueError(f"could not find valid input for {name}")

            node.inputs["a"].value = v1
            node.inputs["b"].value = v2
            await node
            self.assertEqual(node.outputs["out"].value, r)

    async def test_vec_functions(self):
        from funcnodes.basic_nodes import math as math_nodes

        for name in _VEC_FUNCTIONS:
            _, nodeclass = get_node_in_shelf(math_nodes.NODE_SHELFE, "math." + name)
            assert issubclass(nodeclass, Node)
            node: Node = nodeclass()
            await node

            _f = getattr(math, name)

            v = [0.5, 1.5, 2.5]
            r = _f(v)

            node.inputs["a"].value = v
            await node
            self.assertEqual(node.outputs["out"].value, r)

    async def test_vec_vec_functions(self):
        from funcnodes.basic_nodes import math as math_nodes

        for name in _VEC_VEC_FUNCTIONS:
            _, nodeclass = get_node_in_shelf(math_nodes.NODE_SHELFE, "math." + name)
            assert issubclass(nodeclass, Node)
            node: Node = nodeclass()
            await node

            _f = getattr(math, name)

            v1 = [0.5, 1.5, 2.5]
            v2 = [2.5, 1.0, 0.1]
            r = _f(v1, v2)

            node.inputs["a"].value = v1
            node.inputs["b"].value = v2
            await node
            self.assertEqual(node.outputs["out"].value, r)

    async def test_int_functions(self):
        from funcnodes.basic_nodes import math as math_nodes

        for name in _INT_FUNCTIONS:
            _, nodeclass = get_node_in_shelf(math_nodes.NODE_SHELFE, "math." + name)
            assert issubclass(nodeclass, Node)
            node: Node = nodeclass()
            await node

            _f = getattr(math, name)

            v = 10
            r = _f(v)

            node.inputs["a"].value = v
            await node
            self.assertEqual(node.outputs["out"].value, r)

    async def test_int_int_functions(self):
        from funcnodes.basic_nodes import math as math_nodes

        for name in _INT_INT_FUNCTIONS:
            _, nodeclass = get_node_in_shelf(math_nodes.NODE_SHELFE, "math." + name)
            assert issubclass(nodeclass, Node)
            node: Node = nodeclass()
            await node
            _f = getattr(math, name)

            v1 = 10
            v2 = 2
            r = _f(v1, v2)

            node.inputs["a"].value = v1
            node.inputs["b"].value = v2
            await node
            self.assertEqual(node.outputs["out"].value, r)

    async def test_float_int_functions(self):
        from funcnodes.basic_nodes import math as math_nodes

        for name in _FLOAT_INT_FUNCTIONS:
            _, nodeclass = get_node_in_shelf(math_nodes.NODE_SHELFE, "math." + name)
            assert issubclass(nodeclass, Node)
            node: Node = nodeclass()
            await node

            _f = getattr(math, name)

            v1 = 3.14
            v2 = 2
            r = _f(v1, v2)

            node.inputs["a"].value = v1
            node.inputs["b"].value = v2
            await node
            self.assertEqual(node.outputs["out"].value, r)

    async def test_buildin_math(self):
        from funcnodes.basic_nodes import math as math_nodes

        v1 = 3.14
        v2 = 2
        for n, r in [
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "add_node")[1], v1 + v2),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "sub_node")[1], v1 - v2),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "mul_node")[1], v1 * v2),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "div_node")[1], v1 / v2),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "mod_node")[1], v1 % v2),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "pow_node")[1], v1**v2),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "floor_div_node")[1], v1 // v2),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "greater_node")[1], v1 > v2),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "less_node")[1], v1 < v2),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "equal_node")[1], v1 == v2),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "not_equal_node")[1], v1 != v2),
            (
                get_node_in_shelf(math_nodes.NODE_SHELFE, "greater_equal_node")[1],
                v1 >= v2,
            ),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "less_equal_node")[1], v1 <= v2),
        ]:
            node = n()

            node.inputs["a"].value = v1
            node.inputs["b"].value = v2
            await node
            self.assertEqual(node.outputs["out"].value, r)

        v = -3.14
        for n, r in [
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "abs_node")[1], abs(v)),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "neg_node")[1], -v),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "pos_node")[1], +v),
        ]:
            node = n()
            node.inputs["a"].value = v
            await node
            self.assertEqual(node.outputs["out"].value, r)

        v1 = True
        v2 = False

        for n, r in [
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "and_node")[1], v1 and v2),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "or_node")[1], v1 or v2),
            (get_node_in_shelf(math_nodes.NODE_SHELFE, "xor_node")[1], v1 ^ v2),
        ]:
            node = n()
            node.inputs["a"].value = v1
            node.inputs["b"].value = v2
            await node
            self.assertEqual(node.outputs["out"].value, r)

        node = get_node_in_shelf(math_nodes.NODE_SHELFE, "round_node")[1]()

        node.inputs["a"].value = 5.123456
        node.inputs["ndigits"].value = 2
        await node
        self.assertEqual(node.outputs["out"].value, round(5.123456, 2))

        node = get_node_in_shelf(math_nodes.NODE_SHELFE, "not_node")[1]()
        node.inputs["a"].value = True
        await node
        self.assertEqual(node.outputs["out"].value, False)

    async def test_count_math_nodes(self):
        from funcnodes.basic_nodes import math as math_nodes

        all_funcs = (
            _CONSTANTS
            + _FLOAT_FUNCTIONS
            + _FLOAT_FUNCTIONS_BOOL
            + _FLOAT_FUNCTIONS_INT
            + _FLOAT_FLOAT_FUNCTIONS
            + _FLOAT_FLOAT_FUNCTIONS_BOOL
            + _INT_FUNCTIONS
            + _INT_INT_FUNCTIONS
            + _FLOAT_INT_FUNCTIONS
            + _VEC_FUNCTIONS
            + _VEC_VEC_FUNCTIONS
        )
        all_nodes = set(
            [
                attr
                for name, attr in vars(math_nodes).items()
                if isinstance(attr, type)
                and issubclass(attr, Node)
                and attr.node_id.startswith("math.")
            ]
        )

        self.assertEqual(len(all_funcs), len(all_nodes))
