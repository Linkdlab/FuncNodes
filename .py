
import numpy as np
import numpy.typing as npt
from funcnodes.io import NodeInput, NodeOutput
from funcnodes.node import Node
from .types import NdArrayType


class AbsNode(Node):
    node_id = "np.abs"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.abs(
            x1.value
        )
        return True



class AbsoluteNode(Node):
    node_id = "np.absolute"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.absolute(
            x1.value
        )
        return True



class AddNode(Node):
    node_id = "np.add"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.add(
            x1.value, x2.value
        )
        return True



class ArccosNode(Node):
    node_id = "np.arccos"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.arccos(
            x1.value
        )
        return True



class ArccoshNode(Node):
    node_id = "np.arccosh"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.arccosh(
            x1.value
        )
        return True



class ArcsinNode(Node):
    node_id = "np.arcsin"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.arcsin(
            x1.value
        )
        return True



class ArcsinhNode(Node):
    node_id = "np.arcsinh"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.arcsinh(
            x1.value
        )
        return True



class ArctanNode(Node):
    node_id = "np.arctan"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.arctan(
            x1.value
        )
        return True



class Arctan2Node(Node):
    node_id = "np.arctan2"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.arctan2(
            x1.value, x2.value
        )
        return True



class ArctanhNode(Node):
    node_id = "np.arctanh"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.arctanh(
            x1.value
        )
        return True



class BitwiseAndNode(Node):
    node_id = "np.bitwise_and"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.bitwise_and(
            x1.value, x2.value
        )
        return True



class BitwiseNotNode(Node):
    node_id = "np.bitwise_not"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.bitwise_not(
            x1.value
        )
        return True



class BitwiseOrNode(Node):
    node_id = "np.bitwise_or"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.bitwise_or(
            x1.value, x2.value
        )
        return True



class BitwiseXorNode(Node):
    node_id = "np.bitwise_xor"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.bitwise_xor(
            x1.value, x2.value
        )
        return True



class CbrtNode(Node):
    node_id = "np.cbrt"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.cbrt(
            x1.value
        )
        return True



class CeilNode(Node):
    node_id = "np.ceil"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.ceil(
            x1.value
        )
        return True



class ConjNode(Node):
    node_id = "np.conj"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.conj(
            x1.value
        )
        return True



class ConjugateNode(Node):
    node_id = "np.conjugate"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.conjugate(
            x1.value
        )
        return True



class CopysignNode(Node):
    node_id = "np.copysign"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.copysign(
            x1.value, x2.value
        )
        return True



class CosNode(Node):
    node_id = "np.cos"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.cos(
            x1.value
        )
        return True



class CoshNode(Node):
    node_id = "np.cosh"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.cosh(
            x1.value
        )
        return True



class Deg2RadNode(Node):
    node_id = "np.deg2rad"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.deg2rad(
            x1.value
        )
        return True



class DegreesNode(Node):
    node_id = "np.degrees"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.degrees(
            x1.value
        )
        return True



class DivideNode(Node):
    node_id = "np.divide"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.divide(
            x1.value, x2.value
        )
        return True



class DivmodNode(Node):
    node_id = "np.divmod"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out1 = NodeOutput(type=NdArrayType)    out2 = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.divmod(
            x1.value, x2.value
        )
        return True



class EqualNode(Node):
    node_id = "np.equal"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.equal(
            x1.value, x2.value
        )
        return True



class ExpNode(Node):
    node_id = "np.exp"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.exp(
            x1.value
        )
        return True



class Exp2Node(Node):
    node_id = "np.exp2"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.exp2(
            x1.value
        )
        return True



class Expm1Node(Node):
    node_id = "np.expm1"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.expm1(
            x1.value
        )
        return True



class FabsNode(Node):
    node_id = "np.fabs"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.fabs(
            x1.value
        )
        return True



class FloatPowerNode(Node):
    node_id = "np.float_power"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.float_power(
            x1.value, x2.value
        )
        return True



class FloorNode(Node):
    node_id = "np.floor"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.floor(
            x1.value
        )
        return True



class FloorDivideNode(Node):
    node_id = "np.floor_divide"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.floor_divide(
            x1.value, x2.value
        )
        return True



class FmaxNode(Node):
    node_id = "np.fmax"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.fmax(
            x1.value, x2.value
        )
        return True



class FminNode(Node):
    node_id = "np.fmin"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.fmin(
            x1.value, x2.value
        )
        return True



class FmodNode(Node):
    node_id = "np.fmod"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.fmod(
            x1.value, x2.value
        )
        return True



class FrexpNode(Node):
    node_id = "np.frexp"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out1 = NodeOutput(type=NdArrayType)    out2 = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.frexp(
            x1.value
        )
        return True



class GcdNode(Node):
    node_id = "np.gcd"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.gcd(
            x1.value, x2.value
        )
        return True



class GreaterNode(Node):
    node_id = "np.greater"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.greater(
            x1.value, x2.value
        )
        return True



class GreaterEqualNode(Node):
    node_id = "np.greater_equal"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.greater_equal(
            x1.value, x2.value
        )
        return True



class HeavisideNode(Node):
    node_id = "np.heaviside"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.heaviside(
            x1.value, x2.value
        )
        return True



class HypotNode(Node):
    node_id = "np.hypot"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.hypot(
            x1.value, x2.value
        )
        return True



class InvertNode(Node):
    node_id = "np.invert"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.invert(
            x1.value
        )
        return True



class IsfiniteNode(Node):
    node_id = "np.isfinite"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.isfinite(
            x1.value
        )
        return True



class IsinfNode(Node):
    node_id = "np.isinf"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.isinf(
            x1.value
        )
        return True



class IsnanNode(Node):
    node_id = "np.isnan"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.isnan(
            x1.value
        )
        return True



class IsnatNode(Node):
    node_id = "np.isnat"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.isnat(
            x1.value
        )
        return True



class LcmNode(Node):
    node_id = "np.lcm"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.lcm(
            x1.value, x2.value
        )
        return True



class LdexpNode(Node):
    node_id = "np.ldexp"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.ldexp(
            x1.value, x2.value
        )
        return True



class LeftShiftNode(Node):
    node_id = "np.left_shift"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.left_shift(
            x1.value, x2.value
        )
        return True



class LessNode(Node):
    node_id = "np.less"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.less(
            x1.value, x2.value
        )
        return True



class LessEqualNode(Node):
    node_id = "np.less_equal"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.less_equal(
            x1.value, x2.value
        )
        return True



class LogNode(Node):
    node_id = "np.log"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.log(
            x1.value
        )
        return True



class Log10Node(Node):
    node_id = "np.log10"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.log10(
            x1.value
        )
        return True



class Log1PNode(Node):
    node_id = "np.log1p"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.log1p(
            x1.value
        )
        return True



class Log2Node(Node):
    node_id = "np.log2"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.log2(
            x1.value
        )
        return True



class LogaddexpNode(Node):
    node_id = "np.logaddexp"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.logaddexp(
            x1.value, x2.value
        )
        return True



class Logaddexp2Node(Node):
    node_id = "np.logaddexp2"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.logaddexp2(
            x1.value, x2.value
        )
        return True



class LogicalAndNode(Node):
    node_id = "np.logical_and"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.logical_and(
            x1.value, x2.value
        )
        return True



class LogicalNotNode(Node):
    node_id = "np.logical_not"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.logical_not(
            x1.value
        )
        return True



class LogicalOrNode(Node):
    node_id = "np.logical_or"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.logical_or(
            x1.value, x2.value
        )
        return True



class LogicalXorNode(Node):
    node_id = "np.logical_xor"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.logical_xor(
            x1.value, x2.value
        )
        return True



class MatmulNode(Node):
    node_id = "np.matmul"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.matmul(
            x1.value, x2.value
        )
        return True



class MaximumNode(Node):
    node_id = "np.maximum"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.maximum(
            x1.value, x2.value
        )
        return True



class MinimumNode(Node):
    node_id = "np.minimum"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.minimum(
            x1.value, x2.value
        )
        return True



class ModNode(Node):
    node_id = "np.mod"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.mod(
            x1.value, x2.value
        )
        return True



class ModfNode(Node):
    node_id = "np.modf"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out1 = NodeOutput(type=NdArrayType)    out2 = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.modf(
            x1.value
        )
        return True



class MultiplyNode(Node):
    node_id = "np.multiply"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.multiply(
            x1.value, x2.value
        )
        return True



class NegativeNode(Node):
    node_id = "np.negative"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.negative(
            x1.value
        )
        return True



class NextafterNode(Node):
    node_id = "np.nextafter"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.nextafter(
            x1.value, x2.value
        )
        return True



class NotEqualNode(Node):
    node_id = "np.not_equal"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.not_equal(
            x1.value, x2.value
        )
        return True



class PositiveNode(Node):
    node_id = "np.positive"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.positive(
            x1.value
        )
        return True



class PowerNode(Node):
    node_id = "np.power"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.power(
            x1.value, x2.value
        )
        return True



class Rad2DegNode(Node):
    node_id = "np.rad2deg"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.rad2deg(
            x1.value
        )
        return True



class RadiansNode(Node):
    node_id = "np.radians"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.radians(
            x1.value
        )
        return True



class ReciprocalNode(Node):
    node_id = "np.reciprocal"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.reciprocal(
            x1.value
        )
        return True



class RemainderNode(Node):
    node_id = "np.remainder"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.remainder(
            x1.value, x2.value
        )
        return True



class RightShiftNode(Node):
    node_id = "np.right_shift"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.right_shift(
            x1.value, x2.value
        )
        return True



class RintNode(Node):
    node_id = "np.rint"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.rint(
            x1.value
        )
        return True



class SignNode(Node):
    node_id = "np.sign"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.sign(
            x1.value
        )
        return True



class SignbitNode(Node):
    node_id = "np.signbit"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.signbit(
            x1.value
        )
        return True



class SinNode(Node):
    node_id = "np.sin"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.sin(
            x1.value
        )
        return True



class SinhNode(Node):
    node_id = "np.sinh"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.sinh(
            x1.value
        )
        return True



class SpacingNode(Node):
    node_id = "np.spacing"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.spacing(
            x1.value
        )
        return True



class SqrtNode(Node):
    node_id = "np.sqrt"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.sqrt(
            x1.value
        )
        return True



class SquareNode(Node):
    node_id = "np.square"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.square(
            x1.value
        )
        return True



class SubtractNode(Node):
    node_id = "np.subtract"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.subtract(
            x1.value, x2.value
        )
        return True



class TanNode(Node):
    node_id = "np.tan"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.tan(
            x1.value
        )
        return True



class TanhNode(Node):
    node_id = "np.tanh"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.tanh(
            x1.value
        )
        return True



class TrueDivideNode(Node):
    node_id = "np.true_divide"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.true_divide(
            x1.value, x2.value
        )
        return True



class TruncNode(Node):
    node_id = "np.trunc"
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = np.trunc(
            x1.value
        )
        return True
