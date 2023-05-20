from ...nodespace import LibShelf

from .basic import LIB as BASIC_LIB

LIB = LibShelf(
    name="conversion",
    nodes=[],
    shelves=[BASIC_LIB],
)
