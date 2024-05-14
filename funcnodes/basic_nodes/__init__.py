from funcnodes import Shelf
from .logic import NODE_SHELF as logic_shelf
from .math import NODE_SHELF as math_shelf

NODE_SHELF = Shelf(
    nodes=[],
    subshelves=[
        math_shelf,
        logic_shelf,
    ],
    name="basics",
    description="basic functionalities",
)
