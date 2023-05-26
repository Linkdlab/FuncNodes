import pandas as pd
from ...nodespace import LibShelf
from ...node import Node
from ...io import NodeInput, NodeOutput

from .types import DataFrameType


class PDReadCSV(Node):
    node_id = "pd.read_csv"
    input = NodeInput(type=str, required=True)
    sep = NodeInput(
        type=str,
        required=False,
        default_value=",",
        options=[(",", ","), (";", ";"), ("tab", "\t"), ("space", " "), ("|", "|")],
    )
    output = NodeOutput(type=DataFrameType.typeclass)

    def try_read_csv(self, value, sep) -> pd.DataFrame:
        try:
            return pd.read_csv(value, index_col=None, sep=sep)
        except (FileNotFoundError, OSError):
            from io import StringIO

            # maybe the string is not a path but a datastring
            return self.try_read_csv(StringIO(value), sep=sep)

    async def on_trigger(self):
        sep = self.sep.value
        self.output.value = self.try_read_csv(self.input.value, sep=sep)
        return True


LIB = LibShelf(
    name="read",
    nodes=[PDReadCSV],
    shelves=[],
)
