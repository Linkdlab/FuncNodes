import pandas as pd

from ...nodespace import LibShelf
from ...node import Node
from ...io import NodeInput, NodeOutput

from .types import SeriesType


class ListToSeriesNode(Node):
    node_id = "pd.toSeries"
    data = NodeInput(type=list, required=True)
    series_name = NodeInput(type=str, required=True)
    output = NodeOutput(type=SeriesType)

    async def on_trigger(self):
        self.output.value = pd.Series(self.data.value, name=self.series_name.value)
        return True


LIB = LibShelf(
    name="generate",
    nodes=[ListToSeriesNode],
    shelves=[],
)
