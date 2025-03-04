# Inputs & Outputs

In FuncNodes, inputs and outputs (IOs) serve as the fundamental connection points between nodes. They are responsible for handling the flow of data and triggering execution throughout a workflow. Both inputs and outputs extend from a common foundation—the NodeIO Base Class—which provides shared functionality for connection management, value handling, serialization, and event emission.

The main principle is that each IO can hold an arbitrary data object, referenceable via the `value` property.
If the value is not set it is automatically set to the NoValue singleton object which is used to represent the absence of a value. This is important because None is a valid value for an IO.

If the value of an IO is changed this may trigger a range of events, including _e.g._ triggering the Node or passing its value to connected IOs.

## NodeIO Base Class

The inputs and outputs of a Node are both derived from the `NodeIO` base class. This class accepts the following parameters (for nromal use cases NodeIO is never intialized directly, but always via the child classes):

<div class="annotate" markdown>
- **uuid**: Each IO has a unique ID that is generated when the IO is created. (1)
- **name**: Each IO has a name that is used as the referencing key and also for display purposes (defaults to the uuid).
- **description**: A description of the IO, mainly used for display purposes.
- **type**: The data type of the IO. This is treated as a hint for the UI and the backend, but is not enforced.
- **allow_multiple**: A boolean flag that indicates whether the IO have multiple connections to other IOs. By default this is False for inputs and True for outputs.
- **hidden**: A boolean flag that indicates whether the IO is hidden in the UI. This is useful for internal IOs or for very IO-rich nodes, to make them more usable.
- **render_options**: See [Render Options](#render-options).
- **value_options**: See [Value Options](#value-options).
</div>
1.  Note: if the IO is derived of a function parameter, the id becomes the signature name of the parameter, so it is not individually unique. But IOs are always attasched to a node, with a unique id, so the combination of node id and IO id is always unique.

## Render Options

The IO-Render options are used to control and customize the appearance of the IO in the UI. In its base form these options are available:

- **type**: If the IO Type is different than what is should be rendered at (e.g. a number that should be rendered as a string or a custom frontend component, this can be set here).
- **set_default**: If the value of the IO is set manually, this flag indicates whether the new value should be set as the default value for the IO (meaning it will also be serialized, and has to be [serializable](./serialization.md)).

The render options are a dictionary, meaning it can be arbitrary extended with custom options.
Which will be passed to the frontend and can there be used to customize the rendering of the IO.

## Value Options

The IO-Value options are used to control and customize the behavior of the IO-value. Currently these values are not directly enforced, but are used as hints for the UI and the backend and if required should be enforced in the respective node functions:

<div class="annotate" markdown>
- **min**: The minimum value of the IO, currently used for number types.
- **max**: The maximum value of the IO, currently used for number types (1).
- **step**: The step size of the IO, currently used for number types.
- **options**: A list of options that the IO can take, rendered as a dropdown (2).
</div>
1.  Note: If min and max are set the default frontend renders the IO as a slider.
2. For more control this can also be defined as a enum type in the form of a dictionary with keys and values (see example below).

```python
import funcnodes as fn

class IOModNode(fn.Node):
    node_id = "iomodnode"
    a = fn.NodeInput(
        value_options={"min": 0, "max": 1, "step": 0.1}, default=0.5, type=float
    )

    b = fn.NodeInput(
        render_options={"type": "color"}, type=str, default="#ff0000"
    )

    c = fn.NodeInput(
        value_options={"options": ["a", "b", "c"]}, default="a", type=str
    )
    d = fn.NodeInput(
        value_options={
            "options": {
                "type": "enum",
                "keys": ["full", "empty"],
                "values": [1, 0],
            }
        }
    )

    async def func(self, a: float, b: str, c: str, d: float):
        self.inputs["a"].set_value(float(d), does_trigger=False)

```

<div class="nodebuilder" code-source="prev_language-python" id="sdgg"></div>
