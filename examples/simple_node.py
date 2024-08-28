import funcnodes as fn
import asyncio


class SimpleNode(fn.Node):
    node_id = "simple_node"

    a = fn.NodeInput(id="a", type=float)
    b = fn.NodeInput(id="b", type=float)

    result = fn.NodeOutput(id="result")

    async def func(self, a, b):
        self.outputs["result"].value = a + b


async def main():
    node1 = SimpleNode()
    node1.inputs["a"].value = 10
    node1.inputs["b"].value = 20
    await node1
    print(node1.outputs["result"].value)


if __name__ == "__main__":
    asyncio.run(main())
