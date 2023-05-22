from __future__ import annotations
from dataclasses import dataclass
from typing import List
from funcnodes.iotypes import IOType
from funcnodes.node import Node
from funcnodes.io import NodeInput, NodeOutput
import numpy as np


@dataclass
class PlotlyDataType:
    x: np.ndarray
    y: np.ndarray
    type: str
    mode: str
    marker: dict | None

    def _repr_json_(self):
        d = {
            "x": self.x.tolist(),
            "y": self.y.tolist(),
            "type": self.type,
            "mode": self.mode,
        }
        if self.marker is not None:
            d["marker"] = self.marker
        return d


class PlotlyListType(List[PlotlyDataType]):
    def _repr_json_(self):
        return [x._repr_json_() for x in self]


class PlotlyData(IOType):
    typeclass = (PlotlyListType,)
    typestring = "plotlydata"


class PlotlyNode(Node):
    node_id = "plotlynode"
    pass


class Plotly2DNode(PlotlyNode):
    node_id = "plotly2dnode"
    x = NodeInput(type=np.ndarray, required=False)
    y = NodeInput(type=np.ndarray, required=True)
    plot = NodeOutput(type=PlotlyListType)

    def on_trigger(self):
        x = self.x.value_or_none
        if x is None:
            x = np.arange(len(self.y.value))
        pld = PlotlyDataType(
            x=np.array(x),
            y=np.array(self.y.value),
            type="scatter",
            mode="lines",
            marker=None,
        )
        pldl: PlotlyListType = PlotlyListType([pld])
        self.plot.value = pldl
        return True


class Plotly2DVLines(PlotlyNode):
    node_id = "plotly2dvlines"
    x = NodeInput(type=np.ndarray, required=True)
    bottom = NodeInput(type=float, default_value=0)
    top = NodeInput(type=float, default_value=1)
    plot = NodeOutput(type=PlotlyListType)

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


class Plotly2DMergeNode(PlotlyNode):
    node_id = "plotly2dmerge"
    plot1 = NodeInput(type=PlotlyListType, required=True)
    plot2 = NodeInput(type=PlotlyListType, required=True)
    plot = NodeOutput(type=PlotlyListType)

    def on_trigger(self):
        pldl: PlotlyListType = PlotlyListType(self.plot1.value + self.plot2.value)
        self.plot.value = pldl
        return True
