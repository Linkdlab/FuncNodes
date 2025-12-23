import funcnodes as fn
from funcnodes_basic.math_nodes import add_node

from pytest_funcnodes import funcnodes_test


@funcnodes_test
async def test_simple_node_creation():
    add_node_ins = add_node()  # basically lambda a, b: a+b

    add_node_ins.inputs["a"].value = 2  # sets the input of a to 1
    assert not add_node_ins.in_trigger
    assert not add_node_ins.ready_to_trigger()

    add_node_ins.inputs["b"].value = 3  # sets the input of a to 1
    assert not add_node_ins.ready_to_trigger()
    assert add_node_ins.in_trigger

    assert add_node_ins.outputs["out"].value == fn.NoValue
    await add_node_ins
    assert add_node_ins.outputs["out"].value == 5


@funcnodes_test
async def test_simple_connection():
    add_node1 = add_node()
    add_node2 = add_node()

    add_node1.outputs["out"].connect(add_node2.inputs["a"])
    add_node1.o["out"].c(add_node2.i["a"])
    add_node1.outputs["out"] > add_node2.inputs["a"]
