## External Workers (`FuncNodesExternalWorker`)

An **external worker** is a stateful, long-lived runtime component that runs *inside* a Worker process and can:

- Maintain persistent state/resources (connections, devices, caches, background tasks).
- Expose **instance-bound nodes** (node functions that operate on that specific instance).
- Optionally provide additional nodes grouped in a **Shelf**.

Use external workers when a pure, stateless node function is not enough—especially when you need a background loop, shared state, or controlled resource management.

---

## Mental model

- A **Worker** hosts a `NodeSpace` and executes graphs.
- An **external worker class** describes *what kind* of external worker it is (e.g. “camera”, “instrument”, “service client”).
- An **external worker instance** is a running object with its own state and optional background loop.
- The Worker integrates the instance into the library under an “external worker” namespace so its methods can be used as nodes in the graph.

---

## When to use (and not use) external workers

Good fits:

- Hardware I/O (serial devices, cameras, lab instruments).
- Long-lived network sessions (websocket clients, authenticated API clients).
- Background monitoring (watchers, polling loops, subscriptions).
- Stateful caches shared across many node invocations.

Avoid external workers when:

- The logic is naturally a pure function (use `@NodeDecorator`).
- You only need offloading for expensive computation (use `separate_thread=True` / `separate_process=True` on nodes).
- State can be passed explicitly through node inputs/outputs without a long-lived object.

---

## Building an external worker (minimum requirements)

### 1) Define a stable class id

Every concrete external worker class must define a stable identifier:

- `NODECLASSID = "<unique_id>"`

This id is used to:

- Refer to the worker type in the UI / RPC payloads.
- Construct node ids for instance methods.

If you build an abstract base class for reuse, keep it abstract and do not register it as a concrete worker type.

### 2) Implement an async loop

External workers are *loops*. Implement:

- `async def loop(self): ...`

This method is called repeatedly by the worker’s loop manager. Keep it:

- Non-blocking (do not do long synchronous I/O here).
- Resilient (handle intermittent failures; log and continue when safe).

If you need blocking calls, move them to threads, subprocesses, or async I/O.

### 3) Expose instance methods as nodes

To expose per-instance operations, decorate methods as **instance node functions** via `instance_nodefunction()`.

Conceptually:

- Each decorated method becomes a node class in the library.
- The node executes against *that external worker instance*, so it can use `self` state.

Node id convention (conceptual):

- `<NODECLASSID>.<instance_uuid>.<method_name>`

Concrete example:

- `my_worker.2f3a8c7f1b4a4b3c8d9e0f1a2b3c4d5e.get_status`

Here, `2f3a...` is the **external worker instance UUID** (not the Worker process UUID).

#### `instance_nodefunction()` options (practical)

`instance_nodefunction()` accepts:

- **Node metadata** (similar to `@NodeDecorator`), e.g. `default_io_options`, `default_render_options`, `description`.
- **Exposed method metadata**, e.g. `inputs=[...]` and `outputs=[...]` to override/extend derived I/O schemas.
- **`trigger_on_call`**: whether calling the instance method directly should `request_trigger()` any existing nodes of that method.
  - If omitted (`None`), it defaults to “trigger on call if the node has no inputs”.

Examples:

```python
from funcnodes_core import instance_nodefunction


class MyWorker(...):
    @instance_nodefunction(
        outputs=[{"name": "status", "type": "str"}],
        default_render_options={"data": {"src": "status", "type": "text"}},
    )
    def get_status(self) -> str:
        return "ok"
```

```python
class MyWorker(...):
    @instance_nodefunction(
        trigger_on_call=False,
        default_io_options={
            "mode": {"value_options": {"options": ["fast", "safe"]}},
        },
    )
    async def run(self, mode: str = "safe") -> str:
        ...
```

#### Accessing nodes created from a method (`.nodes()` / `.nodeclass()`)

At runtime, instance node functions also provide helper APIs:

- `self.<method>.nodes()` returns the current node instances created from that method for *this* external worker instance.
- `self.<method>.nodeclass()` returns the generated node class for that method for *this* instance.

This is commonly used to update input defaults/options dynamically (e.g., after config or state changes).

```python
class MyWorker(...):
    @instance_nodefunction(default_io_options={"item": {"value_options": {"options": []}}})
    def pick(self, item: str) -> str:
        return item

    def refresh_items(self, items: list[str]) -> None:
        for node in self.pick.nodes():
            node.inputs["item"].update_value_options(options=items)
        self.pick.nodeclass().input_item.update_value_options(options=items)
```

Note: older code may pass `self` into `nodes(self)` / `nodeclass(self)`; that instance argument is deprecated.

---

---

## Configuration (`ExternalWorkerConfig`)

External workers can declare a Pydantic config model to drive:

- Validation/defaults for worker configuration.
- JSON schema for UI forms.

Pattern:

- Create `class MyConfig(ExternalWorkerConfig): ...`
- Set `config_cls = MyConfig` on the external worker class.

### Reacting to config changes

External workers typically implement a “post update” hook to apply changes:

- Validate and apply config changes safely and idempotently.
- If the set of exposed nodes/shelves depends on config, trigger a refresh (see below).

Common pattern:

1. Read `self.config` (already validated/merged).
2. Apply changes to internal state/resources.
3. If the *library surface* changed (shelf contents or UI options), emit a nodes update.

### Export vs. save (secrets)

Worker *exports* (for sharing/migration) should not leak secrets.

If your config includes tokens/credentials, mark them as non-exportable:

- Class-level: `EXPORT_EXCLUDE_FIELDS = {"token", ...}`
- Field-level: set a JSON schema extra flag `export: false` on that field.

The goal is:

- Normal saves preserve full state for local use.
- Exports redact sensitive fields.

---

## Providing additional nodes via a Shelf (optional)

Beyond instance methods, an external worker can optionally provide a `Shelf` by implementing `get_nodeshelf()`:

- This is useful when you want to group extra nodes under a named subshelf.
- The shelf can be computed dynamically based on current worker state/config.

Signature (conceptual):

- `def get_nodeshelf(self) -> Optional[Shelf]: ...`

Behavior:

- If it returns `None`, no subshelf is added.
- If it returns a `Shelf`, the Worker adds it as a **weak subshelf** for the external worker instance.

### Instance methods vs shelf nodes (how to choose)

- Prefer **instance methods** for operations that must run against the instance state (`self`).
- Prefer a **shelf** when you want to expose a grouped set of nodes that is:
  - generated dynamically (e.g. based on config or discovered capabilities), or
  - not naturally expressed as a single method-per-node on the instance.

### Refresh mechanics (`"nodes_update"`)

If the shelf contents or UI options depend on state/config changes:

- Emit a `"nodes_update"` event (`self.emit("nodes_update")`) after the change.
- Alternatively, set/replace the shelf (which emits `"nodes_update"` internally when a shelf is assigned).

Minimal sketch:

```python
from typing import Optional
from funcnodes_core import Shelf


class MyWorker(...):
    def get_nodeshelf(self) -> Optional[Shelf]:
        return self._nodeshelf

    def post_config_update(self):
        self._nodeshelf = self._build_shelf_from_config()
        self.emit("nodes_update")
```

---

## Lifecycle and cleanup

External workers should clearly define:

- What resources are acquired (files, sockets, threads, subprocesses).
- How they are released on stop.

Recommended approach:

- Keep resource acquisition in init/setup methods that can fail cleanly.
- Ensure stop triggers cleanup and ends the loop promptly.
- Avoid reference cycles (event handlers capturing `self`, long-lived closures) that prevent garbage collection.

### `cleanup()`

External workers inherit cleanup behavior from `NodeClassMixin`:

- `cleanup()` cleans up all node instances created for this external worker instance.
- `stop()` calls `cleanup()` as part of shutdown.

If you override `cleanup()` to release extra resources, always call `super().cleanup()` as well.

---

## Discovery & registration (how external workers become available)

There are two common ways external worker classes become available to a Worker:

1. **Local scripts (development/experiments)**
   A Worker can scan a local scripts directory and discover subclasses placed there.

   - Default location: `<worker_data_path>/local_scripts/`
   - Any `*.py` file in that folder (recursively) can define subclasses of `FuncNodesExternalWorker`.
   - Discovered classes become available to instantiate as external worker instances.

2. **Module-provided external workers (packaged distribution)**
   A FuncNodes module can advertise external worker classes via its `funcnodes.module` entry points under the key `external_worker`.

   Minimal `pyproject.toml` entry point:

   ```toml
   [project.entry-points."funcnodes.module"]
   module = "my_pkg"
   shelf = "my_pkg:NODE_SHELF"
   external_worker = "my_pkg:FUNCNODES_WORKER_CLASSES"
   ```

   And in `my_pkg/__init__.py`:

   ```python
   from .my_worker import MyWorker

   FUNCNODES_WORKER_CLASSES = [MyWorker]
   ```

   `FUNCNODES_WORKER_CLASSES` may also be a single class instead of a list/tuple.

The Worker then exposes these “available worker classes” so the UI can instantiate and manage instances.

---

## Minimal template (starter)

This is a minimal shape of an external worker. Replace the method decorators and config fields to fit your use case.

```python
from pydantic import Field
from funcnodes_worker import FuncNodesExternalWorker, ExternalWorkerConfig
from funcnodes_core import instance_nodefunction


class MyWorkerConfig(ExternalWorkerConfig):
    interval_s: float = Field(default=1.0, ge=0.05)


class MyWorker(FuncNodesExternalWorker):
    NODECLASSID = "my_worker"
    config_cls = MyWorkerConfig

    async def loop(self):
        # background maintenance work (non-blocking)
        ...

    def post_config_update(self):
        # apply config changes; optionally refresh nodes/shelf
        ...

    @instance_nodefunction()
    def get_status(self) -> str:
        # instance-bound node that reads state
        return "ok"
```

---

## Troubleshooting checklist

- **`TypeError` about awaiting `None`**: `loop()` must be `async def loop(self): ...`.
- **Worker becomes unresponsive**: avoid blocking I/O in `loop()` and `post_config_update()`; offload to async/thread/process as needed.
- **UI does not update options/shelf**: emit `self.emit("nodes_update")` after changing shelf or updating node input options.
- **Secrets leaked in exports**: exclude sensitive config fields via `EXPORT_EXCLUDE_FIELDS` / field `export: false`.
