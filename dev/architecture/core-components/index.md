# Core Components (`funcnodes_core`)

The `funcnodes_core` package provides the fundamental building blocks for the FuncNodes runtime. This document explains its internal architecture and key classes.

______________________________________________________________________

## Package Structure

```text
funcnodes_core/
├── __init__.py           # Public API exports
├── node.py               # Node, NodeDecorator
├── nodeio.py             # NodeIO, NodeInput, NodeOutput
├── nodespace.py          # NodeSpace (graph container)
├── lib.py                # Library, Shelf
├── config.py             # Configuration management
├── io_hooks.py           # IO update decorators
├── eventmanager.py       # Event subscription system
└── utils/
    ├── serialization.py  # JSON encoder/decoder
    ├── functions.py      # Async helpers, process wrappers
    └── data.py           # DataEnum, NoValue
```

______________________________________________________________________

## Node System

### Node Class Hierarchy

```
classDiagram
    class object {
    }

    class Node {
        +node_id: str
        +node_name: str
        +inputs: Dict
        +outputs: Dict
        +func()
    }

    class CustomNode {
        (user subclass)
    }

    class DecoratorNode {
        (generated from @NodeDecorator)
    }

    class PlaceHolderNode {
        (missing class fallback)
    }

    object <|-- Node : Base class for all nodes
    Node <|-- CustomNode
    Node <|-- DecoratorNode
    Node <|-- PlaceHolderNode
```

### Node Lifecycle

```python
# 1. Class Definition (at import time)
class MyNode(fn.Node):
    node_id = "my_module.my_node"
    node_name = "My Node"

    input1 = fn.NodeInput(id="input1", type=int)
    output1 = fn.NodeOutput(id="output1", type=int)

    async def func(self, input1):
        self.outputs["output1"].value = input1 * 2

# 2. Registration (module load)
# Node class is registered in Library via shelf

# 3. Instantiation (adding to graph)
node_instance = MyNode()  # Creates unique UUID
nodespace.add_node(node_instance)

# 4. Execution (triggered by input change)
await node_instance.trigger()  # Calls func() if inputs ready

# 5. Cleanup (removal)
nodespace.remove_node(node_instance.uuid)
```

### NodeDecorator Internals

The `@fn.NodeDecorator` creates a Node subclass dynamically:

```python
@fn.NodeDecorator(node_id="add_numbers", name="Add")
def add(a: int, b: int) -> int:
    return a + b

# Equivalent to:
class add(fn.Node):
    node_id = "add_numbers"
    node_name = "Add"

    a = fn.NodeInput(id="a", type=int)
    b = fn.NodeInput(id="b", type=int)
    out = fn.NodeOutput(id="out", type=int)

    async def func(self, a, b):
        result = add._original_func(a, b)
        self.outputs["out"].value = result
```

**Key transformations:**

1. Function parameters → `NodeInput` instances
1. Return type annotation → `NodeOutput` type
1. Return value → Assigned to output
1. Sync functions wrapped in async

______________________________________________________________________

## IO System

### NodeIO Base Class

```python
class NodeIO:
    """Base class for inputs and outputs."""

    # Identity
    uuid: str              # Unique identifier
    id: str                # Name/key (from parameter name)

    # Type info
    type: Type             # Python type hint

    # Value
    _value: Any            # Current value (use .value property)
    default: Any           # Default value

    # Behavior
    allow_multiple: bool   # Multiple connections allowed?
    hidden: bool           # Hidden from UI?

    # Options
    render_options: dict   # UI rendering hints
    value_options: dict    # Constraints (min, max, options)

    # Connections
    connections: List[NodeIO]  # Connected IOs
```

### NodeInput Specifics

```python
class NodeInput(NodeIO):
    does_trigger: bool = True    # Setting value triggers node?
    required: bool = True        # Must have value to execute?

    def set_value(self, value, does_trigger=True, emit_value_set=True):
        """Set input value, optionally triggering the node."""
        self._value = value
        if emit_value_set:
            self.emit("after_set_value", value)
        if does_trigger and self.does_trigger:
            self.node.request_trigger()
```

### NodeOutput Specifics

```python
class NodeOutput(NodeIO):
    allow_multiple: bool = True  # Default: multiple connections

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value
        # Propagate to all connected inputs
        for connected_input in self.connections:
            connected_input.set_value(new_value)
```

### NoValue Sentinel

```python
class NoValue:
    """Represents absence of a value (distinct from None)."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

# Usage
if input.value is NoValue:
    # Input has no value set
    pass
```

**NoValue semantics:**

- Default state for unset inputs
- Suppresses downstream triggering when set
- Distinct from `None` (which is a valid value)
- Reset state when disconnecting inputs

______________________________________________________________________

## NodeSpace

The `NodeSpace` is the in-memory graph container:

```python
class NodeSpace:
    """Container for a node graph."""

    # Storage
    _nodes: Dict[str, Node]           # UUID → Node instance
    _edges: List[Tuple[str, str, str, str]]  # Connections
    _lib: Library                     # Available node classes

    # Properties
    prop: Dict[str, Any]              # Serializable properties
    secret: Dict[str, Any]            # Non-serialized runtime state

    # Methods
    def add_node(self, node: Node) -> None
    def remove_node(self, uuid: str) -> None
    def add_edge(self, src_uuid, src_io, dst_uuid, dst_io) -> None
    def remove_edge(self, src_uuid, src_io, dst_uuid, dst_io) -> None

    # Serialization
    def serialize(self) -> NodeSpaceJSON
    def full_serialize(self, with_io_values=False) -> FullNodeSpaceJSON

    @classmethod
    def deserialize(cls, data: dict, lib: Library) -> NodeSpace
```

### Serialization Format

```json
{
  "nodes": [
    {
      "node_id": "funcnodes_basic.math.add",
      "uuid": "abc-123",
      "frontend": { "pos": [100, 200] },
      "io": {
        "a": { "value": 5 },
        "b": { "value": 3 }
      }
    }
  ],
  "edges": [
    {
      "src": ["node-1", "out"],
      "dst": ["node-2", "a"]
    }
  ],
  "prop": {
    "name": "My Workflow"
  },
  "groups": []
}
```

______________________________________________________________________

## Library System

### Library Class

```python
class Library:
    """Registry of node classes organized by shelf paths."""

    _records: Dict[Tuple[str, ...], _ShelfRecord]

    def add_shelf(self, shelf: Shelf) -> None
        """Add a shelf (and all its nodes) to the library."""

    def add_node(self, path: Tuple[str, ...], node_class: Type[Node]) -> None
        """Add a single node class to a shelf path."""

    def get_node_by_id(self, node_id: str) -> Type[Node]
        """Look up a node class by its node_id."""

    def find_nodeid(self, node_id: str) -> List[Tuple[str, ...]]
        """Find all shelf paths containing a node_id."""

    def full_serialize(self) -> dict
        """Serialize all shelves for transmission to UI."""
```

### Shelf Structure

```python
@dataclass
class Shelf:
    name: str
    description: str = ""
    nodes: List[Type[Node]] = field(default_factory=list)
    subshelves: List[Shelf] = field(default_factory=list)

# Example shelf hierarchy:
root_shelf = Shelf(
    name="funcnodes_numpy",
    description="NumPy operations",
    subshelves=[
        Shelf(name="creation", nodes=[zeros, ones, eye, ...]),
        Shelf(name="manipulation", nodes=[reshape, transpose, ...]),
        Shelf(name="math", nodes=[add, multiply, ...]),
    ]
)
```

### Module Discovery

```python
# Entry point in pyproject.toml:
[project.entry-points."funcnodes.module"]
module = "funcnodes_numpy"
shelf = "funcnodes_numpy:NODE_SHELF"

# Discovery process:
def discover_modules():
    for dist in importlib.metadata.distributions():
        eps = dist.entry_points
        if "funcnodes.module" in eps.groups:
            for ep in eps["funcnodes.module"]:
                if ep.name == "shelf":
                    shelf = ep.load()
                    library.add_shelf(shelf)
```

______________________________________________________________________

## Configuration

### Config Structure

```python
@dataclass
class FuncNodesConfig:
    env_dir: Path                    # Base directory
    worker_manager: WorkerManagerConfig
    frontend: FrontendConfig
    nodes: NodesConfig
    logging: LoggingConfig
    render_options: RenderOptionsConfig

@dataclass
class WorkerManagerConfig:
    host: str = "localhost"
    port: int = 9380
    ssl: bool = False

@dataclass
class NodesConfig:
    pretrigger_delay: float = 0.0    # Delay before triggering
```

### Config File Location

```text
~/.funcnodes/config.json
# or
$FUNCNODES_CONFIG_DIR/config.json
# or
--dir .funcnodes → .funcnodes/config.json
```

### Config Loading

```python
def get_config() -> FuncNodesConfig:
    """Load config, creating defaults if needed."""
    config_path = get_config_dir() / "config.json"

    if config_path.exists():
        config = load_config(config_path)
    else:
        config = FuncNodesConfig()
        save_config(config, config_path)

    return config
```

______________________________________________________________________

## Event System

The core uses an event emitter pattern:

```python
class EventEmitter:
    _listeners: Dict[str, List[Callable]]

    def on(self, event: str, callback: Callable) -> None
        """Subscribe to an event."""

    def off(self, event: str, callback: Callable) -> None
        """Unsubscribe from an event."""

    def emit(self, event: str, *args, **kwargs) -> None
        """Emit an event to all subscribers."""

# Node events
node.on("trigger", callback)
node.on("error", callback)

# IO events
input.on("after_set_value", callback)
output.on("value_changed", callback)

# NodeSpace events
nodespace.on("node_added", callback)
nodespace.on("node_removed", callback)
nodespace.on("edge_added", callback)
```

See [Event System](https://linkdlab.github.io/FuncNodes/dev/architecture/event-system/index.md) for the complete event reference.

______________________________________________________________________

## Utility Functions

### Async Helpers

```python
# Run sync function in thread pool
async def run_in_thread(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

# Run function in separate process
def make_run_in_new_process(func):
    """Decorator to run function in ProcessPoolExecutor."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            ProcessPoolExecutor(),
            partial(func, *args, **kwargs)
        )
    return wrapper
```

### Serialization

```python
class FuncNodesJSONEncoder(json.JSONEncoder):
    """Extended JSON encoder for FuncNodes types."""

    def default(self, obj):
        # NumPy arrays
        if isinstance(obj, np.ndarray):
            return {"__ndarray__": obj.tolist(), "dtype": str(obj.dtype)}

        # DataEnum
        if isinstance(obj, DataEnum):
            return {"__dataenum__": type(obj).__name__, "value": obj.value}

        # datetime
        if isinstance(obj, datetime):
            return {"__datetime__": obj.isoformat()}

        return super().default(obj)
```

______________________________________________________________________

## See Also

- [Architecture Overview](https://linkdlab.github.io/FuncNodes/dev/architecture/overview/index.md) — System-level view
- [Worker Components](https://linkdlab.github.io/FuncNodes/dev/architecture/worker-components/index.md) — Worker runtime
- [Event System](https://linkdlab.github.io/FuncNodes/dev/architecture/event-system/index.md) — Event reference
- [Creating Nodes](https://linkdlab.github.io/FuncNodes/dev/components/node/index.md) — User guide
