# Funcnodes

<div align="center">
<img src="assets/logos/funcnodes.png" width="200">
</div>

## Project Overview

Funcnodes is a flexible and modular framework designed for building and managing computational graphs, particularly suited for tasks involving data processing, machine learning, and scientific computations but also capable of hardware controll and arbitarty other functions. The core of Funcnodes revolves around "nodes," which are individual units of computation that can be connected to form complex workflows. Each node performs specific operations, and users can dynamically create and manage these nodes through a web interface or programmatically via an API. The project includes a variety of built-in nodes for common operations and supports custom nodes for specialized tasks.

## Table of Contents

1. [Installation Instructions](#installation-instructions)
2. [Usage Guide](#usage-guide)
3. [Configuration](#configuration)
4. [Testing](#testing)
5. [Architecture](#architecture)
6. [Contributing Guidelines](#contributing-guidelines)
7. [Licensing Information](#licensing-information)
8. [Credits and Acknowledgements](#credits-and-acknowledgements)
9. [Additional Sections](#additional-sections)

## Installation Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Steps

1. **Install the package:**

   ```bash
   pip install funcnodes
   ```

2. **Configure environment variables (optional):**
   Create a `.env` file in the root directory and specify configuration options as needed (see [Configuration](#configuration)).

## Underlying logic

Funcnodes basically wraps arbitary functions in Nodes. The inputs of a Node(usually) mirrors the function arguments and the output(s) is the return of the function. Whenever an input recieves data the respective nodes is triggered, meaning its function is tried to be called.
This happens if:

- the node is not currently running, in which case a new trigger process is qeued.
- if all necessary inputs are set, inputs can can have default values, in which case they act like kwargs and are optional.

This also means under "default" conditions, if a Node with two inputs recieves values on both inputs "simultanously" (which can never really happen, but it can be close), the Node will (try) to run twice. Once it the first input value is set and a second time when the seconds value is set.
Imagin this funcions as a Node

```python
def add(a,b=1):
    return a + b
```

setting a (as 2) and directly b (as 3) would result in

```python
add(2)
add(2,3)
```

The function or the respective Node is called two times. While this can be prevented and is intendet by design it is also important to keep in mind.

If a Nodes finishes triggering, it updates its outputs with newly generated values. if the outputs are connected to other inputs these inputs are then updated as well and the respective Notes are due to be triggered.

The behaviour of the individual inputs and outputs can be manipulated on a Nodeclass level and on a Node instance level (see the respective section).

## Usage Guide

### Use funcnodes programmatically

While not the intendet usage it is important (or at least usefull) to understand how funcnodes workes on a programatically level. Esprecially for testing the implmenetation of new nodes can be tested on a programatically level.
Since funcnodes makes usage of async functions all node specific

#### Nodes

Node instances can be created from the respective class (see [Generating New Nodes in Funcnodes](#generating-new-nodes-in-funcnodes)).

```python
from funcnodes.basic_nodes.math import add_node

async def main():
    add_node = Adadd_nodedNode() # generate Node instance that does a, b: a+b

    add_node.inputs["a"].value = 1 # sets the input of a to 1

    # since add_node requires both inputs to be set, nothing happens
    # node is not ready to trigger:
    print("ready2trigger",add_node_ins.ready_to_trigger())
    # an is also not currently in trigger:
    print("in_trigger",add_node_ins.in_trigger)

    add_node_ins.inputs["b"].value = 3

    # node is not ready to trigger:
    print("ready2trigger",add_node_ins.ready_to_trigger())
    # since it is currently in trigger:
    print("in_trigger",add_node_ins.in_trigger)

    # since it is still triggering the output is not set:
    print("out", add_node_ins.outputs["out"].value)

    # wait fot the actuall trigger process
    await add_node_ins

    # now the output is as expected
    print("out", 5)

... # call asyinc main function.

>>> ready2trigger, False
>>> in_trigger, False
>>> ready2trigger, False
>>> in_trigger, True
>>> out <NoValue>
>>> out 5
```

#### Connections (Edges)

Connections can be created via inputs and outputs (direction invariant):

```python
add_node1 = add_node()
add_node2 = add_node()

add_node1.outputs["out"].connect(add_node2.inputs["a"])

# or short via:
add_node1.o["out"].c(add_node2.i["a"])

# or shorter:
add_node1.o["out"] > add_node2.i["a"]
```

by default inputs can have only 1 connection. If a connection already exists between an output and an input, nothing happens.
if input is already occupied, an error will be raised by default, or the existing connection will be removed if connect is called with the replace=True argument.

### Web Interface

Funcnodes was initially developed for internal use, but we decided to make it publicly available.
While this package mainly serves as the backend logic it also comes with a initial browser based user interface, which allowes the vizual interaction with the system.

1. **Starting the server:**

   ```bash
   funcnodes runserver
   ```

2. **Accessing the web interface:**
   Open `http://127.0.0.1:8000` in a web browser to access the web interface where you can visually manage and connect nodes.

When calling the runserver comand, a simple server is run up, which provides the basic web interface.

#### WorkerManager

The interaction beween the interface and the backend happens via websockers. The first instance that accepts websokcet connections is the WorkerManager, which runs in a seperate window or in the background (depending on our system). It is automatically started when the server starts and it is not already running.
It can be seperatly run via:

```bash
funcnodes startworkermanager
```

The workermanager starts, stops and creates worker (the instances that are running the Node functionalities)

#### Worker

Each Worker runs in a seperate process in the python environment it was created in.
New worker can be created via the web interface or via:

```bash
funcnodes worker new --name=<otional non unique name> --uuid=<otional unique id>
```

Where the uuid is created automatically if not provided and the name falls back to the uuid if not provided.

To run a worker process, simpy activate it via the webinterface or in the cli via:

```bash
funcnodes worker start --name=<otional non unique name> --uuid=<otional unique id>
```

either name or uuid have to be provided. If uuid is provided it will start the respective worker. Otherwise it will start the first worker with the matching name.

### Using the web interface

One important feature is that each

## Generating New Nodes in Funcnodes

In Funcnodes, nodes are the fundamental units of computation that you can configure and connect to form complex data processing workflows. You can create custom nodes by either defining new classes or using decorators. This guide will walk you through both methods, helping you extend the functionality of Funcnodes with custom operations.

### Method 1: Defining Node Classes

To create a new node, you can subclass the `Node` class from Funcnodes and define the computation that the node should perform. Here's a step-by-step guide:

1. **Import the Base Class:**
   Import the `Node` class along with the `NodeInput` and `NodeOutput` classes which are used to define the inputs and outputs of your node.

   ```python
   from funcnodes import Node, NodeInput, NodeOutput
   ```

2. **Define the Node Class:**
   Create a new class that inherits from `Node`. Define properties and methods as required.

   ```python
   class MyCustomNode(Node):
       node_id = "my_custom_node"
       node_name = "My Custom Node"

       # Define inputs
       input1 = NodeInput(id="input1", type="float")
       input2 = NodeInput(id="input2", type="float")

       # Define outputs
       output = NodeOutput(id="output", type="float")

       # Define the computation performed by the node
       async def func(self, input1: float, input2: float) -> None:
           result = input1 + input2  # Example operation
           self.outputs['output'].value = result
   ```

3. **Initiate and use the Nodes:**
   Once the class is defined, you can create an instance of this node in your node space and connect it as needed.

   ```python
   from funcnodes import NodeSpace

   ns = NodeSpace()
   custom_node = MyCustomNode()

   # Add the node to the node space
   ns.add_node_instance(custom_node)
   ```

### Method 2: Using Decorators

Funcnodes provides a decorator `@NodeDecorator` that simplifies the creation of custom nodes by automatically handling boilerplate code.

1. **Import the Decorator:**
   Import the `NodeDecorator` from funcnodes.

   ```python
   from funcnodes.nodemaker import NodeDecorator
   ```

2. **Define the Function:**
   Write a regular Python function that performs the computation you want. This function should accept inputs as arguments and return the output.

   ```python
   @NodeDecorator("addition_node")
   def addition(a: float, b: float) -> float:
       return a + b
   ```

   The `@NodeDecorator` takes the node ID as an argument and automatically creates a node class based on the signature of the function.

3. **Use the Decorated Node:**
   After defining the function with the decorator, it can be instantiated and used just like any other node class.

   ```python
   addition_node = addition()  # Instantiate the node
   ns.add_node_instance(addition_node)  # Add to the node space
   ```

4. **Adding nodes programmatically:**

   ```python
   from funcnodes import NodeSpace, get_nodeclass

   # Create a new node space
   ns = NodeSpace()

   # Get a node class and instantiate it
   AddNode = get_nodeclass('add_node')
   add_node = AddNode()

   # Add the node to the node space
   ns.add_node_instance(add_node)
   ```

5. **Connecting nodes:**
   ```python
   # Assuming add_node and another node (output_node) are already instantiated
   add_node.outputs['sum'].connect(output_node.inputs['input'])
   ```

### Advanced Usage

- **Creating custom nodes:**
  You can create custom nodes by extending the `Node` class. Refer to the [Contributing Guidelines](#contributing-guidelines) for more details on setting up a development environment for creating custom nodes.

## Configuration

Environment variables and configuration options can be set in a `.env` file or directly in the system environment. Key configuration options include:

- `FUNCNODES_CONFIG_DIR`: Path to the configuration directory (defaults to `~/.funcnodes`).
- `FUNCNODES_PORT`: Port for the web server (defaults to `8000`).

## Testing

To run tests:

```bash
pytest tests/
```

Ensure you have `pytest` installed, or install it using `pip install pytest`.

For more detailed documentation, visit the [official Funcnodes documentation](#).

## Contributing Guidelines

Contributions are welcome! Please refer to `CONTRIBUTING.md` for detailed instructions on setting up your development environment, coding standards, and the pull request process.

## Licensing Information

This project is licensed under the MIT License - see the `LICENSE` file for details.
