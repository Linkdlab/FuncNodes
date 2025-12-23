# First Steps with FuncNodes

This guide walks you through launching FuncNodes, creating your first worker, and building a simple workflow.

______________________________________________________________________

## 1. Launch the UI

Start the FuncNodes web interface:

```bash
funcnodes runserver # (1)!
```

1. For more options see the [CLI reference](https://linkdlab.github.io/FuncNodes/dev/api/cli/#runserver)

This opens a browser window with the FuncNodes interface:

______________________________________________________________________

## 2. Create a Worker

[Workers](https://linkdlab.github.io/FuncNodes/dev/components/worker/index.md) are isolated execution environments that run your workflows. Each worker has:

- Its own **virtual environment** (isolated dependencies)
- Its own **nodespace** (graph state)
- Its own **installed modules**

### Steps

1. Click **Worker** → **New** in the menu bar
1. Enter a name for your worker
1. Click **Create**

The worker is created in `~/.funcnodes/workers/` with its own virtualenv.

______________________________________________________________________

## 3. Start the Worker

1. Go to **Worker** → **Select**
1. Click on your worker's name

The worker is active when you see:

- **Nodespace** menu enabled in the header
- **Manage Libraries** button available

______________________________________________________________________

## 4. Install Modules

FuncNodes functionality comes from **modules**—Python packages containing nodes.

### Steps

1. Click **Manage Libraries**
1. Browse available modules:
1. **Installed** — Modules in your worker's environment
1. **Available** — Modules from the [official registry](https://github.com/Linkdlab/funcnodes_repositories)
1. **Active** — Modules loaded in the current worker
1. Click **Add** to install a module

After installation, the module's [shelf](https://linkdlab.github.io/FuncNodes/dev/components/shelf/index.md) appears in the **Lib** menu.

______________________________________________________________________

## 5. Add Nodes to Your Workflow

[Nodes](https://linkdlab.github.io/FuncNodes/dev/components/node/index.md) are the computational units—functions with [inputs](https://linkdlab.github.io/FuncNodes/dev/components/inputs-outputs/index.md) and outputs.

### Adding Nodes

1. Open the **Lib** menu
1. Browse shelves or use the **search bar**
1. **Double-click** a node name to add it to the [nodespace](https://linkdlab.github.io/FuncNodes/dev/components/nodespace/index.md)

### Connecting Nodes

1. **Drag** from an output port to an input port to create a connection
1. **Click** on an input to edit its value manually (for compatible types)
1. **Hover** over any port to see its current value

### Execution Flow

- When an input changes, the node **triggers** automatically
- Outputs flow to connected inputs, potentially triggering downstream nodes
- Execution cascades through the graph based on data dependencies

______________________________________________________________________

## 6. What's Next?

Now that you have a running workflow:

| Topic                                                                                           | Description                                   |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------- |
| [Creating Nodes](https://linkdlab.github.io/FuncNodes/dev/components/node/index.md)             | Build custom nodes with decorators or classes |
| [Inputs & Outputs](https://linkdlab.github.io/FuncNodes/dev/components/inputs-outputs/index.md) | Understand data flow and type rendering       |
| [Examples](https://linkdlab.github.io/FuncNodes/dev/examples/index.md)                          | See complete workflow examples                |
| [Available Modules](https://linkdlab.github.io/FuncNodes/dev/modules/index.md)                  | Browse the official module ecosystem          |

______________________________________________________________________

## Tips

Live Preview

Click on connections to see data flowing through your workflow in real-time.

Development Mode

For developing custom nodes, use `funcnodes --dir .funcnodes runserver` to keep data in your project folder.
