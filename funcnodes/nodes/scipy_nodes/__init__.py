from ...nodespace import LibShelf

from .distributions import LIB as DIST_LIB
from .signals import LIB as SIGNAL_LIB

LIB = LibShelf(
    name="scipy",
    nodes=[],
    shelves=[SIGNAL_LIB, DIST_LIB],
)
