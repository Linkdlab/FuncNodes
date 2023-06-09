from funcnodes.nodes.numpy_nodes.types import NdArrayType
from funcnodes.node import Node, NodeInput, NodeOutput
import numpy as np
from .signal_tools import interpolate_xy


class NthPointReduction(Node):
    """Reduced data by selecting every nth point"""

    node_id = "datareduction.nth_point"

    x = NodeInput(type=NdArrayType)
    factor = NodeInput(type=int, default=1)

    x_reduced = NodeOutput(type=NdArrayType)
    selected_indices = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        x = self.x.value_or_none
        if x is None:
            self.x_reduced.value = np.array([])
            return True

        factor = self.factor.value
        if factor <= 1:
            self.x_reduced.value = x
            return True

        indices = np.arange(len(x))
        selected_indices = indices[::factor]
        self.x_reduced.value = np.copy(x[::factor])
        self.selected_indices.value = selected_indices


class EvenData(Node):
    node_id = "datareduction.even_data"

    x = NodeInput(type=NdArrayType)
    y = NodeInput(type=NdArrayType)

    xr = NodeOutput(type=NdArrayType)
    yr = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        y = self.y.value
        x = self.x.value

        if len(y) <= 1 or len(x) <= 1:
            self.xr.value = np.array([])
            self.yr.value = np.array([])
            return True

        xr, yr = interpolate_xy(x, y)

        self.xr.value = xr
        self.yr.value = yr
