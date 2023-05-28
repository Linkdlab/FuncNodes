from dataclasses import dataclass
from typing import List
import numpy as np
from funcnodes.iotypes import IOType


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


IOType.register_type(PlotlyData.typestring, PlotlyData)
