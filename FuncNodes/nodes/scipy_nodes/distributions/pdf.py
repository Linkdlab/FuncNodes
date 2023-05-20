import inspect
from scipy import stats
from typing import Any, Callable, List, Type
import numpy as np


if __name__ == "__main__":
    import sys
    import os

    cw = os.path.abspath(os.path.dirname(__file__))
    while "FuncNodes" not in os.listdir(cw):
        cw = os.path.abspath(os.path.join(cw, ".."))
    sys.path.append(cw)
from FuncNodes.nodes.node_creator import (
    func_to_node,
    FuncNodeFunctionParam,
    OutputParam,
)
from FuncNodes.nodespace import LibShelf
from FuncNodes.nodes.numpy_nodes.types import NdArrayType

PDF_NODES = []
for n in dir(stats):
    v = getattr(stats, n)
    x_test = np.linspace(0, 100, 200)
    if hasattr(v, "_pdf"):
        pdf = v._pdf

        sig = inspect.signature(pdf)
        params: List[FuncNodeFunctionParam] = []
        for i, p in sig.parameters.items():
            param_dict: FuncNodeFunctionParam = {
                "name": i,
                "annotation": p.annotation
                if p.annotation is not inspect.Parameter.empty
                else np.ndarray,
                "positional": p.kind == p.POSITIONAL_OR_KEYWORD,
            }
            if p.default is not inspect.Parameter.empty:
                param_dict["default"] = p.default

            params.append(param_dict)

        params.append(
            {
                "name": "loc",
                "default": 0,
                "annotation": float,
                "positional": False,
            }
        )
        params.append(
            {
                "name": "scale",
                "default": 1,
                "annotation": float,
                "positional": False,
            }
        )

        call_dict = {}
        for p in params:
            if p["name"] == "x":
                call_dict[p["name"]] = x_test
            else:
                if "default" in p:
                    call_dict[p["name"]] = p["default"]
                else:
                    call_dict[p["name"]] = 0.9

        try:
            v.pdf(**call_dict)
        except Exception as e:
            continue
        noodename = "".join(x.title() for x in n.split("_")) + "Node"

        nodeclass = func_to_node(
            v.pdf,
            node_id="scipy.stat.pdf." + n,
            nodeclass_name=noodename,
            input_params=params,
        )

        node = nodeclass()
        node(**call_dict)
        ser = node.full_serialize()

        PDF_NODES.append(nodeclass)
        print(n)


LIB = LibShelf(
    name="pdf",
    nodes=PDF_NODES,
    shelves=[],
)
