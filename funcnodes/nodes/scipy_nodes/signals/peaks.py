from funcnodes.nodespace import LibShelf
from funcnodes.nodes.numpy_nodes.types import NdArrayType
from funcnodes.node import Node, NodeInput, NodeOutput
import numpy as np
from scipy.signal import find_peaks_cwt, find_peaks
from .signal_tools import interpolate_xy


class FindPeaksCWT(Node):
    node_id = "scipy.signal.find_peaks_cwt"
    x = NodeInput(type=NdArrayType)
    y = NodeInput(type=NdArrayType, required=True)
    widths = NodeInput(type=NdArrayType, required=True)

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

        peaks = find_peaks_cwt(y, self.widths.value)
        if len(peaks) == 0:
            self.output.value = np.array([])
            return True

        peaks = x[peaks]

        self.output.value = peaks
        return True


class FindPeaks(Node):
    node_id = "scipy.signal.find_peaks"
    x = NodeInput(type=NdArrayType)
    y = NodeInput(type=NdArrayType, required=True)
    min_distance = NodeInput(type=float, default=0)
    min_width = NodeInput(type=float, default=0)

    peak_indices = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        y = self.y.value
        if len(y) <= 1:
            self.peak_indices.value = np.array([])
            return True
        x = self.x.value_or_none

        if x is not None:
            if len(x) <= 1:
                self.peak_indices.value = np.array([])
                return True
            x, y = interpolate_xy(x, y)
        else:
            x = np.arange(len(y))

        dx = np.diff(x).min()

        min_distance = self.min_distance.value
        min_distance = int(dx / min_distance)
        if min_distance <= 0:
            min_distance = 1

        min_width = self.min_width.value
        min_width = int(dx / min_width)
        if min_width <= 0:
            min_width = None

        peaks, _ = find_peaks(y, distance=min_distance, width=min_width)
        return True


LIB = LibShelf(
    name="peaks",
    nodes=[FindPeaksCWT],
    shelves=[],
)
