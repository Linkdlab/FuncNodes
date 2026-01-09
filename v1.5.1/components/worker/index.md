## What is a Worker?

Workers are long-lived processes that execute FuncNodes graphs. Each worker owns:

- A **NodeSpace** (graph state, groups, properties).
- An isolated **environment** (virtualenv by default) and dependency set.
- A **data directory** (`~/.funcnodes/workers/worker_<uuid>/`) containing `nodespace.json`, uploaded `files/`, optional `pyproject.toml`, and `worker.log`.
- A **WebSocket/HTTP server** that exposes RPC commands and large-payload endpoints.

Workers are started and supervised by the **Workermanager**, but you can also launch them directly via `funcnodes worker start`.

## Runtime loops & health

The worker event loop runs several recurring tasks:

- **NodeSpaceLoop** — drains pending triggers (`NodeSpace.await_done`) on a short interval (default 5 ms).
- **SaveLoop** — writes process/runstate files and persists the graph when `request_save()` is flagged.
- **LocalWorkerLookupLoop** — discovers external worker classes in `data_path/local_scripts`.
- **HeartbeatLoop** — optional; if `required_heartbeat` is set and no `heartbeat()` RPC arrives in time, the worker stops itself.

Defaults can be tuned via worker config (e.g., `nodespace_delay`, `save_delay`) for responsiveness vs. CPU/disk usage.

For stateful integrations that provide instance-bound nodes and background loops, see [External Workers](https://linkdlab.github.io/FuncNodes/v1.5.1/components/external-workers/index.md).

## RPC surface (WebSocket JSON)

Clients send `{"type":"cmd","cmd":<name>,"kwargs":{...}}`; worker replies with `result` or `error`. Common commands:

- **Identity/meta**: `uuid`, `name`, `get_meta`, `heartbeat`
- **State**: `full_state`, `get_nodes`, `get_edges`, `get_groups`, `view_state`, `get_save_state`
- **Mutations**: `update_node`, `update_group`, `group_nodes`, `remove_group`, `clear`, `save`, `load_data`, `export_worker`, `import_worker`
- **Library/modules**: `get_library`, `get_worker_dependencies`, `get_plugin_keys`, `get_plugin`, `add_package_dependency`, `remove_package_dependency`
- **External tooling**: `list_local_workers`, `start_local_worker`, `stop_local_worker`, `upload`

Ping/pong is built in (`{"type":"ping"}` → `{"type":"pong"}`) and is how the UI detects liveness.

## Messaging & large payloads

- Standard messages travel over WebSockets as JSON.
- Messages larger than `MESSAGE_SIZE_BEFORE_REQUEST` (default 1 MB) are staged in memory; the worker sends a `large_message` stub and exposes a temporary HTTP endpoint `/message/<msg_id>` for retrieval.
- Binary streams (e.g., image frames) are chunked with headers `chunk=<i>/<n>` to avoid blocking the socket.
- Uploads use `POST /upload/` and are forcibly rooted to `files/` inside the worker’s data dir; attempts to traverse elsewhere are rejected.

## Lifecycle & files on disk

When running, the worker writes:

- `worker_<uuid>.json` — config (host/port, env paths, flags)
- `worker_<uuid>.p` — PID file for liveness detection
- `worker_<uuid>.runstate` — human-readable status (“starting…”, “running”, etc.)

Shutting down clears PID/runstate and flushes a final save. Exports bundle `config`, `state`, optional `pyproject.toml`, and `files/` into a ZIP for backup/migration.

## Isolation & performance

- **Process/thread offload**: Nodes can set `separate_thread=True` or `separate_process=True` to avoid blocking the event loop.
- **Message size caps**: `MAX_DATA_SIZE` (default 10 GB) protects memory; adjust via env if needed.
- **Logging**: Per-worker rotating file handler (~100 KB × 5). Change location/level via config.

## Security considerations

- Workers do **not** implement authentication. In production, front them with an authenticated proxy (e.g., nginx/Traefik) and keep ports non-public. File writes are constrained to `files/`, but you should still sandbox network access and enforce upload size limits at the proxy.
- TLS termination is not provided by the worker itself; the `ssl` field in the config defaults to `False` and the WebSocket loop always starts plain HTTP. Terminate TLS in your proxy/load balancer instead.

## Environments & dependencies

- New workers create their own virtualenv unless started with `--not-in-venv`; sharing the interpreter is possible but increases the risk of version conflicts.
- The worker config carries `update_on_startup` flags (default `True` for `funcnodes`, `funcnodes-core`, `funcnodes-worker`) so core packages can be upgraded automatically when a worker starts.
- Additional packages installed via `funcnodes worker ... modules install ...` are tracked per worker in `package_dependencies`; isolated envs let different workers pin incompatible versions safely.

## Subprocess/offload options

- `@NodeDecorator(..., separate_thread=True)` runs the wrapped function in a thread; `separate_process=True` wraps it in a `ProcessPoolExecutor` (`funcnodes_core.utils.functions.make_run_in_new_process`).
- Workers expose an optional `subprocess_monitor` host/port in their config; if set, heavy external commands can be supervised by the `subprocess_monitor` service. FuncNodes itself does not enforce per-node resource limits—rely on the monitor/OS for that.
