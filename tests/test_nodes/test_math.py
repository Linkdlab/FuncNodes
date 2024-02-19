import unittest
import sys
import math

from funcnodes import Node


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
            nodeclass = math_nodes.NODE_SHELFE["nodes"]["math." + name]
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
            nodeclass = math_nodes.NODE_SHELFE["nodes"]["math." + name]
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
            nodeclass = math_nodes.NODE_SHELFE["nodes"]["math." + name]
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
            nodeclass = math_nodes.NODE_SHELFE["nodes"]["math." + name]
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
            nodeclass = math_nodes.NODE_SHELFE["nodes"]["math." + name]
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
            nodeclass = math_nodes.NODE_SHELFE["nodes"]["math." + name]
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
            nodeclass = math_nodes.NODE_SHELFE["nodes"]["math." + name]
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
            nodeclass = math_nodes.NODE_SHELFE["nodes"]["math." + name]
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
            (math_nodes.NODE_SHELFE["nodes"]["add_node"], v1 + v2),
            (math_nodes.NODE_SHELFE["nodes"]["sub_node"], v1 - v2),
            (math_nodes.NODE_SHELFE["nodes"]["mul_node"], v1 * v2),
            (math_nodes.NODE_SHELFE["nodes"]["div_node"], v1 / v2),
            (math_nodes.NODE_SHELFE["nodes"]["mod_node"], v1 % v2),
            (math_nodes.NODE_SHELFE["nodes"]["pow_node"], v1**v2),
            (math_nodes.NODE_SHELFE["nodes"]["floor_div_node"], v1 // v2),
            (math_nodes.NODE_SHELFE["nodes"]["greater_node"], v1 > v2),
            (math_nodes.NODE_SHELFE["nodes"]["less_node"], v1 < v2),
            (math_nodes.NODE_SHELFE["nodes"]["equal_node"], v1 == v2),
            (math_nodes.NODE_SHELFE["nodes"]["not_equal_node"], v1 != v2),
            (math_nodes.NODE_SHELFE["nodes"]["greater_equal_node"], v1 >= v2),
            (math_nodes.NODE_SHELFE["nodes"]["less_equal_node"], v1 <= v2),
        ]:
            node = n()

            node.inputs["a"].value = v1
            node.inputs["b"].value = v2
            await node
            self.assertEqual(node.outputs["out"].value, r)

        v = -3.14
        for n, r in [
            (math_nodes.NODE_SHELFE["nodes"]["abs_node"], abs(v)),
            (math_nodes.NODE_SHELFE["nodes"]["neg_node"], -v),
            (math_nodes.NODE_SHELFE["nodes"]["pos_node"], +v),
        ]:
            node = n()
            node.inputs["a"].value = v
            await node
            self.assertEqual(node.outputs["out"].value, r)

        v1 = True
        v2 = False

        for n, r in [
            (math_nodes.NODE_SHELFE["nodes"]["and_node"], v1 and v2),
            (math_nodes.NODE_SHELFE["nodes"]["or_node"], v1 or v2),
            (math_nodes.NODE_SHELFE["nodes"]["xor_node"], v1 ^ v2),
        ]:
            node = n()
            node.inputs["a"].value = v1
            node.inputs["b"].value = v2
            await node
            self.assertEqual(node.outputs["out"].value, r)

        node = math_nodes.NODE_SHELFE["nodes"]["round_node"]()

        node.inputs["a"].value = 5.123456
        node.inputs["ndigits"].value = 2
        await node
        self.assertEqual(node.outputs["out"].value, round(5.123456, 2))

        node = math_nodes.NODE_SHELFE["nodes"]["not_node"]()
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
