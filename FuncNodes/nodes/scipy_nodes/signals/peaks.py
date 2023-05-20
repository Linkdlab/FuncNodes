from typing import Literal
from FuncNodes.nodespace import LibShelf
from FuncNodes.nodes.numpy_nodes.types import NdArrayType
from FuncNodes.node import Node, NodeInput, NodeOutput
import numpy as np


def interpolate_xy(xin, yin, diff: Literal["min", "median", "mean", "max"] = "median"):
    # crop both arrays to the same length
    minlen = min(len(xin), len(yin))
    x = xin[:minlen].astype(float)
    y = yin[:minlen].astype(float)

    sorted_indices = np.argsort(x)
    x = x[sorted_indices]
    y = y[sorted_indices]

    x_diffs = np.diff(x)
    mindiff = np.min(x_diffs)
    maxdiff = np.max(x_diffs)
    if mindiff == maxdiff:
        return x, y

    if diff == "min":
        usediff = mindiff
    elif diff == "max":
        usediff = maxdiff
    elif diff == "median":
        usediff = np.median(x_diffs)
    elif diff == "mean":
        usediff = np.mean(x_diffs)
    else:
        raise ValueError(
            f"diff must be one of 'min', 'max', 'median', 'mean', not {diff}"
        )

    x_new = np.linspace(x[0], x[-1] + usediff, int(np.ceil((x[-1] - x[0]) / usediff)))
    y_new = np.interp(x_new, x, y)
    return x_new.astype(xin.dtype), y_new.astype(yin.dtype)


from scipy.signal import find_peaks_cwt


class FindPeaksCWT(Node):
    node_id = "scipy.signal.find_peaks_cwt"
    x = NodeInput(type=NdArrayType)
    y = NodeInput(type=NdArrayType, required=True)
    width = NodeInput(type=float, required=True)

    output = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        y = self.y.value
        if len(y) <= 1:
            self.output.value = np.array([])
            return True
        x = self.x.value_or_none

        if x is not None:
            if len(x) <= 1:
                self.output.value = np.array([])
                return True
            x, y = interpolate_xy(self.x.value, y)
        else:
            x = np.arange(len(y))

        peaks = find_peaks_cwt(y, self.width.value)
        if len(peaks) == 0:
            self.output.value = np.array([])
            return True

        peaks = x[peaks]

        self.output.value = peaks
        return True


LIB = LibShelf(
    name="peaks",
    nodes=[FindPeaksCWT],
    shelves=[],
)
