from ...nodespace import LibShelf

from .ufunc import LIB as UFUNC_LIB
from .nprandom import LIB as RANDOM_LIB
from .ranges import LIB as RANGES_LIB

LIB = LibShelf(
    name="numpy",
    nodes=[],
    shelves=[UFUNC_LIB, RANDOM_LIB, RANGES_LIB],
)
