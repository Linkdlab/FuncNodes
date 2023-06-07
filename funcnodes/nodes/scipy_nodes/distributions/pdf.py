import inspect
from scipy import stats
from typing import List
import numpy as np

from funcnodes.node_creator import (
    func_to_node,
    FuncNodeFunctionParam,
)
from funcnodes.nodespace import LibShelf

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
        except Exception:
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


LIB = LibShelf(
    name="pdf",
    nodes=PDF_NODES,
    shelves=[],
)
