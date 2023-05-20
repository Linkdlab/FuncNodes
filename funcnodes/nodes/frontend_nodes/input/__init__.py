from ....nodespace import LibShelf

from .files import FileInputNode

LIB = LibShelf(
    name="input",
    nodes=[FileInputNode],
    shelves=[],
)
