from funcnodes import Node, NodeInput, NodeOutput
import pandas as pd


class ExtractSeriesNode(Node):
    node_id = "pd.extractSeries"
    data = NodeInput(type=pd.DataFrame, required=True)
    series_name = NodeInput(type=str, required=False, options=[])
    output = NodeOutput(type=pd.Series)

    async def on_trigger(self):
        df = self.data.value
        cols = [str(c) for c in df.columns]
        df.columns = cols
        if len(cols) == 0:
            return False

        self.series_name.options = list(zip(cols, cols))
        ser = self.series_name.value_or_none
        if ser is None or ser not in cols:
            self.series_name.set_value_and_default(cols[0])

        self.output.value = df[self.series_name.value]
        return True
