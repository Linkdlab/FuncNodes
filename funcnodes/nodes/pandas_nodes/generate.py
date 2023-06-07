import pandas as pd

from funcnodes import Node, NodeInput, NodeOutput
from funcnodes.nodes.special_bases import VariableInputNode
from ...nodespace import LibShelf
from .types import SeriesType, NdArrayType


class ListToSeriesNode(Node):
    node_id = "pd.toSeries"
    data = NodeInput(type=list, required=True)
    series_name = NodeInput(type=str, required=True)
    output = NodeOutput(type=SeriesType)

    async def on_trigger(self):
        self.output.value = pd.Series(self.data.value, name=self.series_name.value)
        return True


class BuildDataFrameNode(VariableInputNode):
    node_id = "pd.buildDataFrame"
    output = NodeOutput(type=pd.DataFrame)

    input_types = [str, NdArrayType]
    input_names = ["col", "data"]

    async def on_trigger(self):
        inputs = self.get_input_pairs()

        series_list = [pd.Series(ipp[1].value, name=ipp[0].value) for ipp in inputs]

        # Creating the DataFrame
        self.output.value = pd.concat(series_list, axis=1)


LIB = LibShelf(
    name="generate",
    nodes=[ListToSeriesNode,BuildDataFrameNode],
    shelves=[],
)
