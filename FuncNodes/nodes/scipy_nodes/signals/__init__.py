from ....nodespace import LibShelf


from .peaks import LIB as peak_LIB

LIB = LibShelf(
    name="signals",
    nodes=[],
    shelves=[peak_LIB],
)
