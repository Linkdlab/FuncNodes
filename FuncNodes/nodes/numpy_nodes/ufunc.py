import sys
from typing import Dict, Type
import numpy as np
import numpy.typing as npt
from ...node import Node
from ...nodespace import LibShelf
from ..node_creator import func_to_node, FuncNodeFunctionParam, OutputParam
from .types import NdArrayType

self_mod = sys.modules[__name__]


UFUNC_NODES: Dict[str, Type[Node]] = {}

for n in dir(np):
    v = getattr(np, n)
    if isinstance(v, np.ufunc):
        noodename = "".join(x.title() for x in n.split("_")) + "Node"

        nodeclass = func_to_node(
            v,
            node_id="np." + n,
            input_params=[
                FuncNodeFunctionParam(
                    name=f"x{i+1}", annotation=npt.ArrayLike, positional=True
                )
                for i in range(v.nin)
            ],
            output_params=[
                OutputParam(name=f"out{i+1}", annotation=NdArrayType)
                for i in range(v.nout)
            ]
            if v.nout > 1
            else [OutputParam(name="out", annotation=NdArrayType)],
            nodeclass_name=noodename,
        )

        setattr(self_mod, noodename, nodeclass)
        UFUNC_NODES[noodename] = nodeclass


LIB = LibShelf(
    name="ufuncs",
    nodes=list(UFUNC_NODES.values()),
    shelves=[],
)
