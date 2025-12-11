# First Steps with FuncNodes

This guide walks you through launching FuncNodes, creating your first worker, and building a simple workflow.

---

## 1. Launch the UI

Start the FuncNodes web interface:

```bash
funcnodes runserver # (1)!
```

1. For more options see the [CLI reference](../api/cli.md#runserver)

This opens a browser window with the FuncNodes interface:

![UI startup](../ui-guide/react_flow/interface_startup.png)

---

## 2. Create a Worker

[Workers](../components/worker.md) are isolated execution environments that run your workflows. Each worker has:

- Its own **virtual environment** (isolated dependencies)
- Its own **nodespace** (graph state)
- Its own **installed modules**

### Steps

1. Click **Worker** → **New** in the menu bar
2. Enter a name for your worker
3. Click **Create**

![new worker](../ui-guide/react_flow/new_worker.gif)

The worker is created in `~/.funcnodes/workers/` with its own virtualenv.

---

## 3. Start the Worker

1. Go to **Worker** → **Select**
2. Click on your worker's name

The worker is active when you see:

- **Nodespace** menu enabled in the header
- **Manage Libraries** button available

![run worker](../ui-guide/react_flow/run_worker.gif)

---

## 4. Install Modules

FuncNodes functionality comes from **modules**—Python packages containing nodes.

### Steps

1. Click **Manage Libraries**
2. Browse available modules:
   - **Installed** — Modules in your worker's environment
   - **Available** — Modules from the [official registry](https://github.com/Linkdlab/funcnodes_repositories){target="_blank"}
   - **Active** — Modules loaded in the current worker
3. Click **Add** to install a module

![add module](../ui-guide/react_flow/add_module.gif)

After installation, the module's [shelf](../components/shelf.md) appears in the **Lib** menu.

---

## 5. Add Nodes to Your Workflow

[Nodes](../components/node.md) are the computational units—functions with [inputs](../components/inputs-outputs.md) and outputs.

### Adding Nodes

1. Open the **Lib** menu
2. Browse shelves or use the **search bar**
3. **Double-click** a node name to add it to the [nodespace](../components/nodespace.md)

![node basics](../ui-guide/react_flow/basic_nodes.gif)

### Connecting Nodes

1. **Drag** from an output port to an input port to create a connection
2. **Click** on an input to edit its value manually (for compatible types)
3. **Hover** over any port to see its current value

### Execution Flow

- When an input changes, the node **triggers** automatically
- Outputs flow to connected inputs, potentially triggering downstream nodes
- Execution cascades through the graph based on data dependencies

---

## 6. What's Next?

Now that you have a running workflow:

| Topic | Description |
|-------|-------------|
| [Creating Nodes](../components/node.md) | Build custom nodes with decorators or classes |
| [Inputs & Outputs](../components/inputs-outputs.md) | Understand data flow and type rendering |
| [Examples](../examples/index.md) | See complete workflow examples |
| [Available Modules](../modules/index.md) | Browse the official module ecosystem |

---

## Tips

!!! tip "Live Preview"
    Click on connections to see data flowing through your workflow in real-time.

!!! tip "Development Mode"
    For developing custom nodes, use `funcnodes --dir .funcnodes runserver` to keep data in your project folder.
