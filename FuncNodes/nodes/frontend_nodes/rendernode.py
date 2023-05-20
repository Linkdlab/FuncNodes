from ...node import Node
from pyscript import Element

class RenderException(Exception):
    pass

class RenderNode(Node):
    node_id = "rendernode"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.element: Element = None

    def render(self, id: str):
        self.element = Element(id)
        if self.element is None:
            self.error(RenderException(f"Element with id {id} not found!"))
        self.element.clear()