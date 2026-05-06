# NodeSpace (Graph State)

`NodeSpace` is the in‑memory representation of a FuncNodes graph plus its library snapshot. Each worker owns exactly one `NodeSpace`.

## What a NodeSpace contains

- **Nodes:** Instances of node classes keyed by UUID.
- **Edges:** Connections between outputs and inputs (stored as tuples of source/target UUIDs and IO IDs).
- **Library:** A `funcnodes_core.lib.Library` with all shelves/nodes visible to this worker.
- **Properties:** Public `prop` (JSON‑serializable) and non‑serialized `secret` properties for runtime state.
- **Groups:** Optional node group metadata from `GroupingLogic`.

## Serialization

Two JSON shapes are used:

- `serialize()` → minimal `NodeSpaceJSON` with `nodes`, `edges`, `prop`, `groups`. IO values are included only if set as defaults; secret properties are excluded.
- `full_serialize(with_io_values=False)` → adds `lib` (full shelf tree) and can embed current IO values when requested.

Files on disk (`nodespace.json` inside each worker’s data directory) use `serialize()`. They are read back with `deserialize`, which re‑hydrates nodes via the library; missing classes become `PlaceHolderNode` instances.

## Edge and connection rules

- Connections must be output→input (or input forwarding) and honor each IO’s `allow_multiple` flag; violations raise `NodeConnectionError` / `MultipleConnectionsError`.
- There is no automatic cycle detection; avoid wiring graphs that feed back indefinitely unless your node logic guards against it.

## Lifecycle hooks

`NodeSpace` emits events on node add/remove, trigger errors (`node_error` / `node_trigger_error`), and cleanup. Workers subscribe to these to update clients.

Error handling is event-only: there is no built-in retry/backoff. When a node raises, the error event is emitted and the node stays in its current state until retriggered by another input change or a manual trigger.

## Persistence cadence

Workers run a `SaveLoop` that writes the serialized NodeSpace to disk when `request_save()` is set (e.g., after edits). Exporting a worker bundles this serialized graph together with config and optional files.
