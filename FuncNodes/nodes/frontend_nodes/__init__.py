from ...nodespace import LibShelf

from .plot import LIB as PLOT_LIB

LIB = LibShelf(
    name="basic",
    nodes=[],
    shelves=[PLOT_LIB],
)

try:
    from .input import LIB as INPUT_LIB

    LIB.shelves.append(INPUT_LIB)
except Exception:
    pass
