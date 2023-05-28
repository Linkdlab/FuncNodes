from funcnodes import Node, NodeInput, NodeOutput
from ...nodespace import LibShelf


class TextSplitNode(Node):
    node_id = "text.split"
    text = NodeInput(type=str, required=True)
    sep = NodeInput(type=str, required=True)
    before = NodeOutput(type=str)
    after = NodeOutput(type=str)

    async def on_trigger(self):
        text = self.text.value
        sep = self.sep.value
        before, after = text.split(sep, 1)
        self.before.value = before
        self.after.value = after
        return True


class StripLinesNode(Node):
    node_id = "text.strip_lines"
    text = NodeInput(type=str, required=True)
    output = NodeOutput(type=str)

    async def on_trigger(self):
        text = self.text.value
        self.output.value = "\n".join([line.strip() for line in text.split("\n")])
        return True


class ToKeyValuePair(Node):
    node_id = "text.kv_pair"
    text = NodeInput(type=str, required=True)
    sep = NodeInput(type=str, required=True)
    output = NodeOutput(type=dict)

    async def on_trigger(self):
        text = self.text.value
        sep = self.sep.value
        sep = bytes(sep, "utf-8").decode("unicode_escape")
        if not sep:
            return False

        out = {}
        for line in text.split("\n"):
            if sep not in line:
                continue
            key, value = line.split(sep, 1)
            out[key.strip()] = value.strip()
        self.output.value = out
        return True


LIB = LibShelf(
    name="text",
    nodes=[
        TextSplitNode,
    ],
    shelves=[],
)
