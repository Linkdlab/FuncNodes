import numpy as np
from ..node_creator import func_to_node, FuncNodeFunctionParam, OutputParam
from ...nodespace import LibShelf
from .types import NdArrayType


ARangeNode = func_to_node(
    np.arange,
    node_id="np.arange",
    input_params=[
        FuncNodeFunctionParam(
            name="start", annotation=float, positional=True, default=0
        ),
        FuncNodeFunctionParam(
            name="stop", annotation=float, positional=True, default=1
        ),
        FuncNodeFunctionParam(
            name="step", annotation=float, positional=True, default=1
        ),
    ],
    output_params=[OutputParam(name="out", annotation=NdArrayType.typeclass)],
)

LinspaceNode = func_to_node(
    np.linspace,
    node_id="np.linspace",
    input_params=[
        FuncNodeFunctionParam(
            name="start", annotation=float, positional=True, default=0
        ),
        FuncNodeFunctionParam(
            name="stop", annotation=float, positional=True, default=1
        ),
        FuncNodeFunctionParam(name="num", annotation=int, positional=True, default=50),
    ],
    output_params=[OutputParam(name="out", annotation=NdArrayType.typeclass)],
)


LIB = LibShelf(
    name="ranges",
    nodes=[ARangeNode, LinspaceNode],
    shelves=[],
)
