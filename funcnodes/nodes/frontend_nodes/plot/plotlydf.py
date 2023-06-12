from funcnodes.node import Node
from funcnodes.io import NodeInput, NodeOutput
import numpy as np
import pandas as pd
from .plotly_types import PlotlyDataType, PlotlyListType, PlotlyData
from funcnodes.nodes.pandas_nodes.types import DataFrameType


class PlotlyDF(Node):
    node_id = "plotlydf"
    df = NodeInput(type=pd.DataFrame)
    plot = NodeOutput(type=PlotlyData)

    def _check_inputs(self, df: pd.DataFrame):
        _df_inputs = {}
        for ip in self.get_inputs():
            if ip.id.startswith("df_"):
                _df_inputs[ip.id] = ip

        required_inputs = []
        for col in df.columns:
            required_inputs.append(f"df_{col}_role")

        unnessesary_inputs = []
        for ip in _df_inputs:
            if ip not in required_inputs:
                unnessesary_inputs.append(_df_inputs[ip])

        for ip in unnessesary_inputs:
            self.remove_input(ip)

        for ip in required_inputs:
            if ip not in _df_inputs:
                if ip.endswith("_role"):
                    newip = NodeInput(
                        type=str,
                        options=[[d, d] for d in ["x", "y", "ignore"]],
                        default_value="y",
                        id=ip,
                    )
                else:
                    raise ValueError(f"Unknown input {ip}")
                print(f"Adding input {ip}")
                self.add_input(newip)

    async def on_trigger(self):
        df: pd.DataFrame = self.df.value
        if df is None:
            return False

        self._check_inputs(df)

        current_x = None

        x_axes = {None: []}

        for col in df.columns:
            role = self.get_input(f"df_{col}_role").value
            if role == "ignore":
                continue
            if role == "x":
                x_axes[col] = []
                current_x = col
            if role == "y":
                x_axes[current_x].append(col)

        plds = []
        for x, ys in x_axes.items():
            for y in ys:
                sdf = df[[x, y] if x is not None else [y]].dropna()
                if len(sdf) == 0:
                    continue

                pld = PlotlyDataType(
                    x=sdf[x] if x is not None else None,
                    y=sdf[y],
                    type="scatter",
                    mode="lines",
                    marker=None,
                    name=y,
                )
                plds.append(pld)

        pldl: PlotlyListType = PlotlyListType(plds)
        self.plot.value = pldl

        return True
