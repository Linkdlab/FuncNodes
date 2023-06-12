from __future__ import annotations

from funcnodes.node import Node
from funcnodes.io import NodeInput, NodeOutput
import numpy as np
from .plotly_types import PlotlyDataType, PlotlyListType, PlotlyData


class Plotly2DNode(Node):
    node_id = "plotly2dnode"
    x = NodeInput(type=np.ndarray, required=False)
    y = NodeInput(type=np.ndarray, required=True)
    mode = NodeInput(
        type=str,
        options=[
            ["lines", "lines"],
            ["markers", "markers"],
            ["lines + markers", "lines+markers"],
        ],
        default_value="lines",
    )

    plot = NodeOutput(type=PlotlyData)

    def on_trigger(self):
        x = self.x.value_or_none
        if x is None:
            x = np.arange(len(self.y.value))
        pld = PlotlyDataType(
            x=np.array(x),
            y=np.array(self.y.value),
            type="scatter",
            mode=self.mode.value,
            marker=None,
        )
        pldl: PlotlyListType = PlotlyListType([pld])
        self.plot.value = pldl
        return True


class Plotly2DVLines(Node):
    node_id = "plotly2dvlines"
    x = NodeInput(type=np.ndarray, required=True)
    bottom = NodeInput(type=float, default_value=0)
    top = NodeInput(type=float, default_value=1)
    plot = NodeOutput(type=PlotlyData)

    def on_trigger(self):
        plds = []
        xv: np.ndarray = self.x.value
        for x in xv:
            pld = PlotlyDataType(
                x=np.array([x, x]),
                y=np.array([self.bottom.value, self.top.value]),
                type="scatter",
                mode="lines",
                marker=None,
            )
            plds.append(pld)
        pldl: PlotlyListType = PlotlyListType(plds)
        self.plot.value = pldl
        return True


class Plotly2DMergeNode(Node):
    node_id = "plotly2dmerge"
    plot1 = NodeInput(type=PlotlyData, required=True)
    plot2 = NodeInput(type=PlotlyData, required=True)
    plot = NodeOutput(type=PlotlyData)

    def on_trigger(self):
        pldl: PlotlyListType = PlotlyListType(self.plot1.value + self.plot2.value)
        self.plot.value = pldl
        return True
