from ...nodespace import LibShelf

from .read import LIB as READ_LIB
from .generate import LIB as GENERATE_LIB

LIB = LibShelf(
    name="pandas",
    nodes=[],
    shelves=[READ_LIB, GENERATE_LIB],
)
