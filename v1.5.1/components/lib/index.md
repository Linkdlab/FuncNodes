# Library (Shelf Registry)

The Library is the runtime registry that exposes shelves and node classes to a `NodeSpace`. It lives in `funcnodes_core.lib.Library` and is attached to every worker.

## Storage model

- Internally a flat dict keyed by tuple paths (`("Top", "Child", ...)`) pointing to `_ShelfRecord` entries that store **only node IDs**, not class objects.
- Weak references can be mounted (`add_external_shelf`, `add_subshelf_weak`) so externally owned shelves disappear automatically when GC’d.
- Materialized shelves are rebuilt on demand with `Shelf` objects; missing node classes are skipped if they are no longer registered.

## API highlights

- `add_shelf(shelf)` — merge/insert a full shelf tree (deduplicates node IDs).
- `add_node(s)/add_nodes` — append one or many node classes to a shelf path, creating intermediate shelves as needed.
- `remove_shelf`, `remove_shelf_path` — drop shelves (and descendants) by object or path.
- `find_nodeid` / `find_nodeclass` — return all shelf paths that reference a node.
- `get_node_by_id` — resolves a node class only if it is both registered and referenced somewhere; otherwise raises `NodeClassNotFoundError`.
- `full_serialize()` — JSON snapshot of all shelves, used by `NodeSpace.full_serialize()`.

## Population from installed modules

Module discovery runs via `funcnodes_core.libparser.module_to_shelf` and `_setup.py`:

1. Installed distributions are inspected for `funcnodes.module` entry points. If a `shelf` object is exported, it is validated (`check_shelf`) and mounted.
1. If no `shelf` entry point is provided, all non‑abstract `Node` subclasses in the module are grouped into a shelf named after the module.
1. Render options or external workers exported via entry points are applied separately and do not affect the library tree.

## Why flat storage?

Keeping only node IDs in `_records` avoids strong references to node classes and keeps the GC happy, while still allowing quick materialization of nested shelves when the UI or serialization needs them.
