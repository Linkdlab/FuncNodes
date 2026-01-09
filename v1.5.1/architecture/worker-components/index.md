# Worker Components (`funcnodes_worker`)

The `funcnodes_worker` package provides the runtime environment for executing FuncNodes graphs. This document explains the worker architecture and its components.

______________________________________________________________________

## Package Structure

```text
funcnodes_worker/
├── __init__.py           # Public exports
├── worker.py             # WSWorker class
├── websocket.py          # WebSocket server and RPC handling
├── loop.py               # Runtime loops (save, trigger, heartbeat)
├── external_worker.py    # External worker base class
└── config.py             # Worker configuration
```

______________________________________________________________________

## Worker Architecture

```
flowchart TB
    subgraph WSWorker["WSWorker"]
        subgraph EventLoop["Event Loop (asyncio)"]
            NSLoop["NodeSpaceLoop<br/>(5ms tick)"]
            SaveLoop["SaveLoop<br/>(1s tick)"]
            HeartLoop["HeartbeatLoop<br/>(optional)"]

            subgraph WS["WebSocket Server"]
                RPC["RPC command handling"]
                Broadcast["Event broadcasting"]
                HTTP["Large message HTTP fallback"]
            end
        end

        subgraph NS["NodeSpace"]
            Nodes["Nodes<br/>(graph)"]
            Edges["Edges<br/>(connections)"]
            Library["Library<br/>(shelves)"]
        end

        subgraph FS["File System (data_path/)"]
            NSJson["nodespace.json"]
            Files["files/"]
            Scripts["local_scripts/"]
            Log["worker.log"]
        end
    end
```

______________________________________________________________________

## WSWorker Class

The main worker class that orchestrates everything:

```python
class WSWorker:
    """WebSocket-based FuncNodes worker."""

    # Identity
    uuid: str                    # Unique identifier
    name: str                    # Human-readable name

    # Paths
    data_path: Path              # Worker data directory
    env_path: Optional[Path]     # Virtualenv path

    # Components
    nodespace: NodeSpace         # Graph container
    lib: Library                 # Node registry

    # Server
    host: str                    # WebSocket host
    port: int                    # WebSocket port

    # State
    _running: bool               # Is worker active?
    _clients: Set[WebSocket]     # Connected clients

    # Loops
    _nodespace_loop: NodeSpaceLoop
    _save_loop: SaveLoop
    _heartbeat_loop: Optional[HeartbeatLoop]
```

### Worker Lifecycle

```
stateDiagram-v2
    [*] --> Created: config.json written

    Created --> Starting: start()

    state Starting {
        [*] --> LoadLibs: Load libs
        LoadLibs --> LoadState: Load state
        LoadState --> StartWS: Start WS
    }

    Starting --> Running

    state Running {
        [*] --> Active
        Active: • Accepting WebSocket connections
        Active: • Processing RPC commands
        Active: • Executing node triggers
        Active: • Saving state periodically
    }

    Running --> Stopping: stop()

    state Stopping {
        [*] --> SaveState: Save state
        SaveState --> CloseWS: Close WS
        CloseWS --> Cleanup: Cleanup
    }

    Stopping --> Stopped

    Stopped --> [*]: PID file removed
```

______________________________________________________________________

## Runtime Loops

### NodeSpaceLoop

Processes pending node triggers:

```python
class NodeSpaceLoop:
    """Drains the node trigger queue."""

    interval: float = 0.005  # 5ms default

    async def run(self):
        while self._running:
            # Wait for any pending triggers to complete
            await self.nodespace.await_done()
            await asyncio.sleep(self.interval)
```

**Purpose:**

- Ensures async node execution completes
- Prevents event loop starvation
- Configurable tick rate for responsiveness vs CPU

### SaveLoop

Persists state to disk:

```python
class SaveLoop:
    """Periodically saves worker state."""

    interval: float = 1.0  # 1 second default

    async def run(self):
        while self._running:
            if self._save_requested:
                await self._save_state()
                self._save_requested = False
            await asyncio.sleep(self.interval)

    def request_save(self):
        """Mark that a save is needed."""
        self._save_requested = True
```

**Saved files:**

- `nodespace.json` — Graph state
- `worker_<uuid>.p` — PID file (liveness indicator)
- `worker_<uuid>.runstate` — Human-readable status

### HeartbeatLoop (Optional)

Enforces client connectivity:

```python
class HeartbeatLoop:
    """Stops worker if no heartbeat received."""

    timeout: float  # From worker config

    async def run(self):
        while self._running:
            if time.time() - self._last_heartbeat > self.timeout:
                logger.warning("Heartbeat timeout, stopping worker")
                await self.worker.stop()
            await asyncio.sleep(1.0)

    def heartbeat(self):
        """Called when client sends heartbeat."""
        self._last_heartbeat = time.time()
```

**Use case:** Auto-stop workers when UI disconnects (optional feature).

______________________________________________________________________

## WebSocket Server

### Connection Handling

```python
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    worker._clients.add(ws)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                await handle_message(ws, msg.data)
            elif msg.type == WSMsgType.BINARY:
                await handle_binary(ws, msg.data)
    finally:
        worker._clients.discard(ws)

    return ws
```

### RPC Dispatch

```python
async def handle_message(ws, data):
    msg = json.loads(data)

    if msg["type"] == "ping":
        await ws.send_json({"type": "pong"})

    elif msg["type"] == "cmd":
        cmd = msg["cmd"]
        kwargs = msg.get("kwargs", {})

        handler = COMMAND_HANDLERS.get(cmd)
        if handler:
            try:
                result = await handler(worker, **kwargs)
                await ws.send_json({
                    "type": "result",
                    "cmd": cmd,
                    "result": result
                })
            except Exception as e:
                await ws.send_json({
                    "type": "error",
                    "cmd": cmd,
                    "error": str(e)
                })
```

### Event Broadcasting

```python
def broadcast_event(event_type: str, data: dict):
    """Send event to all connected clients."""
    message = {
        "type": "nodespaceevent",
        "event": event_type,
        "data": data
    }
    for client in worker._clients:
        asyncio.create_task(client.send_json(message))
```

______________________________________________________________________

## Large Message Handling

Messages exceeding `MESSAGE_SIZE_BEFORE_REQUEST` (default 1MB) use HTTP fallback:

```text
┌──────────┐                          ┌──────────┐
│  Client  │                          │  Worker  │
└────┬─────┘                          └────┬─────┘
     │                                     │
     │  1. WS: request full_state          │
     │ ───────────────────────────────────►│
     │                                     │
     │  2. Worker serializes (>1MB)        │
     │                                     │
     │  3. WS: {"type": "large_message",   │
     │         "msg_id": "abc123"}         │
     │◄─────────────────────────────────── │
     │                                     │
     │  4. HTTP GET /message/abc123        │
     │ ───────────────────────────────────►│
     │                                     │
     │  5. HTTP Response (full JSON)       │
     │◄─────────────────────────────────── │
     │                                     │
```

```python
# Server side
async def send_large_message(ws, data):
    msg_id = str(uuid4())
    _pending_messages[msg_id] = data

    await ws.send_json({
        "type": "large_message",
        "msg_id": msg_id
    })

# HTTP endpoint
async def get_message(request):
    msg_id = request.match_info["msg_id"]
    data = _pending_messages.pop(msg_id)
    return web.json_response(data)
```

______________________________________________________________________

## File Upload Handling

Uploads are received via HTTP POST and stored in `files/`:

```python
async def upload_handler(request):
    reader = await request.multipart()

    async for part in reader:
        filename = part.filename
        # Security: sanitize filename, prevent path traversal
        safe_name = secure_filename(filename)

        target_path = worker.files_dir / safe_name

        with open(target_path, 'wb') as f:
            while chunk := await part.read_chunk():
                f.write(chunk)

    return web.json_response({"success": True})
```

**Security measures:**

- Filename sanitization
- Path traversal prevention (no `..`)
- Files constrained to `files/` directory
- Size limits at proxy layer (recommended)

______________________________________________________________________

## Worker Configuration

### WorkerConfig

```python
@dataclass
class WorkerConfig:
    uuid: str
    name: str

    # Paths
    data_path: Path
    env_path: Optional[Path]
    python_path: Optional[Path]

    # Network
    host: str = "localhost"
    port: int = 9382
    ssl: bool = False

    # Behavior
    update_on_startup: Dict[str, bool] = field(default_factory=dict)
    required_heartbeat: Optional[float] = None

    # Dependencies
    package_dependencies: Dict[str, PackageDependency] = field(default_factory=dict)
    worker_dependencies: Dict[str, Any] = field(default_factory=dict)

    # Type
    workertype: str = "WSWorker"
```

### Config File Location

```text
~/.funcnodes/workers/worker_<uuid>.json
```

### Example Config

```json
{
  "uuid": "abc123",
  "name": "my-workflow",
  "data_path": "~/.funcnodes/workers/worker_my-workflow",
  "env_path": "~/.funcnodes/workers/worker_my-workflow/.venv",
  "host": "localhost",
  "port": 9382,
  "ssl": false,
  "update_on_startup": {
    "funcnodes": true,
    "funcnodes-core": true
  },
  "package_dependencies": {
    "funcnodes-numpy": {
      "package": "funcnodes-numpy",
      "version": ">=0.2.0"
    }
  },
  "workertype": "WSWorker"
}
```

______________________________________________________________________

## External Workers

Custom worker types can be created by subclassing:

```python
from funcnodes_worker import ExternalWorker

class MyCustomWorker(ExternalWorker):
    """Custom worker with additional capabilities."""

    worker_type = "my_custom_worker"

    async def setup(self):
        """Called during worker initialization."""
        await super().setup()
        # Custom setup logic

    async def handle_custom_command(self, **kwargs):
        """Custom RPC command."""
        return {"custom": "result"}
```

Register via entry point:

```toml
[project.entry-points."funcnodes.module"]
external_worker = "my_module:MyCustomWorker"
```

______________________________________________________________________

## Process Isolation

### Separate Thread

For I/O-bound or blocking operations:

```python
@fn.NodeDecorator(
    node_id="heavy_io",
    separate_thread=True  # Run in ThreadPoolExecutor
)
def heavy_io_operation(data: bytes) -> bytes:
    # This won't block the event loop
    return process_data(data)
```

### Separate Process

For CPU-bound operations:

```python
@fn.NodeDecorator(
    node_id="cpu_intensive",
    separate_process=True  # Run in ProcessPoolExecutor
)
def cpu_intensive_task(data: list) -> list:
    # This runs in a separate process
    return [heavy_computation(x) for x in data]
```

**Note:** `separate_process` has limitations:

- Arguments must be picklable
- No access to node state during execution
- Higher overhead than threads

### Subprocess Monitor Integration

For long-running external processes:

```python
# Worker config
{
  "subprocess_monitor": {
    "host": "localhost",
    "port": 8765
  }
}

# Usage in node
async def run_external_tool(cmd: str):
    async with subprocess_monitor.spawn(cmd) as proc:
        async for line in proc.stdout:
            yield line  # Stream output
```

______________________________________________________________________

## Logging

### Per-Worker Logs

Each worker has its own rotating log file:

```text
~/.funcnodes/workers/worker_<name>/worker.log
```

### Log Configuration

```python
# Rotating file handler
handler = RotatingFileHandler(
    log_path,
    maxBytes=100_000,    # 100KB per file
    backupCount=5        # Keep 5 backups
)

# Format
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Log Levels

| Level   | Usage                           |
| ------- | ------------------------------- |
| DEBUG   | Detailed execution flow         |
| INFO    | Startup, shutdown, major events |
| WARNING | Recoverable issues              |
| ERROR   | Failures, exceptions            |

______________________________________________________________________

## See Also

- [Architecture Overview](https://linkdlab.github.io/FuncNodes/v1.5.1/architecture/overview/index.md) — System-level view
- [Core Components](https://linkdlab.github.io/FuncNodes/v1.5.1/architecture/core-components/index.md) — `funcnodes_core` internals
- [Message Protocol](https://linkdlab.github.io/FuncNodes/v1.5.1/architecture/message-protocol/index.md) — RPC reference
- [Worker Configuration](https://linkdlab.github.io/FuncNodes/v1.5.1/components/worker_config/index.md) — User guide
