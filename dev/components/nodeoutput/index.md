# Node Outputs

`NodeOutput` is the output connection point for nodes in FuncNodes. It extends `NodeIO` and is responsible for sending data to connected inputs, triggering downstream execution.

______________________________________________________________________

## Constructor Parameters

```python
fn.NodeOutput(
    id: str,                           # Unique identifier (required)
    type: Type = Any,                  # Data type hint
    name: str = None,                  # Display name (defaults to id)
    description: str = None,           # Help text
    allow_multiple: bool = True,       # Allow multiple connections?
    hidden: bool = False,              # Hide in UI?
    value_options: dict = None,        # Value constraints (for previews)
    render_options: dict = None,       # UI rendering hints
    emit_value_set: bool = True,       # Emit events on value change?
    on: dict = None,                   # Event handlers
)
```

### Parameter Details

| Parameter        | Type   | Default  | Description                                                                               |
| ---------------- | ------ | -------- | ----------------------------------------------------------------------------------------- |
| `id`             | `str`  | Required | Unique identifier within the node. Used for programmatic access via `node.outputs["id"]`. |
| `type`           | `Type` | `Any`    | Python type hint. Affects how value is previewed in UI and serialized.                    |
| `name`           | `str`  | `id`     | Human-readable display name shown in UI.                                                  |
| `description`    | `str`  | `None`   | Tooltip/help text shown on hover in UI.                                                   |
| `allow_multiple` | `bool` | `True`   | If `True`, can connect to multiple inputs (fan-out). Almost always `True`.                |
| `hidden`         | `bool` | `False`  | If `True`, output is hidden from UI (but still functional).                               |
| `value_options`  | `dict` | `None`   | Metadata for previews (rarely used for outputs).                                          |
| `render_options` | `dict` | `None`   | UI hints for rendering previews.                                                          |
| `emit_value_set` | `bool` | `True`   | If `True`, emits `after_set_value` event when value changes.                              |
| `on`             | `dict` | `None`   | Event handlers to register.                                                               |

______________________________________________________________________

## Basic Usage

### Class-Based Nodes

```python
import funcnodes_core as fn

class CalculatorNode(fn.Node):
    node_id = "calculator"
    node_name = "Calculator"

    a = fn.NodeInput(id="a", type=float, default=0.0)
    b = fn.NodeInput(id="b", type=float, default=0.0)

    # Single output
    result = fn.NodeOutput(id="result", type=float)

    async def func(self, a, b):
        # Explicitly set output value
        self.outputs["result"].value = a + b
```

### Decorator-Based Nodes

With decorators, outputs are created from return type annotations:

```python
# Single output (named "out" by default)
@fn.NodeDecorator(node_id="double")
def double(x: float) -> float:
    return x * 2
```

### Using Type Annotations with `OutputMeta`

For more control over output properties in decorator-based nodes, use `typing.Annotated` with `fn.OutputMeta`:

```python
from typing import Annotated
import funcnodes_core as fn

@fn.NodeDecorator(node_id="process")
def process(
    value: int
) -> Annotated[int, fn.OutputMeta(name="result", description="Processed value")]:
    return value + 1
```

This approach:

- Uses `Annotated` on the **return type**
- The output **type** comes from the first argument to `Annotated`
- The output **name** and other properties come from `OutputMeta`

### `OutputMeta` Parameters

| Parameter        | Type   | Description                 |
| ---------------- | ------ | --------------------------- |
| `name`           | `str`  | Display name for the output |
| `description`    | `str`  | Help text shown in UI       |
| `hidden`         | `bool` | Whether to hide in UI       |
| `render_options` | `dict` | UI rendering hints          |

### Combining `InputMeta` and `OutputMeta`

You can use both in the same node for full control:

```python
from typing import Annotated
import funcnodes_core as fn

@fn.NodeDecorator(node_id="my_node")
def my_node(
    a: Annotated[
        int,
        fn.InputMeta(
            name="Input Value",
            description="Value to increment",
            default=1,
            does_trigger=False,
        ),
    ],
) -> Annotated[int, fn.OutputMeta(name="Result", description="Incremented value")]:
    return a + 1
```

______________________________________________________________________

## Setting Output Values

### In Class-Based Nodes

Outputs must be set **explicitly** in the `func` method:

```python
class MyNode(fn.Node):
    node_id = "my_node"

    input = fn.NodeInput(id="input", type=int)
    output = fn.NodeOutput(id="output", type=int)
    debug = fn.NodeOutput(id="debug", type=str)

    async def func(self, input):
        # Set outputs explicitly
        self.outputs["output"].value = input * 2
        self.outputs["debug"].value = f"Processed: {input}"
```

### In Decorator-Based Nodes

Return values are automatically assigned to outputs:

```python
# Single return → single output "out"
@fn.NodeDecorator(node_id="add")
def add(a: int, b: int) -> int:
    return a + b  # Assigned to output "out"
```

______________________________________________________________________

## Multiple Outputs

### Class-Based Approach

Simply define multiple `NodeOutput` attributes:

```python
class DivModNode(fn.Node):
    node_id = "divmod_node"

    a = fn.NodeInput(id="a", type=int)
    b = fn.NodeInput(id="b", type=int)

    quotient = fn.NodeOutput(id="quotient", type=int)
    remainder = fn.NodeOutput(id="remainder", type=int)

    async def func(self, a, b):
        q, r = divmod(a, b)
        self.outputs["quotient"].value = q
        self.outputs["remainder"].value = r
```

### Decorator with Typed Tuple

For multiple outputs in decorators, use `Tuple` with type hints:

```python
from typing import Tuple

@fn.NodeDecorator(node_id="divmod")
def divmod_node(a: int, b: int) -> Tuple[int, int]:
    return divmod(a, b)  # Creates outputs "out_0" and "out_1"
```

### Named Multiple Outputs

Use the `outputs` parameter to name them:

```python
from typing import Tuple

@fn.NodeDecorator(
    node_id="divmod",
    outputs=[
        {"name": "quotient"},
        {"name": "remainder"}
    ]
)
def divmod_node(a: int, b: int) -> Tuple[int, int]:
    q, r = divmod(a, b)
    return q, r  # quotient, remainder
```

### With Types in Output Spec

```python
@fn.NodeDecorator(
    node_id="stats",
    outputs=[
        {"name": "mean", "type": float},
        {"name": "std", "type": float},
        {"name": "count", "type": int}
    ]
)
def statistics(data: list) -> Tuple[float, float, int]:
    import statistics as st
    return st.mean(data), st.stdev(data), len(data)
```

______________________________________________________________________

## NoValue — Conditional Outputs

`NoValue` is a special sentinel that indicates "no data". When an output is set to `NoValue`, it **does not trigger** connected inputs.

### Suppressing Downstream Triggers

```python
from funcnodes_core import NoValue

class ConditionalNode(fn.Node):
    node_id = "conditional"

    condition = fn.NodeInput(id="condition", type=bool)
    value = fn.NodeInput(id="value", type=Any)

    on_true = fn.NodeOutput(id="on_true", type=Any)
    on_false = fn.NodeOutput(id="on_false", type=Any)

    async def func(self, condition, value):
        if condition:
            self.outputs["on_true"].value = value
            self.outputs["on_false"].value = NoValue  # Won't trigger connected nodes
        else:
            self.outputs["on_true"].value = NoValue
            self.outputs["on_false"].value = value
```

### In Decorators

```python
from funcnodes_core import NoValue

@fn.NodeDecorator(
    node_id="filter_positive",
    outputs=[{"name": "positive"}, {"name": "negative"}]
)
def filter_positive(value: float) -> Tuple[float, float]:
    if value >= 0:
        return value, NoValue  # Only positive output triggers
    else:
        return NoValue, value  # Only negative output triggers
```

______________________________________________________________________

## Output Value Propagation

When an output value is set, it automatically propagates to all connected inputs:

```
flowchart TD
    SetOutput["Output.value = x"]
    ForEach["For each<br/>connected input"]
    SetInput["input.set_value(x)"]
    InputTrigger["input.trigger()"]
    NodeTrigger["node.trigger()<br/>(if ready)"]

    SetOutput --> ForEach
    ForEach --> SetInput
    SetInput --> InputTrigger
    InputTrigger --> NodeTrigger
```

### Propagation Timing

- Values propagate **immediately** when set
- All connected inputs receive the value
- Each input may trigger its node (if `does_trigger=True`)
- Execution cascades through the graph

______________________________________________________________________

## Connection Behavior

### Fan-Out (Default)

Outputs can connect to **multiple inputs** by default:

```python
# Single output connected to multiple nodes
output = fn.NodeOutput(id="result", type=float)

# Connect to multiple inputs
output.connect(node1.inputs["a"])
output.connect(node2.inputs["x"])
output.connect(node3.inputs["value"])
# All three inputs receive the same value
```

### Restricting Connections

Rarely needed, but you can limit to single connection:

```python
# Only one input can connect (unusual for outputs)
exclusive_output = fn.NodeOutput(
    id="exclusive",
    type=Any,
    allow_multiple=False
)
```

### Connection on Value Set

When a new connection is made, the current output value is **immediately sent** to the newly connected input:

```python
# If output.value is already 42
output.connect(new_input)
# new_input.value is now 42
```

______________________________________________________________________

## Hidden Outputs

Hide outputs that are for internal use or debugging:

```python
class DebugNode(fn.Node):
    node_id = "debug_node"

    input = fn.NodeInput(id="input", type=Any)

    # Visible in UI
    result = fn.NodeOutput(id="result", type=Any)

    # Hidden from UI (for debugging/internal use)
    trace = fn.NodeOutput(id="trace", type=str, hidden=True)

    async def func(self, input):
        self.outputs["result"].value = process(input)
        self.outputs["trace"].value = f"Processed at {time.time()}"
```

______________________________________________________________________

## Preview Rendering

### Default Render Options

Configure how the output preview is displayed:

```python
class ImageNode(fn.Node):
    node_id = "image_processor"

    # Tell UI which output to use for node preview
    default_render_options = {
        "data": {"src": "output_image"}
    }

    input_image = fn.NodeInput(id="input_image", type="np.ndarray")
    output_image = fn.NodeOutput(id="output_image", type="np.ndarray")
```

### Per-Output Render Options

```python
# Plotly figure output
figure = fn.NodeOutput(
    id="figure",
    type="plotly.graph_objs.Figure",
    render_options={"type": "plotly"}
)
```

______________________________________________________________________

## Events

### Available Events

| Event               | When Fired             | Payload                                |
| ------------------- | ---------------------- | -------------------------------------- |
| `after_set_value`   | After value changes    | `{"src": output, "result": new_value}` |
| `before_connect`    | Before connection made | Connection info                        |
| `after_connect`     | After connection made  | Connection info                        |
| `before_disconnect` | Before disconnection   | Disconnection info                     |
| `after_disconnect`  | After disconnection    | Disconnection info                     |

### Subscribing to Events

```python
class MyNode(fn.Node):
    node_id = "my_node"

    output = fn.NodeOutput(id="output", type=int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outputs["output"].on("after_set_value", self._on_output_change)

    def _on_output_change(self, msg):
        print(f"Output set to: {msg['result']}")
```

______________________________________________________________________

## Status and State

### Check Output State

```python
output = node.outputs["result"]

# Check if value is set
has_value = output.value is not fn.NoValue

# Check if connected
is_connected = output.is_connected()

# Get connections
connections = output.connections  # List of connected NodeInputs

# Get full status
status = output.status()
# Returns: {"has_value": bool, "has_node": bool, "ready": bool, "connected": bool}
```

______________________________________________________________________

## Manual Triggering

Force propagation to connected inputs:

```python
# Trigger all connected inputs with current value
output.trigger()

# This:
# 1. Sets value on all connected inputs (without triggering them)
# 2. Then triggers each connected input
```

______________________________________________________________________

## Serialization

### Serialize Output State

```python
# Get serialized representation
serialized = output.serialize()
# Returns: {"id": "result", "type": "float", ...}

# Full serialization with value
full = output.full_serialize(with_value=True)
```

______________________________________________________________________

## Complete Examples

### Router Node (Conditional Output)

```python
import funcnodes_core as fn
from funcnodes_core import NoValue
from typing import Any

class RouterNode(fn.Node):
    """Routes input to one of multiple outputs based on a selector."""

    node_id = "router"
    node_name = "Router"

    value = fn.NodeInput(id="value", type=Any)
    route = fn.NodeInput(
        id="route",
        type=int,
        default=0,
        value_options={"min": 0, "max": 2}
    )

    out_0 = fn.NodeOutput(id="out_0", type=Any)
    out_1 = fn.NodeOutput(id="out_1", type=Any)
    out_2 = fn.NodeOutput(id="out_2", type=Any)

    async def func(self, value, route):
        outputs = [self.outputs["out_0"],
                   self.outputs["out_1"],
                   self.outputs["out_2"]]

        for i, out in enumerate(outputs):
            if i == route:
                out.value = value
            else:
                out.value = NoValue  # Don't trigger other routes
```

### Statistics Node (Multiple Typed Outputs)

```python
from typing import Tuple, List
import statistics

@fn.NodeDecorator(
    node_id="statistics",
    name="Statistics",
    outputs=[
        {"name": "mean", "type": float},
        {"name": "median", "type": float},
        {"name": "stdev", "type": float},
        {"name": "min", "type": float},
        {"name": "max", "type": float},
    ]
)
def calc_statistics(
    data: List[float]
) -> Tuple[float, float, float, float, float]:
    """Calculate various statistics for a list of numbers."""
    return (
        statistics.mean(data),
        statistics.median(data),
        statistics.stdev(data) if len(data) > 1 else 0.0,
        min(data),
        max(data),
    )
```

### Image Processing with Preview

```python
import funcnodes_core as fn

class GrayscaleNode(fn.Node):
    """Convert image to grayscale."""

    node_id = "grayscale"
    node_name = "To Grayscale"

    # Configure preview to show output_image
    default_render_options = {
        "data": {"src": "output_image"}
    }

    input_image = fn.NodeInput(id="input_image", type="np.ndarray")
    output_image = fn.NodeOutput(id="output_image", type="np.ndarray")

    async def func(self, input_image):
        import cv2
        gray = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)
        self.outputs["output_image"].value = gray
```

______________________________________________________________________

## Comparison: Input vs Output

| Aspect                     | NodeInput             | NodeOutput          |
| -------------------------- | --------------------- | ------------------- |
| **Direction**              | Receives data         | Sends data          |
| **allow_multiple default** | `False`               | `True`              |
| **Triggers node**          | Yes (configurable)    | No                  |
| **Has default value**      | Yes                   | No                  |
| **required parameter**     | Yes                   | No                  |
| **does_trigger parameter** | Yes                   | No                  |
| **Value propagation**      | From connected output | To connected inputs |

______________________________________________________________________

## See Also

- [Node Inputs](https://linkdlab.github.io/FuncNodes/dev/components/nodeinput/index.md) — Input connection points
- [Inputs & Outputs](https://linkdlab.github.io/FuncNodes/dev/components/inputs-outputs/index.md) — Complete IO reference
- [Creating Nodes](https://linkdlab.github.io/FuncNodes/dev/components/node/index.md) — Node creation patterns
- [Event System](https://linkdlab.github.io/FuncNodes/dev/architecture/event-system/index.md) — Event handling
