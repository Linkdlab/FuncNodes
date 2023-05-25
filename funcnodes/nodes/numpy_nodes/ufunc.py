"""implementaation of numpy ufuncs as Nodes"""
from __future__ import annotations
from typing import Dict, Type
import numpy as np
import numpy.typing as npt
from funcnodes import NodeInput, NodeOutput
from funcnodes.node_creator import FunctionBasedNode
from funcnodes.nodespace import LibShelf
from .types import NdArrayType

UFUNC_NODES: Dict[str, Type[FunctionBasedNode]] = {}


class AbsNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.abs"""

    node_id = "np.abs"
    func = np.abs
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["AbsNode"] = AbsNode


class AbsoluteNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.absolute"""

    node_id = "np.absolute"
    func = np.absolute
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["AbsoluteNode"] = AbsoluteNode


class AddNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.add"""

    node_id = "np.add"
    func = np.add
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["AddNode"] = AddNode


class ArccosNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.arccos"""

    node_id = "np.arccos"
    func = np.arccos
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["ArccosNode"] = ArccosNode


class ArccoshNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.arccosh"""

    node_id = "np.arccosh"
    func = np.arccosh
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["ArccoshNode"] = ArccoshNode


class ArcsinNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.arcsin"""

    node_id = "np.arcsin"
    func = np.arcsin
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["ArcsinNode"] = ArcsinNode


class ArcsinhNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.arcsinh"""

    node_id = "np.arcsinh"
    func = np.arcsinh
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["ArcsinhNode"] = ArcsinhNode


class ArctanNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.arctan"""

    node_id = "np.arctan"
    func = np.arctan
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["ArctanNode"] = ArctanNode


class Arctan2Node(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.arctan2"""

    node_id = "np.arctan2"
    func = np.arctan2
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["Arctan2Node"] = Arctan2Node


class ArctanhNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.arctanh"""

    node_id = "np.arctanh"
    func = np.arctanh
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["ArctanhNode"] = ArctanhNode


class BitwiseAndNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.bitwise_and"""

    node_id = "np.bitwise_and"
    func = np.bitwise_and
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["BitwiseAndNode"] = BitwiseAndNode


class BitwiseNotNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.bitwise_not"""

    node_id = "np.bitwise_not"
    func = np.bitwise_not
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["BitwiseNotNode"] = BitwiseNotNode


class BitwiseOrNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.bitwise_or"""

    node_id = "np.bitwise_or"
    func = np.bitwise_or
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["BitwiseOrNode"] = BitwiseOrNode


class BitwiseXorNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.bitwise_xor"""

    node_id = "np.bitwise_xor"
    func = np.bitwise_xor
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["BitwiseXorNode"] = BitwiseXorNode


class CbrtNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.cbrt"""

    node_id = "np.cbrt"
    func = np.cbrt
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["CbrtNode"] = CbrtNode


class CeilNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.ceil"""

    node_id = "np.ceil"
    func = np.ceil
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["CeilNode"] = CeilNode


class ConjNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.conj"""

    node_id = "np.conj"
    func = np.conj
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["ConjNode"] = ConjNode


class ConjugateNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.conjugate"""

    node_id = "np.conjugate"
    func = np.conjugate
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["ConjugateNode"] = ConjugateNode


class CopysignNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.copysign"""

    node_id = "np.copysign"
    func = np.copysign
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["CopysignNode"] = CopysignNode


class CosNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.cos"""

    node_id = "np.cos"
    func = np.cos
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["CosNode"] = CosNode


class CoshNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.cosh"""

    node_id = "np.cosh"
    func = np.cosh
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["CoshNode"] = CoshNode


class Deg2RadNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.deg2rad"""

    node_id = "np.deg2rad"
    func = np.deg2rad
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["Deg2RadNode"] = Deg2RadNode


class DegreesNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.degrees"""

    node_id = "np.degrees"
    func = np.degrees
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["DegreesNode"] = DegreesNode


class DivideNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.divide"""

    node_id = "np.divide"
    func = np.divide
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["DivideNode"] = DivideNode


class DivmodNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.divmod"""

    node_id = "np.divmod"
    func = np.divmod
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out1 = NodeOutput(type=NdArrayType)
    out2 = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out1.value, self.out2.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["DivmodNode"] = DivmodNode


class EqualNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.equal"""

    node_id = "np.equal"
    func = np.equal
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["EqualNode"] = EqualNode


class ExpNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.exp"""

    node_id = "np.exp"
    func = np.exp
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["ExpNode"] = ExpNode


class Exp2Node(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.exp2"""

    node_id = "np.exp2"
    func = np.exp2
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["Exp2Node"] = Exp2Node


class Expm1Node(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.expm1"""

    node_id = "np.expm1"
    func = np.expm1
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["Expm1Node"] = Expm1Node


class FabsNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.fabs"""

    node_id = "np.fabs"
    func = np.fabs
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["FabsNode"] = FabsNode


class FloatPowerNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.float_power"""

    node_id = "np.float_power"
    func = np.float_power
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["FloatPowerNode"] = FloatPowerNode


class FloorNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.floor"""

    node_id = "np.floor"
    func = np.floor
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["FloorNode"] = FloorNode


class FloorDivideNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.floor_divide"""

    node_id = "np.floor_divide"
    func = np.floor_divide
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["FloorDivideNode"] = FloorDivideNode


class FmaxNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.fmax"""

    node_id = "np.fmax"
    func = np.fmax
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["FmaxNode"] = FmaxNode


class FminNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.fmin"""

    node_id = "np.fmin"
    func = np.fmin
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["FminNode"] = FminNode


class FmodNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.fmod"""

    node_id = "np.fmod"
    func = np.fmod
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["FmodNode"] = FmodNode


class FrexpNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.frexp"""

    node_id = "np.frexp"
    func = np.frexp
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out1 = NodeOutput(type=NdArrayType)
    out2 = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out1.value, self.out2.value = self(self.x1.value)
        return True


UFUNC_NODES["FrexpNode"] = FrexpNode


class GcdNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.gcd"""

    node_id = "np.gcd"
    func = np.gcd
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["GcdNode"] = GcdNode


class GreaterNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.greater"""

    node_id = "np.greater"
    func = np.greater
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["GreaterNode"] = GreaterNode


class GreaterEqualNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.greater_equal"""

    node_id = "np.greater_equal"
    func = np.greater_equal
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["GreaterEqualNode"] = GreaterEqualNode


class HeavisideNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.heaviside"""

    node_id = "np.heaviside"
    func = np.heaviside
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["HeavisideNode"] = HeavisideNode


class HypotNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.hypot"""

    node_id = "np.hypot"
    func = np.hypot
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["HypotNode"] = HypotNode


class InvertNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.invert"""

    node_id = "np.invert"
    func = np.invert
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["InvertNode"] = InvertNode


class IsfiniteNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.isfinite"""

    node_id = "np.isfinite"
    func = np.isfinite
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["IsfiniteNode"] = IsfiniteNode


class IsinfNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.isinf"""

    node_id = "np.isinf"
    func = np.isinf
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["IsinfNode"] = IsinfNode


class IsnanNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.isnan"""

    node_id = "np.isnan"
    func = np.isnan
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["IsnanNode"] = IsnanNode


class IsnatNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.isnat"""

    node_id = "np.isnat"
    func = np.isnat
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["IsnatNode"] = IsnatNode


class LcmNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.lcm"""

    node_id = "np.lcm"
    func = np.lcm
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["LcmNode"] = LcmNode


class LdexpNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.ldexp"""

    node_id = "np.ldexp"
    func = np.ldexp
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["LdexpNode"] = LdexpNode


class LeftShiftNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.left_shift"""

    node_id = "np.left_shift"
    func = np.left_shift
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["LeftShiftNode"] = LeftShiftNode


class LessNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.less"""

    node_id = "np.less"
    func = np.less
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["LessNode"] = LessNode


class LessEqualNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.less_equal"""

    node_id = "np.less_equal"
    func = np.less_equal
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["LessEqualNode"] = LessEqualNode


class LogNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.log"""

    node_id = "np.log"
    func = np.log
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["LogNode"] = LogNode


class Log10Node(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.log10"""

    node_id = "np.log10"
    func = np.log10
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["Log10Node"] = Log10Node


class Log1PNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.log1p"""

    node_id = "np.log1p"
    func = np.log1p
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["Log1PNode"] = Log1PNode


class Log2Node(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.log2"""

    node_id = "np.log2"
    func = np.log2
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["Log2Node"] = Log2Node


class LogaddexpNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.logaddexp"""

    node_id = "np.logaddexp"
    func = np.logaddexp
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["LogaddexpNode"] = LogaddexpNode


class Logaddexp2Node(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.logaddexp2"""

    node_id = "np.logaddexp2"
    func = np.logaddexp2
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["Logaddexp2Node"] = Logaddexp2Node


class LogicalAndNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.logical_and"""

    node_id = "np.logical_and"
    func = np.logical_and
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["LogicalAndNode"] = LogicalAndNode


class LogicalNotNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.logical_not"""

    node_id = "np.logical_not"
    func = np.logical_not
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["LogicalNotNode"] = LogicalNotNode


class LogicalOrNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.logical_or"""

    node_id = "np.logical_or"
    func = np.logical_or
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["LogicalOrNode"] = LogicalOrNode


class LogicalXorNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.logical_xor"""

    node_id = "np.logical_xor"
    func = np.logical_xor
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["LogicalXorNode"] = LogicalXorNode


class MatmulNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.matmul"""

    node_id = "np.matmul"
    func = np.matmul
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["MatmulNode"] = MatmulNode


class MaximumNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.maximum"""

    node_id = "np.maximum"
    func = np.maximum
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["MaximumNode"] = MaximumNode


class MinimumNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.minimum"""

    node_id = "np.minimum"
    func = np.minimum
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["MinimumNode"] = MinimumNode


class ModNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.mod"""

    node_id = "np.mod"
    func = np.mod
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["ModNode"] = ModNode


class ModfNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.modf"""

    node_id = "np.modf"
    func = np.modf
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out1 = NodeOutput(type=NdArrayType)
    out2 = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out1.value, self.out2.value = self(self.x1.value)
        return True


UFUNC_NODES["ModfNode"] = ModfNode


class MultiplyNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.multiply"""

    node_id = "np.multiply"
    func = np.multiply
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["MultiplyNode"] = MultiplyNode


class NegativeNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.negative"""

    node_id = "np.negative"
    func = np.negative
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["NegativeNode"] = NegativeNode


class NextafterNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.nextafter"""

    node_id = "np.nextafter"
    func = np.nextafter
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["NextafterNode"] = NextafterNode


class NotEqualNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.not_equal"""

    node_id = "np.not_equal"
    func = np.not_equal
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["NotEqualNode"] = NotEqualNode


class PositiveNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.positive"""

    node_id = "np.positive"
    func = np.positive
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["PositiveNode"] = PositiveNode


class PowerNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.power"""

    node_id = "np.power"
    func = np.power
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["PowerNode"] = PowerNode


class Rad2DegNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.rad2deg"""

    node_id = "np.rad2deg"
    func = np.rad2deg
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["Rad2DegNode"] = Rad2DegNode


class RadiansNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.radians"""

    node_id = "np.radians"
    func = np.radians
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["RadiansNode"] = RadiansNode


class ReciprocalNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.reciprocal"""

    node_id = "np.reciprocal"
    func = np.reciprocal
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["ReciprocalNode"] = ReciprocalNode


class RemainderNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.remainder"""

    node_id = "np.remainder"
    func = np.remainder
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["RemainderNode"] = RemainderNode


class RightShiftNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.right_shift"""

    node_id = "np.right_shift"
    func = np.right_shift
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["RightShiftNode"] = RightShiftNode


class RintNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.rint"""

    node_id = "np.rint"
    func = np.rint
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["RintNode"] = RintNode


class SignNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.sign"""

    node_id = "np.sign"
    func = np.sign
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["SignNode"] = SignNode


class SignbitNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.signbit"""

    node_id = "np.signbit"
    func = np.signbit
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["SignbitNode"] = SignbitNode


class SinNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.sin"""

    node_id = "np.sin"
    func = np.sin
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["SinNode"] = SinNode


class SinhNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.sinh"""

    node_id = "np.sinh"
    func = np.sinh
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["SinhNode"] = SinhNode


class SpacingNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.spacing"""

    node_id = "np.spacing"
    func = np.spacing
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["SpacingNode"] = SpacingNode


class SqrtNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.sqrt"""

    node_id = "np.sqrt"
    func = np.sqrt
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["SqrtNode"] = SqrtNode


class SquareNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.square"""

    node_id = "np.square"
    func = np.square
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["SquareNode"] = SquareNode


class SubtractNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.subtract"""

    node_id = "np.subtract"
    func = np.subtract
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["SubtractNode"] = SubtractNode


class TanNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.tan"""

    node_id = "np.tan"
    func = np.tan
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["TanNode"] = TanNode


class TanhNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.tanh"""

    node_id = "np.tanh"
    func = np.tanh
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["TanhNode"] = TanhNode


class TrueDivideNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.true_divide"""

    node_id = "np.true_divide"
    func = np.true_divide
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    x2 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value, self.x2.value)
        return True


UFUNC_NODES["TrueDivideNode"] = TrueDivideNode


class TruncNode(FunctionBasedNode):
    """FuncNode for the numpy ufunc np.trunc"""

    node_id = "np.trunc"
    func = np.trunc
    x1 = NodeInput(type=npt.ArrayLike, positional=True)
    out = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        self.out.value = self(self.x1.value)
        return True


UFUNC_NODES["TruncNode"] = TruncNode


LIB = LibShelf(
    name="ufuncs",
    nodes=list(UFUNC_NODES.values()),
    shelves=[],
)
