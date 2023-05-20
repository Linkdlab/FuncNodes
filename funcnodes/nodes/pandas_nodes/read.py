import pandas as pd
from ...nodespace import LibShelf
from ...node import Node
from ...io import NodeInput, NodeOutput

from .types import DataFrameType


class PDReadCSV(Node):
    node_id = "pd.read_csv"
    input = NodeInput(type=str, required=True)
    output = NodeOutput(type=DataFrameType.typeclass)

    def try_read_csv(self, value) -> pd.DataFrame:
        try:
            return pd.read_csv(value, index_col=None)
        except (FileNotFoundError, OSError):
            from io import StringIO

            # maybe the string is not a path but a datastring
            return self.try_read_csv(StringIO(value))

    async def on_trigger(self):
        self.output.value = self.try_read_csv(self.input.value)
        return True


LIB = LibShelf(
    name="read",
    nodes=[PDReadCSV],
    shelves=[],
)
