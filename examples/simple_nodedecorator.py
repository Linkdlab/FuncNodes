import funcnodes as fn
import asyncio


@fn.NodeDecorator(
    node_id="simple_node",
)
def simplefunction(a: float, b: float) -> float:
    return a + b


async def main():
    node1 = simplefunction()
    node1.inputs["a"].value = 10
    node1.inputs["b"].value = 20
    await node1
    print(node1.outputs["out"].value)


if __name__ == "__main__":
    asyncio.run(main())
