from funcnodes import Node, NodeInput, NodeOutput


class DataDisplayNode(Node):
    node_id = "data_display"
    node_name = "Data Display"

    data = NodeInput(id="data", type="Any")
    forward = NodeOutput(id="forward", type="Any")
    display = NodeOutput(id="display", type="Any")

    default_render_options = {
        "data": {
            "src": "data",
        }
    }

    async def func(self, data) -> None:
        self.outputs["forward"].value = data
        self.outputs["display"].value = data


try:
    import pandas as pd

    class TableNode(DataDisplayNode):
        node_id = "table"
        node_name = "Table"

        display = NodeOutput(id="display", type=pd.DataFrame)

        async def func(self, data) -> None:
            self.outputs["display"].value = data

except ModuleNotFoundError:
    pass
