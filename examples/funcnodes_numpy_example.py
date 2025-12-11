import funcnodes_numpy as fnnp
import funcnodes as fn
import asyncio


async def main1():
    linspace = fnnp.linspace()

    linspace.inputs["start"].value = 0
    linspace.inputs["stop"].value = 10
    linspace.inputs["num"].value = 100
    await linspace  # wait for the node to finish execution
    print(linspace.outputs["samples"].value)
    print(linspace.outputs["step"].value)


async def main2():
    linspace = fnnp.linspace()

    linspace.inputs["start"].value = 0
    linspace.inputs["stop"].value = 10
    linspace.inputs["num"].value = 100

    sin = fnnp.sin()

    sin.inputs["x"].connect(linspace.outputs["samples"])

    # wait for all nodes to finish execution
    await fn.run_until_complete(sin, linspace)

    print(sin.outputs["y"].value)


if __name__ == "__main__":
    asyncio.run(main1())
    asyncio.run(main2())
