Nodes are the most fundamental building blocks of FuncNodes. Each node encapsulates a function with defined inputs and outputs. Nodes execute when all required inputs are available, producing output data for downstream nodes. Nodes can be created with two different methods: [class based](#class-based-nodes) and [decorator based](#decorator-based-nodes). While class based nodes are more flexible and can be used to create complex nodes, decorator based nodes are simpler and faster to create.

[class-based-nodes]: #class-based-nodes
[decorator-based-nodes]: #decorator-based-nodes

## Class Based Nodes {#class-based-nodes}

Class based nodes are created by subclassing the `Node` class from the `funcnodes` package. This method is more flexible and allows for more complex nodes to be created. The `Node` class provides a number of methods and properties that can be overridden to customize the behavior of the node.

The basic layout of a class based node is as follows:

```{ .python .nodebuilder }

import funcnodes as fn

class MyNode(fn.Node):
    node_name = "My Node"
    node_id = "my_node"

    async def func(self):
        """The function to be executed when the node is triggered."""
```

The `node_name` and `node_id` required properties define the name and ID of the node, respectively.
It is important that the 'node_id' is unique across all nodes in the system since it is used for serialization and deserialization of the node. So it is recommended to make it as descriptive as possible, e.g. if the node CalculateOrbit is part of a public package named 'funcnodes_astronomy' and the node the node_id could be 'funcnodes_astronomy.calculate_orbit'. And while this is not enforced it is recommended to use a similar naming scheme for the ids, to prevent id clashes.
The node name is the human readable name of the node and is used in the UI.

The async `func` method is the entry point for the node's execution. This method is called when the node is triggered and should contain the logic for the node's function.In the class based nodes the `func` method is the only method that is required to be implemented. The `func` method has to be an async method since the execution of the node is done asynchronously.

The node above has no inputs or outputs, which makes it relatively useless. inputs and outputs can be added on the class level as well:

```{ .python .nodebuilder }
import funcnodes as fn

class MyNode(fn.Node):
    node_name = "My Node"
    node_id = "my_node"

    input1 = fn.NodeInput(id="input1", type=int)
    input2 = fn.NodeInput(id="input2", type=int)

    output1 = fn.NodeOutput(id="output1", type=int)


    async def func(self, input1, input2):

        result =  input1 + input2
        self.outputs["output1"].value = result
```

In the example above, the node has two inputs, `input1` and `input2`, and one output, `output`. The `func` method now takes two arguments, `input1` and `input2`, which are the values of the inputs.
The `func` method then adds the two inputs together and sets the result as the value of the output.
While the class attributes of the inputs and outputs can be arbitrary named, it is recommended to use
the same name as the id of the input or output (IO), to make the code more readable.
setting the type of the IO is optional, but it is recommended since this will
be used to render the corresponding IO in the UI (defaults to Any).

!!! warning

    The typing of the IO is not enforced, to stay as pythonic as possible. If the value is not of the expected type, the node will still trigger and raise an exception if it occurs.

    This is important to keep the system flexible: e.g. numpy arrays can be passed to inputs that expect a list and it should still work.

    If enforcing is required, it should be done in the `func` method.

During triggering all inputs are passed to the `func` method as keyword arguments, so the order of the inputs does not matter, but the ids should be valid python variable names.
In the class based approach outputs have to be set **explicitly**, by setting the value of the output in the `func` method.
For more details on the `IO` see the [Inputs and Outputs](inputs-outputs.md).

## Decorator Based Nodes {#decorator-based-nodes}

A even simpler way to create nodes is by using the `@fn.NodeDecorator` decorator. This decorator can be used to create nodes from a simple function. The function should take the inputs as arguments and return the outputs as a dictionary.
The decorator will automatically create the node and set the inputs and outputs based on the function signature.

```{ .python .nodebuilder }
import funcnodes as fn

@fn.NodeDecorator(node_id="my_node")
def my_node(input1: int, input2: int) -> float:
    return input1 / input2
```

This will create a node with the id `my_node`, which has two inputs, `input1` and `input2` (of type `int`), and one output, `output1` (of type `float`).

The `@fn.NodeDecorator` decorator has the required argument `node_id`, which is the id of the node, similar to the `node_id` property in the class based nodes.
The inputs are automatically created based on the function signature, as such the function should have only defined positional and keyword arguments and no expanding arguments like `*args` or `**kwargs`.
Similar to the class based nodes, the type of the inputs is optional, but recommended.

The Decorator can also be used to create a Node from an arbitrary external function, by passing the function as an argument to the decorator.
The corresponding inputs and outputs will be created based on the signature of the function and the type hints.

```{ .python .nodebuilder }
from typing import Tuple
import funcnodes as fn

def myfunction(a: int=1, b: int=2) -> int:
    return a + b

MyFuncNode = fn.NodeDecorator(
    node_id="my_node",
)(myfunction)
```

The outputs are defined by the return type of the function, the output type is also interpreted from the return type, if present. The default id if the output is `out` and the default type is `Any`.

How the Node input and Output can be further customized with decorators is described in the [Inputs and Outputs](inputs-outputs.md) section.

### Defining multiple outputs

Will the class based approach allows for multiple outputs simply by defining multiple outputs, the decorator requires a little modification.

To have multiple outputs, the function should return multiple values, which would make the return type a tuple. The decorator will then interpret the tuple as multiple outputs.

```{ .python .nodebuilder }
import funcnodes as fn

@fn.NodeDecorator(node_id="my_node")
def my_node(input1: int, input2: int) -> tuple:
    result1 =  input1 + input2
    result2 =  input1 - input2
    return result1, result2

```

But this will result in a single output `out` of the type tuple. To actually have multiple outputs, the output has to be modified in the decorator.

```{ .python .nodebuilder }
from typing import Tuple
import funcnodes as fn

@fn.NodeDecorator(
    node_id="my_node",
    outputs=[
        {"name": "output1"},
        {"name": "output2"},
    ]
)
def my_node(input1: int, input2: int) -> Tuple[int, int]:
    result1 =  input1 + input2
    result2 =  input1 - input2
    return result1, result2
```

The `outputs` argument of the decorator is a list of dictionaries, where each dictionary represents an output. The dictionary should have the key `name` which is the id of the output. To specify the type, the `type` argument can be used. Alternatively, the type can be specified in the return type of the function as in the example above.

In a similar manner the inputs can be customized with the `inputs` argument.

```{ .python .nodebuilder }
from typing import Tuple
import funcnodes as fn

@fn.NodeDecorator(
    node_id="my_node",
    inputs=[
        {"name": "a"},
        {"name": "b"},
    ],
)
def myfunction(var_name_i_dont_like_a: int=1, var_name_i_dont_like_b: int=2) -> int:
    return var_name_i_dont_like_a + var_name_i_dont_like_b

```

Defining the inputs and outputs in the decorator is especially useful when the function is an external function and the signature cannot be changed.

In the following example, the function `divmod` is an external function and the signature cannot be changed.

```{ .python .nodebuilder }
from typing import Tuple
import funcnodes as fn

MyFuncNode = fn.NodeDecorator(
    node_id="divmod",
)(divmod)

```

As you can see the function has the expected inputs, but it is not typed. As such the inputs are of type `Any`, which allows no manual input and the return type is not defined, meaning the function has no output.

To fix this, the inputs and outputs can be defined in the decorator.

```{ .python .nodebuilder }
from typing import Tuple
import funcnodes as fn

MyFuncNode = fn.NodeDecorator(
    node_id="divmod",
    inputs=[
        {"name": "a"},
        {"name": "b"},
    ],
    outputs=[
        {"name": "quotient", "type": int},
        {"name": "remainder", "type": int},
    ]
)(divmod)

```

While under normal circumstances this works as expected, it is recommended to use the `fn.NodeDecorator`
as a decorator, and create a wrapper function that calls the external function, to make the node more readable and to allow for more customization.

```{ .python .nodebuilder }
from typing import Tuple
import funcnodes as fn

@fn.NodeDecorator(
    node_id="divmod",
    outputs=[
        {"name": "quotient"},
        {"name": "remainder"},
    ]
)
def divmod_node(a: int, b: int) -> Tuple[int, int]:
    return divmod(a, b)
```

### Defining the node name

The node name is especially important for the UI, as it is the human readable name of the node. If not present, the node name will be the name of the function or the class. To set the node name, the `node_name` class attribute or the `name` argument of the decorator can be used.

```{ .python .nodebuilder }
import funcnodes as fn

@fn.NodeDecorator(node_id="my_node1", name="My Node Decorator")
def my_node(input1: int, input2: int) -> float:
    return input1 / input2

class MyNode(fn.Node):
    node_name = "My Node Class"
    node_id = "my_node2"

    async def func(self, input1, input2):
        result =  input1 + input2
        self.outputs["output1"].value = result
```

### Defining the node description

In a similar manner the node description can be set with the `description` argument of the decorator or the `description` class attribute of the class based nodes.

Description is a human readable description of the node, which can be used to provide more information about the node to the user.

Additionaly if no description is provided, the docstring of the function or the class will be used as the description (if present).

```{ .python .nodebuilder }
import funcnodes as fn

@fn.NodeDecorator(node_id="my_node1", description="This is a node created with the decorator")
def my_node(ip:int) -> float:
    return ip/2

@fn.NodeDecorator(node_id="my_node2")
def my_node(ip:int) -> float:
    """This is a node created with the decorator and a docstring"""
    return ip/2

class MyNode(fn.Node):
    node_name = "My Node Class"
    node_id = "my_node3"
    description = description = """
This is a node created with the class

Multi line is supported
    """

    ip = fn.NodeInput(id="ip", type=int)

    async def func(self, ip):
        self.outputs["output1"].value = ip / 2
```

(Hover over the node header in the UI to see the description)

!!! info "Future Plans"

    We plan to render the description as via Markdown/Sphinx in the UI, so it is recommended to use Markdown in the description.

### Node progress bar

Especially for long running nodes, it is recommended to provide a progress bar to the user.
For this purpose the node has a custom property `progress` which wraps the `tqdm` progress bar and automatically streams the progress to the UI.

```{ .python .nodebuilder }
import asyncio
import funcnodes as fn

class MyNode(fn.Node):
    node_name = "My Node Class"
    node_id = "my_node3"
    description = "This is a node created with the class"

    ip = fn.NodeInput(id="ip", type=int)

    async def func(self, ip):
        for i in self.progress(range(ip)):
            await asyncio.sleep(1)

        self.outputs["output1"].value = ip / 2
```

(No live preview - yet? - since the progress bar is only visible during triggering)

To access the progress bar in a decorator based node, we need to access the underlying node object. For this purpose an input argument `node` can be added, which will not be considered as normal input, but as a reference to the node object.

```{ .python .nodebuilder }

import asyncio
import funcnodes as fn

@fn.NodeDecorator(node_id="my_node")
async def my_node(ip:int, node: fn.Node) -> float:
    for i in node.progress(range(ip)):
        await asyncio.sleep(1)

    return ip/2
```

### Heavy Tasks

Since Funcnodes uses the asyncio library, a blocking function will block the event loop and prevent other nodes from executing. To prevent this, heavy tasks should be executed in a separate thread or process. This can be done e.g. by using the `asyncio.to_thread` function, which will run the function in a separate thread and return the result.

```{ .python .nodebuilder }
import asyncio
import time
import funcnodes as fn

@fn.NodeDecorator(node_id="my_node")
async def my_node(input1: int, input2: int) -> int:
    def heavy_task(input1, input2):
        time.sleep(1)
        return input1 + input2

    return await asyncio.to_thread(heavy_task, input1, input2)
```

This works for both class based and decorator based nodes.
Alternatively, the NodeDecorator accepts a `separate_thread=True` argument, which will automatically run the function in a separate thread. (The decorator alternativly accepts a `separate_process=True` argument, which will run the function in a separate process, but this is still experimental and should only considered for heavy CPU bound tasks)

### Nested Inheritance

While the class based approach allows for more complex inheritance patterns:

```{ .python .nodebuilder }
import funcnodes as fn

class BaseNode(fn.Node):
    """
    `Abstract` base class does not need a `func` method or a `node_id`
    """

    my_id = fn.NodeOutput(id="my_id", type=int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outputs["my_id"].value = id(self)


class MyNode(BaseNode):
    node_name = "My Node"
    node_id = "my_node"

    input1 = fn.NodeInput(id="input1", type=int)
    input2 = fn.NodeInput(id="input2", type=int)

    output1 = fn.NodeOutput(id="output1", type=int)

    async def func(self, input1, input2):
        result =  input1 + input2
        self.outputs["output1"].value = result

class MyNodeTwo(BaseNode):
    node_name = "My Node Two"
    node_id = "my_node_two"

    input1 = fn.NodeInput(id="input1", type=int)
    output1 = fn.NodeOutput(id="output1", type=float)

    async def func(self, input1):
        self.outputs["output1"].value = input1/2

```

The decorator also allows to use different baseclasses than the default `Node` class, by using the `superclass` argument of the decorator.

```{ .python .nodebuilder }
import funcnodes as fn

class BaseNode(fn.Node):
    """
    `Abstract` base class does not need a `func` method or a `node_id`
    """

    my_id = fn.NodeOutput(id="my_id", type=int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outputs["my_id"].value = id(self)


@fn.NodeDecorator(node_id="my_node", superclass=BaseNode)
def my_node(input1: int, input2: int) -> int:
    return input1 + input2

instance = my_node()
instance.outputs["my_id"].value == id(instance) # True

```

### Try it out yourself

<div>
<div id="node-code-demo" style="width:100%;aspect-ratio : 2 / 1;" ></div>
    <script>
        document.addEventListener("DOMContentLoaded", function () {
  NodeBuilder(document.getElementById("node-code-demo"), {
    python_code: `
# Edit me
import funcnodes as fn
@fn.NodeDecorator(node_id="my_node")
def my_node(input1: int, input2: int) -> int:
    return input1 + input2
`,
    show_python_editor: true,
    nodeview:{
        width:"100%",
        height:"100%",
    },
    editorview:{
        width:"100%",
    }
  });
});

    </script>

</div>
