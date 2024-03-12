from funcnodes import Shelf
from .frontend import NODE_SHELFE as frontend_shelf
from .logic import NODE_SHELFE as logic_shelf
from .math import NODE_SHELFE as math_shelf

NODE_SHELFE = Shelf(
    nodes=[],
    subshelves=[math_shelf, logic_shelf, frontend_shelf],
    name="basics",
    description="basic functionalities",
)
