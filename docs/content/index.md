# FuncNodes Documentation

**FuncNodes** is a modular workflow automation system for **data processing, AI pipelines, scientific computing, and task automation**.

![example](./examples/titanic.png)

<small>*[Plotly visualization example](./examples/titanic.md) — interactive data analysis in FuncNodes*</small>

---

## Quick Start

```bash
pip install funcnodes    # Install
funcnodes runserver      # Launch UI at localhost:8000
```

Then create a worker, add modules, and start building workflows visually.

---

## Try It Now

Create nodes interactively—the preview updates as you type:

<div>
<div id="node-code-demo" style="width:100%;aspect-ratio : 2 / 1;" ></div>
<script>
(()=>{
if (window.inject_fn_on_div) inject_nodebuilder_into_div({
  id: document.getElementById("node-code-demo"),
  python_code: default_py_editor_code,
  show_python_editor: true,
});
else
document.addEventListener("DOMContentLoaded", function (event) {
  window.inject_nodebuilder_into_div({
    id: document.getElementById("node-code-demo"),
    python_code: default_py_editor_code,
    show_python_editor: true,
  });
});
})();
</script>
</div>

---

## Features

| | |
|---|---|
| **Visual Editor** | Drag-and-drop workflow creation with live data previews |
| **Async Execution** | Non-blocking, event-driven processing |
| **Isolated Workers** | Each workflow runs in its own virtualenv |
| **Type-Aware UI** | Smart input rendering (sliders, dropdowns, custom widgets) |
| **Modular Ecosystem** | Install only the domain packages you need |
| **Python Native** | Turn any function into a node with one decorator |

---

## Documentation Guide

### Getting Started

| Page | Description |
|------|-------------|
| [Introduction](getting-started/introduction.md) | Architecture overview and core concepts |
| [Installation](getting-started/installation.md) | Setup instructions |
| [First Steps](getting-started/basic_usage.md) | Launch UI, create workers, build workflows |

### Core Concepts

| Page | Description |
|------|-------------|
| [Creating Nodes](components/node.md) | Class-based and decorator-based node creation |
| [Inputs & Outputs](components/inputs-outputs.md) | Data flow, types, render options, events |
| [Nodespace](components/nodespace.md) | Graph state and persistence |
| [Shelves & Libraries](components/shelf.md) | Organizing and discovering nodes |

### Runtime

| Page | Description |
|------|-------------|
| [Workers](components/worker.md) | Execution environments and RPC interface |
| [Workermanager](components/workermanager.md) | Worker orchestration service |
| [Configuration](components/config.md) | System and worker settings |

### Resources

| Page | Description |
|------|-------------|
| [Web UI Guide](ui-guide/react_flow/web-ui.md) | Using the visual editor |
| [Available Modules](modules/index.md) | Official node packages |
| [CLI Reference](api/cli.md) | Command-line interface |
| [Examples](examples/index.md) | Interactive workflow demos |

---

## Need Help?

- **[FAQ & Troubleshooting](faq/common-issues.md)** — Common issues and solutions
- **[GitHub Issues](https://github.com/Linkdlab/funcnodes/issues)** — Report bugs
- **[GitHub Discussions](https://github.com/Linkdlab/funcnodes/discussions)** — Ask questions
