# Inputs & Outputs

In FuncNodes, inputs and outputs (IOs) serve as the fundamental connection points between nodes. They are responsible for handling the flow of data and triggering execution throughout a workflow. Both inputs and outputs extend from a common foundation—the NodeIO Base Class—which provides shared functionality for connection management, value handling, serialization, and event emission.

The main principle is that each IO can hold an arbitrary data object, referenceable via the `value` property. If the value is not set it is automatically set to the NoValue singleton object which is used to represent the absence of a value. This is important because None is a valid value for an IO.

If the value of an IO is changed this may trigger a range of events, including *e.g.* triggering the Node or passing its value to connected IOs.

## NodeIO Base Class

The inputs and outputs of a Node are both derived from the `NodeIO` base class. This class accepts the following parameters (for nromal use cases NodeIO is never intialized directly, but always via the child classes):

- **uuid**: Each IO has a unique ID that is generated when the IO is created. (1)
- **name**: Each IO has a name that is used as the referencing key and also for display purposes (defaults to the uuid).
- **description**: A description of the IO, mainly used for display purposes.
- **type**: The data type of the IO. This is treated as a hint for the UI and the backend, but is not enforced.
- **allow_multiple**: A boolean flag that indicates whether the IO have multiple connections to other IOs. By default this is False for inputs and True for outputs.
- **hidden**: A boolean flag that indicates whether the IO is hidden in the UI. This is useful for internal IOs or for very IO-rich nodes, to make them more usable.
- **render_options**: See [Render Options](#render-options).
- **value_options**: See [Value Options](#value-options).

1. Note: if the IO is derived of a function parameter, the id becomes the signature name of the parameter, so it is not individually unique. But IOs are always attasched to a node, with a unique id, so the combination of node id and IO id is always unique.

## Render Options

The IO-Render options are used to control and customize the appearance of the IO in the UI. In its base form these options are available:

- **type**: If the IO Type is different than what is should be rendered at (e.g. a number that should be rendered as a string or a custom frontend component, this can be set here).
- **set_default**: If the value of the IO is set manually, this flag indicates whether the new value should be set as the default value for the IO (meaning it will also be serialized, and has to be [serializable](https://linkdlab.github.io/FuncNodes/components/serialization/index.md)).

The render options are a dictionary, meaning it can be arbitrary extended with custom options. Which will be passed to the frontend and can there be used to customize the rendering of the IO.

## Value Options

The IO-Value options are used to control and customize the behavior of the IO-value. Currently these values are not directly enforced, but are used as hints for the UI and the backend and if required should be enforced in the respective node functions:

- **min**: The minimum value of the IO, currently used for number types.
- **max**: The maximum value of the IO, currently used for number types (1).
- **step**: The step size of the IO, currently used for number types.
- **options**: A list of options that the IO can take, rendered as a dropdown (2).

1. Note: If min and max are set the default frontend renders the IO as a slider.
1. For more control this can also be defined as a enum type in the form of a dictionary with keys and values (see example below).

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

## Events & triggering

- Inputs fire `after_set_value` events when `emit_value_set=True`; outputs fire on `trigger`.
- Inputs can opt out of triggering the node with `does_trigger=False` (useful for control signals or staged values).
- Hidden maintenance ports (e.g., the auto-created `_triggerinput`/`_triggeroutput`) use `hidden=True` to stay out of the UI.

## Dynamic IO updates

Use decorator helpers to recompute options based on other inputs:

- `update_other_io_options("target", modifier=...)` — recalc dropdown contents.
- `update_other_io_value_options("target", options_generator=...)` — recalc numeric bounds (`min/max/step`).

Patterns in the shipped modules:

- Pandas column selectors rebuild `options` from `df.columns`.
- Basic list nodes adjust valid indices to the current list length.
- File/folder pickers repopulate from the worker `files_dir`.

## Enumerations & `DataEnum`

For stable choice lists, subclass `fn.DataEnum`; it registers a type string and exposes `.v()` to resolve stored values. Example:

```python
class BorderTypes(fn.DataEnum):
    CONSTANT = (0, "Constant")
    REFLECT = (2, "Reflect")
```

Attach the enum as the IO `type` or use `value_options={"options": BorderTypes}`; the UI renders friendly labels while storing the underlying values.

## `NoValue` and optional outputs

`NoValue` represents “no data” and **suppresses downstream triggers**. Return it from optional outputs or routers to avoid firing branches unintentionally. Inputs default to `NoValue` until set; disconnecting an input resets it to its class default if provided.

## Render routing & previews

Node-level `default_render_options` can point the UI at a specific IO, e.g. `{"data": {"src": "figure"}}` for Plotly or images. Per-IO `render_options` can request widgets (`{"type": "color"}`, sliders via min/max) or mark values as preview-only.

### Custom renderers and type hints

- The global render-option registry lives in `funcnodes_core.config.FUNCNODES_RENDER_OPTIONS`. Modules can extend it at import time via an entry point (`render_options`) or by calling `funcnodes_core.config.update_render_options`.
- Serialization uses `funcnodes_core.utils.serialization.JSONEncoder/Decoder`; modules may register additional encoders so custom types can be stored in `nodespace.json` and previewed in the UI.
- Enums for dropdowns should subclass `fn.DataEnum` so both values and display labels are preserved.

## Connection rules & multiplicity

- Inputs default to **single connection**; set `allow_multiple=True` for fan-in semantics.
- Outputs allow multiple downstream connections.
- Connection validation prevents input→input and output→output wiring and enforces `allow_multiple`; violations raise `NodeConnectionError` / `MultipleConnectionsError`.
- There is no automatic cycle detection across the graph; avoid feedback loops unless your node logic guards against it.

## Serialization hints

- All IO values must be JSON-serializable by the registered encoders to persist in `nodespace.json`.
- Set `render_options["set_default"]=True` when user-set values should become the new default and be serialized with the graph.
