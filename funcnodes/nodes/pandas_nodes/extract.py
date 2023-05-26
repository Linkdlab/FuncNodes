from funcnodes import Node, NodeInput, NodeOutput
import pandas as pd


class ExtractSeriesNode(Node):
    node_id = "pd.extractSeries"
    data = NodeInput(type=pd.DataFrame, required=True)
    series_name = NodeInput(type=str, required=True, options=[], default_value="")
    output = NodeOutput(type=pd.Series)

    async def on_trigger(self):
        df = self.data.value
        df.columns = [str(c) for c in df.columns]
        if len(df.columns) == 0:
            return False

        self.series_name.options = list(df.columns)
        if self.series_name.value_or_none not in df.columns:
            self.series_name.set_value_and_default = df.columns[0]

        self.output.value = df[self.series_name.value]
        return True
