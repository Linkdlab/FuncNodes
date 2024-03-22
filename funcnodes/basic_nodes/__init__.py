from funcnodes import Shelf
from .frontend import NODE_SHELF as frontend_shelf
from .logic import NODE_SHELF as logic_shelf
from .math import NODE_SHELF as math_shelf

NODE_SHELF = Shelf(
    nodes=[],
    subshelves=[math_shelf, logic_shelf, frontend_shelf],
    name="basics",
    description="basic functionalities",
)
