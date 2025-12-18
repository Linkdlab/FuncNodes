# Node Inputs

`NodeInput` is the input connection point for nodes in FuncNodes. It extends `NodeIO` with input-specific behavior including triggering, default values, and required/optional semantics.

______________________________________________________________________

## Constructor Parameters

```python
fn.NodeInput(
    id: str,                           # Unique identifier (required)
    type: Type = Any,                  # Data type hint
    name: str = None,                  # Display name (defaults to id)
    description: str = None,           # Help text
    default: Any = NoValue,            # Default value
    required: bool = True,             # Must have value to execute?
    does_trigger: bool = True,         # Triggers node on value change?
    allow_multiple: bool = False,      # Allow multiple connections?
    hidden: bool = False,              # Hide in UI
    value_options: dict = None,        # Value constraints
    render_options: dict = None,       # UI rendering hints
    emit_value_set: bool = True,       # Emit events on value change?
    on: dict = None,                   # Event handlers
)
```

### Parameter Details

| Parameter        | Type   | Default   | Description                                                                                                                 |
| ---------------- | ------ | --------- | --------------------------------------------------------------------------------------------------------------------------- |
| `id`             | `str`  | Required  | Unique identifier within the node. Used for programmatic access via `node.inputs["id"]`. Must be a valid Python identifier. |
| `type`           | `Type` | `Any`     | Python type hint. Affects UI rendering (e.g., `int` shows number input, `bool` shows checkbox). Not enforced at runtime.    |
| `name`           | `str`  | `id`      | Human-readable display name shown in UI.                                                                                    |
| `description`    | `str`  | `None`    | Tooltip/help text shown on hover in UI.                                                                                     |
| `default`        | `Any`  | `NoValue` | Default value when input is not connected and not manually set.                                                             |
| `required`       | `bool` | `True`    | If `True`, node won't execute until this input has a value.                                                                 |
| `does_trigger`   | `bool` | `True`    | If `True`, setting this input triggers node execution.                                                                      |
| `allow_multiple` | `bool` | `False`   | If `True`, multiple outputs can connect to this input.                                                                      |
| `hidden`         | `bool` | `False`   | If `True`, input is hidden from UI (but still functional).                                                                  |
| `value_options`  | `dict` | `None`    | Constraints like `min`, `max`, `step`, `options`.                                                                           |
| `render_options` | `dict` | `None`    | UI hints like custom renderer type.                                                                                         |
| `emit_value_set` | `bool` | `True`    | If `True`, emits `after_set_value` event when value changes.                                                                |
| `on`             | `dict` | `None`    | Event handlers to register (e.g., `{"after_set_value": handler}`).                                                          |

______________________________________________________________________

## Basic Usage

### Class-Based Nodes

```python
import funcnodes_core as fn

class MyNode(fn.Node):
    node_id = "my_module.my_node"
    node_name = "My Node"

    # Basic input with type and default
    value = fn.NodeInput(id="value", type=float, default=0.0)

    # Required input (must be set before node executes)
    data = fn.NodeInput(id="data", type=list, required=True)

    # Optional input with description
    label = fn.NodeInput(
        id="label",
        type=str,
        default="",
        required=False,
        description="Optional label for the output"
    )

    async def func(self, value, data, label):
        result = process(data, value)
        return f"{label}: {result}" if label else str(result)
```

### Decorator-Based Nodes

With decorators, inputs are created automatically from function parameters:

```python
@fn.NodeDecorator(node_id="add_numbers")
def add(a: int = 0, b: int = 0) -> int:
    return a + b
```

This creates:

- Input `a` with type `int`, default `0`
- Input `b` with type `int`, default `0`

### Using Type Annotations with `InputMeta`

For more control in decorator-based nodes, use `typing.Annotated` with `fn.InputMeta` to define all input properties inline:

```python
from typing import Annotated
import funcnodes_core as fn

@fn.NodeDecorator(node_id="my_node")
def my_node(
    a: Annotated[
        int,
        fn.InputMeta(
            name="Amount",           # Display name
            description="The amount to process",
            default=1,
            does_trigger=False,
            hidden=True,
        ),
    ],
) -> int:
    return a + 1
```

This approach:

- Uses the **parameter name** (`a`) as the input ID
- The **type** comes from the first argument to `Annotated`
- All input properties are specified in `InputMeta`

### `InputMeta` with Dynamic Options

You can also include event handlers directly in `InputMeta`:

```python
from typing import Annotated
import funcnodes_core as fn

@fn.NodeDecorator(node_id="dict_selector")
def dict_selector(
    data: Annotated[
        dict[str, int],
        fn.InputMeta(
            name="Data",
            description="Dictionary to select from",
            on={
                "after_set_value": fn.decorator.update_other_io_options(
                    "key",
                    list,  # Updates key's options to list(data.keys())
                )
            },
        ),
    ],
    key: str,
) -> int:
    return data[key]
```

Each node instance maintains **separate state** — setting `data` on one instance updates only that instance's `key` options:

```python
node1 = dict_selector()
node2 = dict_selector()

node1["data"] = {"k1": 1, "k2": 2}
node2["data"] = {"k3": 3, "k4": 4}

# node1's key options: ["k1", "k2"]
# node2's key options: ["k3", "k4"]
```

### `InputMeta` Parameters

| Parameter        | Type   | Description                               |
| ---------------- | ------ | ----------------------------------------- |
| `name`           | `str`  | Display name (defaults to parameter name) |
| `description`    | `str`  | Help text                                 |
| `default`        | `Any`  | Default value                             |
| `does_trigger`   | `bool` | Whether setting triggers execution        |
| `required`       | `bool` | Whether input must have value             |
| `hidden`         | `bool` | Whether to hide in UI                     |
| `value_options`  | `dict` | Constraints like `min`, `max`, `options`  |
| `render_options` | `dict` | UI rendering hints                        |
| `on`             | `dict` | Event handlers                            |

______________________________________________________________________

## Value Constraints (`value_options`)

### Numeric Constraints

```python
# Slider with min/max (renders as slider in UI)
amount = fn.NodeInput(
    id="amount",
    type=float,
    default=0.5,
    value_options={"min": 0.0, "max": 1.0, "step": 0.1}
)

# Integer with minimum only
count = fn.NodeInput(
    id="count",
    type=int,
    default=1,
    value_options={"min": 1}
)
```

### Dropdown Options

```python
# Simple string options
mode = fn.NodeInput(
    id="mode",
    type=str,
    default="fast",
    value_options={"options": ["fast", "balanced", "accurate"]}
)

# Enum-style options (display labels different from values)
border_type = fn.NodeInput(
    id="border",
    type=int,
    default=0,
    value_options={
        "options": {
            "type": "enum",
            "keys": ["Constant", "Reflect", "Replicate"],
            "values": [0, 2, 1]
        }
    }
)
```

### Using DataEnum for Type-Safe Options

```python
from funcnodes_core import DataEnum

class ColorMode(DataEnum):
    RGB = ("rgb", "RGB Color")
    HSV = ("hsv", "HSV Color")
    GRAY = ("gray", "Grayscale")

@fn.NodeDecorator(node_id="convert_color")
def convert_color(
    image: "np.ndarray",
    mode: ColorMode = ColorMode.RGB
) -> "np.ndarray":
    return convert(image, mode.v())  # .v() gets the actual value
```

______________________________________________________________________

## Dynamic Value Options

Update input constraints based on other inputs using decorators:

### Dynamic Dropdown (Column Selector)

```python
from funcnodes_core.decorator import update_other_io_options

@fn.NodeDecorator(
    node_id="select_column",
    default_io_options={
        "df": {
            "on": {
                "after_set_value": update_other_io_options(
                    "column",  # Target input to update
                    lambda df: list(df.columns)  # Generate options
                )
            }
        },
    },
)
def select_column(df: "pd.DataFrame", column: str) -> "pd.Series":
    return df[column]
```

### Dynamic Numeric Bounds (List Index)

```python
from funcnodes_core.decorator import update_other_io_value_options

@fn.NodeDecorator(
    node_id="list_get",
    default_io_options={
        "lst": {
            "on": {
                "after_set_value": update_other_io_value_options(
                    "index",  # Target input
                    lambda lst: {
                        "min": -len(lst),
                        "max": len(lst) - 1 if len(lst) > 0 else 0,
                    }
                )
            }
        },
    },
)
def list_get(lst: list, index: int = -1) -> Any:
    return lst[index]
```

______________________________________________________________________

## Triggering Behavior

### `does_trigger` Parameter

Controls whether setting this input triggers node execution:

```python
class WaitNode(fn.Node):
    node_id = "wait_node"

    # Setting delay does NOT trigger the node
    delay = fn.NodeInput(
        id="delay",
        type=float,
        default=1.0,
        does_trigger=False,  # Change this without re-executing
        value_options={"min": 0.0}
    )

    # Setting input DOES trigger the node
    input = fn.NodeInput(id="input", type=Any)

    output = fn.NodeOutput(id="output", type=Any)

    async def func(self, delay, input):
        await asyncio.sleep(delay)
        self.outputs["output"].value = input
```

**Use cases for `does_trigger=False`:**

- Configuration parameters that shouldn't cause re-execution
- Parameters that are read during execution but don't initiate it
- Collector inputs in loop constructs

### Programmatic Value Setting

```python
# Set value and trigger (default)
node.inputs["value"].set_value(42)

# Set value without triggering
node.inputs["value"].set_value(42, does_trigger=False)

# Using property (always triggers based on does_trigger setting)
node.inputs["value"].value = 42
```

______________________________________________________________________

## Required vs Optional Inputs

### Required Inputs (`required=True`)

Node will **not execute** until all required inputs have values:

```python
class ProcessNode(fn.Node):
    node_id = "process_node"

    # Must be set before node can run
    data = fn.NodeInput(id="data", type=list, required=True)

    async def func(self, data):
        return process(data)
```

### Optional Inputs (`required=False`)

Node can execute even if these inputs have no value:

```python
class FormatNode(fn.Node):
    node_id = "format_node"

    value = fn.NodeInput(id="value", type=float, required=True)

    # Optional: uses default if not provided
    precision = fn.NodeInput(
        id="precision",
        type=int,
        default=2,
        required=False
    )

    async def func(self, value, precision):
        return f"{value:.{precision}f}"
```

______________________________________________________________________

## Default Values

### Static Defaults

```python
threshold = fn.NodeInput(id="threshold", type=float, default=0.5)
enabled = fn.NodeInput(id="enabled", type=bool, default=True)
items = fn.NodeInput(id="items", type=list, default=[])
```

### Dynamic Defaults with DefaultFactory

For defaults that depend on input state:

```python
class MyNode(fn.Node):
    node_id = "my_node"

    @staticmethod
    @fn.NodeInput.DefaultFactory
    def _default_timestamp(input: fn.NodeInput):
        """Generate timestamp when accessed."""
        import time
        return time.time()

    timestamp = fn.NodeInput(
        id="timestamp",
        type=float,
        default=_default_timestamp
    )
```

______________________________________________________________________

## Connection Behavior

### Single Connection (Default)

```python
# Only one output can connect to this input
input = fn.NodeInput(id="input", type=int, allow_multiple=False)
```

### Multiple Connections

```python
# Multiple outputs can connect (fan-in)
inputs = fn.NodeInput(id="inputs", type=Any, allow_multiple=True)
```

Fan-in Semantics

When multiple outputs connect to a single input, only the **last value set** is used. The values don't accumulate automatically.

### Disconnection Behavior

When an input is disconnected, it resets to its default value:

```python
# If default is NoValue, input becomes "not set"
# If default is provided, input gets that value
```

______________________________________________________________________

## Input Forwarding

Inputs can forward their values to other inputs (useful for subgraphs):

```python
# Forward value from one input to another
input_a.forward(input_b)

# Remove forwarding
input_a.unforward(input_b)

# Check forwarding relationships
input_a.has_forward_to(input_b)
input_b.has_forwards_from(input_a)
```

______________________________________________________________________

## Events

### Available Events

| Event               | When Fired              | Payload                               |
| ------------------- | ----------------------- | ------------------------------------- |
| `after_set_value`   | After value changes     | `{"src": input, "result": new_value}` |
| `before_connect`    | Before connection made  | Connection info                       |
| `after_connect`     | After connection made   | Connection info                       |
| `before_disconnect` | Before disconnection    | Disconnection info                    |
| `after_disconnect`  | After disconnection     | Disconnection info                    |
| `before_forward`    | Before input forwarding | Forward info                          |
| `after_forward`     | After input forwarding  | Forward info                          |

### Subscribing to Events

```python
# In class-based node
class MyNode(fn.Node):
    node_id = "my_node"

    value = fn.NodeInput(id="value", type=int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inputs["value"].on("after_set_value", self._on_value_change)

    def _on_value_change(self, msg):
        print(f"Value changed to: {msg['result']}")

# Using on parameter
value = fn.NodeInput(
    id="value",
    type=int,
    on={"after_set_value": lambda msg: print(f"New: {msg['result']}")}
)
```

______________________________________________________________________

## Render Options

### Custom Renderer Type

```python
# Render as color picker
color = fn.NodeInput(
    id="color",
    type=str,
    default="#ff0000",
    render_options={"type": "color"}
)

# Render with custom step display
delay = fn.NodeInput(
    id="delay",
    type=float,
    default=1.0,
    render_options={"step": "0.1"}
)
```

### Set Default on Manual Edit

```python
# When user manually edits, save as new default
config = fn.NodeInput(
    id="config",
    type=dict,
    render_options={"set_default": True}
)
```

______________________________________________________________________

## Status and State

### Check Input State

```python
input = node.inputs["value"]

# Check if value is set
has_value = input.value is not fn.NoValue

# Check if connected
is_connected = input.is_connected()

# Check if ready (has value or not required)
is_ready = input.ready()

# Get full status
status = input.status()
# Returns: {"has_value": bool, "has_node": bool, "ready": bool,
#           "connected": bool, "required": bool}
```

______________________________________________________________________

## Serialization

### Serialize Input State

```python
# Get serialized representation
serialized = input.serialize()
# Returns: {"id": "value", "type": "int", "value": 42, ...}

# Full serialization with all details
full = input.full_serialize(with_value=True)
```

### Restore from Serialized

```python
input.deserialize({"value": 42, "required": False})
```

______________________________________________________________________

## Complete Example

```python
import funcnodes_core as fn
from funcnodes_core.decorator import update_other_io_value_options
from typing import List, Any

@fn.NodeDecorator(
    node_id="funcnodes_example.list_processor",
    name="List Processor",
    description="Process a list with configurable options",
    default_io_options={
        "items": {
            "on": {
                "after_set_value": update_other_io_value_options(
                    "start_index",
                    lambda lst: {"min": 0, "max": len(lst) - 1} if lst else {"min": 0, "max": 0}
                )
            }
        }
    }
)
def list_processor(
    items: List[Any],
    start_index: int = 0,
    reverse: bool = False,
    limit: int = 10
) -> List[Any]:
    """Process a list with various options."""
    result = items[start_index:]
    if reverse:
        result = list(reversed(result))
    return result[:limit]
```

______________________________________________________________________

## See Also

- [Node Outputs](https://linkdlab.github.io/FuncNodes/components/nodeoutput/index.md) — Output connection points
- [Inputs & Outputs](https://linkdlab.github.io/FuncNodes/components/inputs-outputs/index.md) — Complete IO reference
- [Creating Nodes](https://linkdlab.github.io/FuncNodes/components/node/index.md) — Node creation patterns
- [Event System](https://linkdlab.github.io/FuncNodes/architecture/event-system/index.md) — Event handling
