from ...nodespace import LibShelf
from .inputnodes import LIB as INPUT_LIB
from .textnodes import LIB as TEXT_LIB


LIB = LibShelf(
    name="basic",
    nodes=[],
    shelves=[INPUT_LIB, TEXT_LIB],
)
