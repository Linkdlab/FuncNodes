from ....nodespace import LibShelf


from .pdf import LIB as PDF_LIB

LIB = LibShelf(
    name="dist",
    nodes=[],
    shelves=[PDF_LIB],
)
