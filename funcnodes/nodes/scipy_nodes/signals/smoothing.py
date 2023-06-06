from funcnodes.nodespace import LibShelf
from funcnodes.nodes.numpy_nodes.types import NdArrayType
from funcnodes.node import Node, NodeInput, NodeOutput
import numpy as np
import pandas as pd
from .signal_tools import interpolate_xy
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d


class MovingAverageSmoothing(Node):
    node_id = "smoothing.movavg"

    x = NodeInput(type=NdArrayType)
    y = NodeInput(type=NdArrayType, required=True)
    window = NodeInput(type=float, default=0)

    x_smoothed = NodeOutput(type=NdArrayType)
    y_smoothed = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        x = self.x.value_or_none
        y = self.y.value
        if len(y) <= 1:
            self.y_smoothed.value = np.array([])
            self.x_smoothed.value = np.array([])
            return True

        if x is not None:
            if len(x) <= 1:
                self.y_smoothed.value = np.array([])
                self.x_smoothed.value = np.array([])
                return True
            x, y = interpolate_xy(x, y)
        else:
            x = np.arange(len(y))

        dx = np.diff(x).min()

        window = self.window.value

        window = int(np.ceil(window / dx))
        if window <= 1:
            self.y_smoothed.value = y
            self.x_smoothed.value = x
            return True

        y_padded = np.pad(y, (window // 2, window // 2), "edge")

        y_smoothed = pd.Series(y_padded).rolling(window, center=True).mean().values
        y_smoothed = y_smoothed[window // 2 : -window // 2]

        self.y_smoothed.value = y_smoothed
        self.x_smoothed.value = x
        return True


class SavitzkyGolaySmoothing(Node):
    node_id = "smoothing.savgol"
    x = NodeInput(type=NdArrayType)
    y = NodeInput(type=NdArrayType, required=True)
    window = NodeInput(type=float, default=0)
    order = NodeInput(type=int, default=3)

    x_smoothed = NodeOutput(type=NdArrayType)
    y_smoothed = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        x = self.x.value_or_none
        y = self.y.value
        if len(y) <= 1:
            self.y_smoothed.value = np.array([])
            self.x_smoothed.value = np.array([])
            return True

        if x is not None:
            if len(x) <= 1:
                self.y_smoothed.value = np.array([])
                self.x_smoothed.value = np.array([])
                return True
            x, y = interpolate_xy(x, y)
        else:
            x = np.arange(len(y))

        dx = np.diff(x).min()

        window = self.window.value

        window = int(np.ceil(window / dx))
        if window <= 1:
            self.y_smoothed.value = y
            self.x_smoothed.value = x
            return True

        order = self.order.value

        y_smoothed = savgol_filter(y, window, order)

        self.y_smoothed.value = y_smoothed
        self.x_smoothed.value = x
        return True


class GaussianSmoothing(Node):
    node_id = "smoothing.gaussian"
    x = NodeInput(type=NdArrayType)
    y = NodeInput(type=NdArrayType, required=True)
    sigma = NodeInput(type=float, default=0)

    x_smoothed = NodeOutput(type=NdArrayType)
    y_smoothed = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        x = self.x.value_or_none
        y = self.y.value
        if len(y) <= 1:
            self.y_smoothed.value = np.array([])
            self.x_smoothed.value = np.array([])
            return True

        if x is not None:
            if len(x) <= 1:
                self.y_smoothed.value = np.array([])
                self.x_smoothed.value = np.array([])
                return True
            x, y = interpolate_xy(x, y)
        else:
            x = np.arange(len(y))

        dx = np.diff(x).min()

        sigma = self.sigma.value
        sigma = sigma / dx
        if sigma <= 0:
            self.y_smoothed.value = y
            self.x_smoothed.value = x
            return True

        y_smoothed = gaussian_filter1d(y, sigma)

        self.y_smoothed.value = y_smoothed
        self.x_smoothed.value = x

        return True
