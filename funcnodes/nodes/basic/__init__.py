from ...nodespace import LibShelf
from ...node import Node
from ...io import NodeInput, NodeOutput
from .inputnodes import LIB as INPUT_LIB


LIB = LibShelf(
    name="basic",
    nodes=[],
    shelves=[INPUT_LIB],
)
