# Message Protocol

This document describes the WebSocket and HTTP communication protocols used between FuncNodes components.

---

## Protocol Overview

```
┌─────────────┐          WebSocket (JSON)           ┌─────────────┐
│             │ ──────────────────────────────────► │             │
│   Frontend  │                                     │   Worker    │
│    (UI)     │ ◄────────────────────────────────── │             │
│             │          WebSocket (JSON)           │             │
└──────┬──────┘                                     └──────┬──────┘
       │                                                   │
       │  HTTP (large payloads, uploads)                   │
       └───────────────────────────────────────────────────┘

┌─────────────┐          WebSocket (JSON)           ┌─────────────────┐
│             │ ──────────────────────────────────► │                 │
│   Frontend  │                                     │  Workermanager  │
│    (UI)     │ ◄────────────────────────────────── │                 │
│             │          WebSocket (JSON)           │                 │
└─────────────┘                                     └─────────────────┘
```

---

## Message Structure

### Base Message Format

All WebSocket messages are JSON objects with a `type` field:

```json
{
  "type": "<message_type>",
  ...additional fields...
}
```

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `ping` | Client → Server | Heartbeat request |
| `pong` | Server → Client | Heartbeat response |
| `cmd` | Client → Server | RPC command |
| `result` | Server → Client | Command response |
| `error` | Server → Client | Command error |
| `nodespaceevent` | Server → Client | Graph state change |
| `large_message` | Server → Client | Large payload indicator |
| `progress` | Server → Client | Operation progress |

---

## Workermanager Protocol

### Connection

```
ws://localhost:9380/
```

### Commands (String)

Simple string commands for basic operations:

| Command | Response | Description |
|---------|----------|-------------|
| `ping` | `pong` | Connectivity check |
| `identify` | JSON object | Get manager identity |
| `worker_status` | JSON object | Get all workers status |
| `stop` | - | Stop the manager |

**identify response:**

```json
{
  "class": "WorkerManager",
  "py": "/usr/bin/python3"
}
```

**worker_status response:**

```json
{
  "active": [
    {
      "uuid": "abc123",
      "name": "my-workflow",
      "host": "localhost",
      "port": 9382
    }
  ],
  "inactive": [
    {
      "uuid": "def456",
      "name": "other-workflow"
    }
  ]
}
```

### Commands (JSON)

Complex operations use JSON format:

#### new_worker

Create a new worker:

```json
// Request
{
  "type": "new_worker",
  "kwargs": {
    "name": "my-workflow",
    "copyLib": false,
    "copyNS": false,
    "in_venv": true,
    "reference": null
  }
}

// Response (broadcast)
{
  "type": "worker_created",
  "worker": {
    "uuid": "abc123",
    "name": "my-workflow",
    "data_path": "~/.funcnodes/workers/worker_my-workflow"
  }
}
```

#### set_active

Start a worker:

```json
// Request
{
  "type": "set_active",
  "workerid": "abc123"
}

// Response (broadcast)
{
  "type": "set_worker",
  "worker": {
    "uuid": "abc123",
    "host": "localhost",
    "port": 9382,
    "status": "running"
  }
}
```

#### stop_worker

Stop a running worker:

```json
{
  "type": "stop_worker",
  "workerid": "abc123"
}
```

#### restart_worker

Restart a worker:

```json
{
  "type": "restart_worker",
  "workerid": "abc123"
}
```

#### delete_worker

Delete a worker and its data:

```json
// Request
{
  "type": "delete_worker",
  "workerid": "abc123"
}

// Response (broadcast)
{
  "type": "worker_deleted",
  "workerid": "abc123"
}
```

### Progress Events

Long operations broadcast progress:

```json
{
  "type": "progress",
  "workerid": "abc123",
  "text": "Installing dependencies...",
  "progress": 0.45
}
```

---

## Worker Protocol

### Connection

```
ws://localhost:{worker_port}/
```

Default ports start at 9382 and increment for each worker.

### Basic Commands

#### ping/pong

```json
// Request
{"type": "ping"}

// Response
{"type": "pong"}
```

#### uuid

Get worker UUID:

```json
// Request
{"type": "cmd", "cmd": "uuid"}

// Response
{"type": "result", "cmd": "uuid", "result": "abc123"}
```

#### name

Get worker name:

```json
// Request
{"type": "cmd", "cmd": "name"}

// Response
{"type": "result", "cmd": "name", "result": "my-workflow"}
```

#### heartbeat

Keep worker alive (when `required_heartbeat` is set):

```json
{"type": "cmd", "cmd": "heartbeat"}
```

### State Commands

#### full_state

Get complete worker state:

```json
// Request
{"type": "cmd", "cmd": "full_state"}

// Response
{
  "type": "result",
  "cmd": "full_state",
  "result": {
    "nodespace": {
      "nodes": [...],
      "edges": [...],
      "prop": {...}
    },
    "lib": {
      "shelves": [...]
    },
    "worker": {
      "uuid": "abc123",
      "name": "my-workflow"
    }
  }
}
```

#### get_nodes

Get all nodes in the graph:

```json
// Request
{"type": "cmd", "cmd": "get_nodes"}

// Response
{
  "type": "result",
  "cmd": "get_nodes",
  "result": [
    {
      "node_id": "funcnodes_basic.math.add",
      "uuid": "node-1",
      "name": "Add",
      "inputs": {...},
      "outputs": {...}
    }
  ]
}
```

#### get_edges

Get all connections:

```json
// Request
{"type": "cmd", "cmd": "get_edges"}

// Response
{
  "type": "result",
  "cmd": "get_edges",
  "result": [
    {
      "src": ["node-1", "out"],
      "dst": ["node-2", "a"]
    }
  ]
}
```

#### get_library

Get available node shelves:

```json
// Request
{"type": "cmd", "cmd": "get_library"}

// Response
{
  "type": "result",
  "cmd": "get_library",
  "result": {
    "shelves": [
      {
        "name": "funcnodes_basic",
        "subshelves": [
          {
            "name": "math",
            "nodes": [
              {"node_id": "funcnodes_basic.math.add", "name": "Add"}
            ]
          }
        ]
      }
    ]
  }
}
```

### Mutation Commands

#### add_node

Add a node to the graph:

```json
// Request
{
  "type": "cmd",
  "cmd": "add_node",
  "kwargs": {
    "node_id": "funcnodes_basic.math.add",
    "uuid": "node-new-1",  // optional, auto-generated if omitted
    "frontend": {
      "pos": [100, 200]
    }
  }
}

// Response
{
  "type": "result",
  "cmd": "add_node",
  "result": {
    "uuid": "node-new-1",
    "node_id": "funcnodes_basic.math.add"
  }
}
```

#### remove_node

Remove a node:

```json
{
  "type": "cmd",
  "cmd": "remove_node",
  "kwargs": {
    "uuid": "node-1"
  }
}
```

#### update_node

Update a node's input or properties:

```json
// Set input value
{
  "type": "cmd",
  "cmd": "update_node",
  "kwargs": {
    "uuid": "node-1",
    "io_id": "a",
    "io_type": "input",
    "value": 42
  }
}

// Update frontend position
{
  "type": "cmd",
  "cmd": "update_node",
  "kwargs": {
    "uuid": "node-1",
    "frontend": {
      "pos": [150, 250]
    }
  }
}
```

#### add_edge

Create a connection:

```json
{
  "type": "cmd",
  "cmd": "add_edge",
  "kwargs": {
    "src_uuid": "node-1",
    "src_io": "out",
    "dst_uuid": "node-2",
    "dst_io": "a"
  }
}
```

#### remove_edge

Remove a connection:

```json
{
  "type": "cmd",
  "cmd": "remove_edge",
  "kwargs": {
    "src_uuid": "node-1",
    "src_io": "out",
    "dst_uuid": "node-2",
    "dst_io": "a"
  }
}
```

#### clear

Clear all nodes and edges:

```json
{
  "type": "cmd",
  "cmd": "clear"
}
```

### Module Commands

#### get_worker_dependencies

Get installed package dependencies:

```json
// Request
{"type": "cmd", "cmd": "get_worker_dependencies"}

// Response
{
  "type": "result",
  "cmd": "get_worker_dependencies",
  "result": {
    "funcnodes-basic": {"package": "funcnodes-basic", "version": "0.2.1"},
    "funcnodes-numpy": {"package": "funcnodes-numpy", "version": "0.2.5"}
  }
}
```

#### add_package_dependency

Install a module:

```json
{
  "type": "cmd",
  "cmd": "add_package_dependency",
  "kwargs": {
    "package": "funcnodes-plotly",
    "version": null  // or specific version
  }
}
```

#### remove_package_dependency

Uninstall a module:

```json
{
  "type": "cmd",
  "cmd": "remove_package_dependency",
  "kwargs": {
    "package": "funcnodes-plotly"
  }
}
```

### Import/Export Commands

#### export_worker

Export worker as ZIP:

```json
// Request
{
  "type": "cmd",
  "cmd": "export_worker",
  "kwargs": {
    "include_files": true
  }
}

// Response contains base64-encoded ZIP or large_message reference
```

#### import_worker

Import from ZIP:

```json
{
  "type": "cmd",
  "cmd": "import_worker",
  "kwargs": {
    "data": "<base64-encoded-zip>"
  }
}
```

#### load_data

Load nodespace from JSON:

```json
{
  "type": "cmd",
  "cmd": "load_data",
  "kwargs": {
    "data": {
      "nodes": [...],
      "edges": [...]
    }
  }
}
```

### Group Commands

#### get_groups

Get node groups:

```json
// Request
{"type": "cmd", "cmd": "get_groups"}

// Response
{
  "type": "result",
  "cmd": "get_groups",
  "result": [
    {
      "id": "group-1",
      "name": "Data Processing",
      "nodes": ["node-1", "node-2"]
    }
  ]
}
```

#### group_nodes

Create a group:

```json
{
  "type": "cmd",
  "cmd": "group_nodes",
  "kwargs": {
    "nodes": ["node-1", "node-2"],
    "name": "Data Processing"
  }
}
```

---

## NodeSpace Events

Workers broadcast state changes to all connected clients:

### node_added

```json
{
  "type": "nodespaceevent",
  "event": "node_added",
  "data": {
    "uuid": "node-1",
    "node_id": "funcnodes_basic.math.add",
    "serialized": {...}
  }
}
```

### node_removed

```json
{
  "type": "nodespaceevent",
  "event": "node_removed",
  "data": {
    "uuid": "node-1"
  }
}
```

### edge_added

```json
{
  "type": "nodespaceevent",
  "event": "edge_added",
  "data": {
    "src": ["node-1", "out"],
    "dst": ["node-2", "a"]
  }
}
```

### edge_removed

```json
{
  "type": "nodespaceevent",
  "event": "edge_removed",
  "data": {
    "src": ["node-1", "out"],
    "dst": ["node-2", "a"]
  }
}
```

### node_triggered

```json
{
  "type": "nodespaceevent",
  "event": "node_triggered",
  "data": {
    "uuid": "node-1"
  }
}
```

### node_done

```json
{
  "type": "nodespaceevent",
  "event": "node_done",
  "data": {
    "uuid": "node-1"
  }
}
```

### node_error

```json
{
  "type": "nodespaceevent",
  "event": "node_error",
  "data": {
    "uuid": "node-1",
    "error": "ValueError: invalid input",
    "traceback": "..."
  }
}
```

### io_value_changed

```json
{
  "type": "nodespaceevent",
  "event": "io_value_changed",
  "data": {
    "node_uuid": "node-1",
    "io_id": "out",
    "io_type": "output",
    "value": 42,
    "preview": "42"  // String representation for UI
  }
}
```

### node_progress

```json
{
  "type": "nodespaceevent",
  "event": "node_progress",
  "data": {
    "uuid": "node-1",
    "progress": 0.65,
    "message": "Processing item 65/100"
  }
}
```

---

## HTTP Endpoints

### Large Message Retrieval

When a message exceeds `MESSAGE_SIZE_BEFORE_REQUEST`:

```
GET /message/{msg_id}

Response: JSON payload
```

### File Upload

```
POST /upload/

Content-Type: multipart/form-data
Body: file data

Response:
{
  "success": true,
  "filename": "uploaded_file.csv",
  "path": "files/uploaded_file.csv"
}
```

### React Plugin Assets

```
GET /plugin/{module_name}/...

Response: Static files from module's react_plugin
```

---

## Error Handling

### Command Errors

```json
{
  "type": "error",
  "cmd": "add_node",
  "error": "NodeClassNotFoundError: unknown_node_id",
  "traceback": "..."  // Optional, depends on debug mode
}
```

### Common Error Types

| Error | Description |
|-------|-------------|
| `NodeClassNotFoundError` | Unknown node_id |
| `NodeConnectionError` | Invalid connection attempt |
| `MultipleConnectionsError` | Multiple connections to single-input |
| `SerializationError` | Value cannot be serialized |
| `ValidationError` | Invalid command parameters |

---

## Connection Lifecycle

```
Client                                    Server
  │                                         │
  │  1. WebSocket connect                   │
  │ ───────────────────────────────────────►│
  │                                         │
  │  2. {"type": "ping"}                    │
  │ ───────────────────────────────────────►│
  │                                         │
  │  3. {"type": "pong"}                    │
  │ ◄───────────────────────────────────────│
  │                                         │
  │  4. {"type": "cmd", "cmd": "full_state"}│
  │ ───────────────────────────────────────►│
  │                                         │
  │  5. {"type": "result", ...}             │
  │ ◄───────────────────────────────────────│
  │                                         │
  │  6. (ongoing) Events broadcast          │
  │ ◄───────────────────────────────────────│
  │                                         │
  │  7. WebSocket close                     │
  │ ───────────────────────────────────────►│
  │                                         │
```

---

## See Also

- [Architecture Overview](overview.md) — System diagram
- [Worker Components](worker-components.md) — Worker internals
- [Event System](event-system.md) — Event reference
