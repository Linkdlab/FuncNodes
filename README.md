# FuncNodes - A Node-Based Data Processing Framework

FuncNodes is a powerful and flexible node-based data processing framework designed for creating complex data flow and processing pipelines. It allows users to define custom nodes, each encapsulating a specific functionality, and connect them to form a directed graph that represents the data processing logic.

## Features

- **Node-Based Architecture**: Create custom nodes with unique processing capabilities and connect them to build sophisticated data processing pipelines.
- **Asynchronous Processing**: Leverage Python's asyncio for concurrent processing of data across different nodes.
- **Dynamic Node Spaces**: Organize nodes into node spaces, allowing for modular and reusable components.
- **Event-Driven**: Nodes can emit and listen for events, enabling reactive programming patterns within your data flow.
- **Serialization**: Serialize and deserialize node states and configurations, making it easy to save and load processing graphs.
- **Worker Management**: Distribute processing load across multiple workers and manage them effectively.
- **Extensible Library**: Extend the core functionality with additional libraries and integrate with existing Python packages.

## Installation

To install FuncNodes, simply use pip:

```bash
pip install funcnodes
```

## Quick Start

Here's a quick example to get you started with FuncNodes:

```python
from funcnodes import Node, NodeSpace

# Define a custom node
class MyNode(Node):
    node_id = "mynode"
    node_name = "My Custom Node"

    async def func(self, input_data):
        # Process input_data and return the result
        return processed_data

# Create a node space and add nodes
space = NodeSpace()
node = MyNode()
space.add_node(node)

# Connect nodes and trigger processing
# ... (additional code to connect and use nodes)
```

## Documentation

Here's a quick example to get you started with FuncNodes:

```python
from funcnodes import Node, NodeDecorator, NodeSpace

# Define a custom node using the base class
class MyNode(Node):
    node_id = "mynode"
    node_name = "My Custom Node"

    async def func(self, input_data):
        # Process input_data and return the result
        return processed_data

# Alternatively, define a custom node using the decorator
@NodeDecorator(node_id="mynode_decorator", node_name="My Decorated Node")
async def my_decorated_node_func(input_data):
    # Process input_data and return the result
    return processed_data

# Create a node space and add nodes
space = NodeSpace()
node = MyNode()
decorated_node = my_decorated_node_func()
space.add_node(node)
space.add_node(decorated_node)

# Connect nodes and trigger processing
# ... (additional code to connect and use nodes)
```

## Creating Custom Nodes

To create custom nodes in FuncNodes, you can either subclass the `Node` base class or use the `@NodeDecorator` to convert a regular function into a node.

### Using the Base Class

Subclass the `Node` base class and define the `node_id` and `node_name` class attributes. Implement the `async def func(self, input_data)` method to define the node's functionality.

### Using the Decorator

Decorate an asynchronous function with `@NodeDecorator`, providing the `node_id` and `node_name`. The function's parameters will be treated as node inputs, and the return value as the node output.

### Requirements

When creating nodes, ensure that:

- Each node has a unique `node_id`.
- The `func` method or decorated function is an asynchronous coroutine.
- Inputs and outputs are properly managed within the `func` method.

For more detailed documentation, visit [FuncNodes Documentation](https://link-to-funcnodes-docs).

## Contributing

Contributions are welcome! If you'd like to contribute, please fork the repository and use a feature branch. Pull requests are warmly welcome.

## Licensing

The code in this project is licensed under MIT license. See the [LICENSE](LICENSE.md) file for more information.

## Contact

If you have any questions or feedback, please contact [FuncNodes Support](mailto:support@funcnodes.com).
