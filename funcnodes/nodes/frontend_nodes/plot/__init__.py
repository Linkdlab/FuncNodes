from ....nodespace import LibShelf

from .plotly import Plotly2DNode, Plotly2DMergeNode, Plotly2DVLines

LIB = LibShelf(
    name="plotting",
    nodes=[Plotly2DNode, Plotly2DMergeNode, Plotly2DVLines],
    shelves=[],
)
