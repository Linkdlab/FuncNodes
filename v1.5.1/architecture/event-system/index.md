# Event System

FuncNodes uses an event-driven architecture where components communicate through events. This document describes the event system and all available events.

______________________________________________________________________

## Overview

```
flowchart LR
    subgraph EventFlow["Event Flow"]
        Emitter["Emitter"]
        Queue["Event Queue"]

        subgraph Listeners["Listeners"]
            Internal["Internal Handler"]
            WS["WebSocket Relay"]
            Custom["Custom Handler"]
        end

        UI["🖥️ UI"]
    end

    Emitter -->|"emit()"| Queue
    Queue -->|dispatch| Internal
    Queue -->|dispatch| WS
    Queue -->|dispatch| Custom
    WS --> UI
```

______________________________________________________________________

## EventEmitter Base

All event-emitting components inherit from `EventEmitter`:

```python
from funcnodes_core.eventmanager import EventEmitter

class MyComponent(EventEmitter):
    def do_something(self):
        # ... do work ...
        self.emit("something_done", result=42)

# Subscribe to events
component = MyComponent()
component.on("something_done", lambda result: print(f"Got {result}"))

# Unsubscribe
component.off("something_done", handler)

# One-time listener
component.once("something_done", handler)
```

### API

| Method                         | Description                 |
| ------------------------------ | --------------------------- |
| `on(event, callback)`          | Subscribe to event          |
| `off(event, callback)`         | Unsubscribe from event      |
| `once(event, callback)`        | Subscribe for single event  |
| `emit(event, *args, **kwargs)` | Emit event to listeners     |
| `listeners(event)`             | Get all listeners for event |
| `remove_all_listeners(event)`  | Remove all listeners        |

______________________________________________________________________

## Node Events

### Trigger Events

Events related to node execution:

#### `before_trigger`

Emitted before node execution begins:

```python
node.on("before_trigger", lambda: print("About to execute"))
```

**Use cases:**

- Validation before execution
- Logging/profiling start

#### `after_trigger`

Emitted after node execution completes:

```python
node.on("after_trigger", lambda: print("Execution complete"))
```

**Use cases:**

- Cleanup operations
- Logging/profiling end
- Cascading updates

#### `trigger_error`

Emitted when node execution fails:

```python
node.on("trigger_error", lambda error: print(f"Error: {error}"))
```

**Payload:**

- `error`: Exception that was raised
- `traceback`: Full traceback string

### Progress Events

#### `progress`

Emitted during long-running operations:

```python
node.on("progress", lambda p, msg: print(f"{p*100:.0f}%: {msg}"))
```

**Payload:**

- `progress`: Float 0.0 to 1.0
- `message`: Optional status message

**Emitting progress:**

```python
class MyNode(fn.Node):
    async def func(self, data):
        for i, item in enumerate(self.progress(data)):
            process(item)
            # Progress automatically emitted
```

______________________________________________________________________

## IO Events

### NodeInput Events

#### `after_set_value`

Emitted when an input value changes:

```python
input.on("after_set_value", lambda value: print(f"New value: {value}"))
```

**When emitted:**

- Manual value set via `input.set_value()`
- Value received from connected output
- UI sets value via RPC

**Options:**

- `emit_value_set=False` suppresses this event
- `does_trigger=False` prevents node triggering

#### `value_options_changed`

Emitted when value constraints change:

```python
input.on("value_options_changed", lambda opts: update_ui(opts))
```

**Payload:** New `value_options` dict

#### `render_options_changed`

Emitted when render hints change:

```python
input.on("render_options_changed", lambda opts: update_ui(opts))
```

**Payload:** New `render_options` dict

### NodeOutput Events

#### `value_changed`

Emitted when output value changes:

```python
output.on("value_changed", lambda value: print(f"Output: {value}"))
```

**Triggered by:**

- Setting `output.value = x`
- Return value from decorated function

______________________________________________________________________

## Connection Events

### `connected`

Emitted when an IO is connected:

```python
io.on("connected", lambda other_io: print(f"Connected to {other_io.id}"))
```

### `disconnected`

Emitted when an IO is disconnected:

```python
io.on("disconnected", lambda other_io: print(f"Disconnected from {other_io.id}"))
```

______________________________________________________________________

## NodeSpace Events

### Node Lifecycle

#### `node_added`

Emitted when a node is added to the graph:

```python
nodespace.on("node_added", lambda node: print(f"Added: {node.node_id}"))
```

**Payload:** Node instance

#### `node_removed`

Emitted when a node is removed:

```python
nodespace.on("node_removed", lambda uuid: print(f"Removed: {uuid}"))
```

**Payload:** Node UUID string

### Edge Lifecycle

#### `edge_added`

Emitted when a connection is created:

```python
nodespace.on("edge_added", lambda src, dst: print(f"Connected {src} → {dst}"))
```

**Payload:**

- `src`: Tuple of (node_uuid, io_id)
- `dst`: Tuple of (node_uuid, io_id)

#### `edge_removed`

Emitted when a connection is removed:

```python
nodespace.on("edge_removed", lambda src, dst: print(f"Disconnected {src} → {dst}"))
```

### Execution Events

#### `node_triggered`

Emitted when a node starts execution:

```python
nodespace.on("node_triggered", lambda uuid: print(f"Triggered: {uuid}"))
```

#### `node_done`

Emitted when a node completes execution:

```python
nodespace.on("node_done", lambda uuid: print(f"Done: {uuid}"))
```

#### `node_error`

Emitted when a node execution fails:

```python
nodespace.on("node_error", lambda uuid, error: print(f"Error in {uuid}: {error}"))
```

**Payload:**

- `uuid`: Node UUID
- `error`: Exception message
- `traceback`: Full traceback

### State Events

#### `cleared`

Emitted when nodespace is cleared:

```python
nodespace.on("cleared", lambda: print("Graph cleared"))
```

#### `loaded`

Emitted after loading state:

```python
nodespace.on("loaded", lambda: print("Graph loaded"))
```

______________________________________________________________________

## Worker Events

### Lifecycle

#### `starting`

Emitted when worker begins startup:

```python
worker.on("starting", lambda: print("Worker starting..."))
```

#### `ready`

Emitted when worker is fully initialized:

```python
worker.on("ready", lambda: print("Worker ready"))
```

#### `stopping`

Emitted when worker begins shutdown:

```python
worker.on("stopping", lambda: print("Worker stopping..."))
```

#### `stopped`

Emitted after worker cleanup:

```python
worker.on("stopped", lambda: print("Worker stopped"))
```

### Client Events

#### `client_connected`

Emitted when a WebSocket client connects:

```python
worker.on("client_connected", lambda ws: print("Client connected"))
```

#### `client_disconnected`

Emitted when a client disconnects:

```python
worker.on("client_disconnected", lambda ws: print("Client disconnected"))
```

______________________________________________________________________

## Event Propagation

### Trigger Cascade

When an input value changes, events cascade through the graph:

```
flowchart TD
    SetValue["Input.set_value()"]

    EmitAfterSet["emit('after_set_value')"]
    RequestTrigger["Node.request_trigger()"]

    EmitBefore["emit('before_trigger')"]
    AwaitFunc["await func()"]
    SetOutput["Output.value = result"]
    EmitValueChanged["emit('value_changed')"]
    ConnectedInputs["Connected inputs..."]
    Cascade["(cascade continues)"]
    EmitAfter["emit('after_trigger')"]

    SetValue --> EmitAfterSet
    SetValue --> RequestTrigger

    RequestTrigger --> EmitBefore
    RequestTrigger --> AwaitFunc
    RequestTrigger --> EmitAfter

    AwaitFunc --> SetOutput
    SetOutput --> EmitValueChanged
    EmitValueChanged --> ConnectedInputs
    ConnectedInputs -.-> Cascade
```

### Event Relay to UI

The worker relays nodespace events to connected WebSocket clients:

```python
# Internal setup (simplified)
def setup_event_relay(nodespace, worker):
    def relay_to_clients(event_name):
        def handler(*args, **kwargs):
            worker.broadcast({
                "type": "nodespaceevent",
                "event": event_name,
                "data": serialize_event_data(args, kwargs)
            })
        return handler

    for event in RELAYED_EVENTS:
        nodespace.on(event, relay_to_clients(event))
```

**Relayed events:**

- `node_added`, `node_removed`
- `edge_added`, `edge_removed`
- `node_triggered`, `node_done`, `node_error`
- `io_value_changed`
- `node_progress`

______________________________________________________________________

## Custom Event Handlers

### Subscribing in Nodes

Class-based nodes can subscribe to their own events:

```python
class MyNode(fn.Node):
    node_id = "my_node"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on("before_trigger", self._log_start)
        self.on("after_trigger", self._log_end)

    def _log_start(self):
        print(f"Node {self.uuid} starting")

    def _log_end(self):
        print(f"Node {self.uuid} finished")
```

### NodeSpace Event Hooks

Workers can add custom handlers:

```python
class MyWorker(WSWorker):
    async def setup(self):
        await super().setup()
        self.nodespace.on("node_error", self._handle_error)

    def _handle_error(self, uuid, error, traceback):
        # Custom error handling
        send_alert(f"Node {uuid} failed: {error}")
```

______________________________________________________________________

## Dynamic IO Updates

### `@update_other_io_options`

Decorator to rebuild dropdown options when an input changes:

```python
from funcnodes_core.io_hooks import update_other_io_options

@fn.NodeDecorator(node_id="column_selector")
@update_other_io_options("column", modifier=lambda df: df.columns.tolist())
def select_column(df: pd.DataFrame, column: str) -> pd.Series:
    return df[column]
```

**How it works:**

1. When `df` input changes, modifier is called
1. Result becomes `column.value_options["options"]`
1. `value_options_changed` event fires
1. UI updates dropdown

### `@update_other_io_value_options`

Decorator to update numeric constraints:

```python
from funcnodes_core.io_hooks import update_other_io_value_options

@fn.NodeDecorator(node_id="list_get")
@update_other_io_value_options("index", options_generator=lambda lst: {
    "min": 0,
    "max": len(lst) - 1 if lst else 0
})
def list_get(lst: list, index: int) -> Any:
    return lst[index]
```

______________________________________________________________________

## Event Best Practices

### Do

✅ Use events for loose coupling between components ✅ Keep event handlers fast (offload heavy work) ✅ Clean up listeners when components are destroyed ✅ Use `once()` for one-time setup handlers ✅ Document custom events in node docstrings

### Don't

❌ Create circular event chains (A→B→A) ❌ Rely on event ordering between different emitters ❌ Block in event handlers (use async if needed) ❌ Emit events during `__init__` (object not ready) ❌ Store sensitive data in event payloads

______________________________________________________________________

## See Also

- [Architecture Overview](https://linkdlab.github.io/FuncNodes/v1.5.1/architecture/overview/index.md) — System diagram
- [Core Components](https://linkdlab.github.io/FuncNodes/v1.5.1/architecture/core-components/index.md) — Event emitter implementation
- [Message Protocol](https://linkdlab.github.io/FuncNodes/v1.5.1/architecture/message-protocol/index.md) — WebSocket event relay
- [Inputs & Outputs](https://linkdlab.github.io/FuncNodes/v1.5.1/components/inputs-outputs/index.md) — IO events
