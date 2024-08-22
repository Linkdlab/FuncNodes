from funcnodes import Shelf
from .logic import NODE_SHELF as logic_shelf
from .math import NODE_SHELF as math_shelf
from .lists import NODE_SHELF as lists_shelf

NODE_SHELF = Shelf(
    nodes=[],
    subshelves=[
        lists_shelf,
        math_shelf,
        logic_shelf,
    ],
    name="basics",
    description="basic functionalities",
)
