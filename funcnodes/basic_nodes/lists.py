from typing import List, Union, Any
import funcnodes as fn


@fn.NodeDecorator(
    id="contains_node",
    name="Contains",
)
def contains(collection: List[Union[str, Any]], item: Union[str, Any]) -> bool:
    return item in collection


class GetIndexNode(fn.Node):
    node_id = "list.get"
    node_name = "Get Element"
    description = "Gets an element from a list."
    inputlist = fn.NodeInput(
        name="List",
        type=List[Union[str, Any]],
        uuid="inputlist",
    )

    index = fn.NodeInput(
        name="Index",
        type=int,
        uuid="index",
    )

    element = fn.NodeOutput(
        name="Element",
        type=Any,
        uuid="element",
    )

    def __init__(self):
        super().__init__()
        self.get_input("inputlist").on("after_set_value", self._update_indices)

    def _update_indices(self, **kwargs):
        try:
            lst = self.get_input("inputlist").value
            index = self.get_input("index")
        except KeyError:
            return
        try:
            index.update_value_options(min=0, max=len(lst) - 1)
        except Exception:
            index.update_value_options(min=0, max=0)

    async def func(
        self,
        inputlist: List[Any],
        index: int,
    ) -> Any:
        index = int(index)
        ele = inputlist[index]
        self.get_output("element").value = ele
        return ele


NODE_SHELF = fn.Shelf(
    nodes=[contains, GetIndexNode],
    subshelves=[],
    name="Logic",
    description="Control flow and decision making nodes.",
)
