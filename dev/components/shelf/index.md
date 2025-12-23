# Shelves (Node Library Groups)

Shelves are the catalog entries that tell FuncNodes which node classes are available and how they are grouped in the UI. A shelf is a small tree that contains node classes (`funcnodes_core.node.Node`) and optional subshelves.

## Structure

- **Data model:** `funcnodes_core.lib.Shelf` holds `name`, `description`, `nodes` (list of node classes), and `subshelves` (list of Shelves). Each shelf gets a generated `shelf_id` when validated.
- **Serialization:** Shelves serialize to JSON via `funcnodes_core.lib.serialize_shelf`, emitting `name`, `description`, `nodes` (serialized node classes), and nested `subshelves`.
- **Storage:** The runtime keeps a flat registry (`funcnodes_core.lib.Library`) keyed by tuple paths (`("Top", "Child", ...)`) for GC‑friendly storage. Complete shelf trees are materialized on demand.

## How shelves are discovered

FuncNodes loads shelves from installed Python packages via the `funcnodes.module` entry point group:

- If a distribution exposes `shelf = "<pkg>:<object>"` under `project.entry-points."funcnodes.module"`, that object is read and validated with `funcnodes_core.lib.check_shelf`. Dictionaries are accepted and converted to `Shelf` instances.
- If no `shelf` entry point is present, FuncNodes falls back to introspection: every non‑abstract subclass of `Node` defined in the module is collected into a shelf named after the module (`funcnodes_core.lib.libparser.module_to_shelf`).
- Additional optional entry points (`render_options`, `external_worker`, `plugin_setup`) may also be exported; they are processed in `_setup.py` but do not affect shelf discovery itself.

Example (from `modules/funcnodes_files/pyproject.toml`):

```toml
[project.entry-points."funcnodes.module"]
module = "funcnodes_files"
shelf = "funcnodes_files:NODE_SHELF"
react_plugin = "funcnodes_files:REACT_PLUGIN"
```

Here `NODE_SHELF` is the authoritative shelf object; the React plugin entry point is consumed by the UI host but does not change the shelf tree.

## How shelves are mounted at runtime

- The Workermanager/Worker loads installed modules, parses their entry points, and registers shelves into a `Library` instance attached to each `NodeSpace`.
- `Library.add_shelf` merges shelves by path, keeping node IDs unique per shelf. External shelves can be mounted via weak references (`add_external_shelf`, `add_subshelf_weak`) so they disappear automatically when their owner is GC’d.
- Finding nodes is path‑aware: `Library.find_nodeid` returns all shelf paths containing a node ID, and `get_node_by_id` only succeeds if the node is both registered and referenced by at least one shelf.

## Authoring guidance for module writers

- Export a `Shelf` (or dict convertible to one) through the `funcnodes.module` entry point to get precise grouping and descriptions.
- Ensure each node class has a globally unique `node_id`; shelves store only node IDs, so duplicates are skipped when the Library deduplicates.
- Organize subshelves for UI grouping—paths are preserved (`["Vision", "Filters", ...]`) and rendered as nested menus in the editor host.
