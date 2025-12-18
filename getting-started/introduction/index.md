# Introduction to FuncNodes

FuncNodes is a **modular workflow automation framework** that uses node-based execution to handle complex computational tasks. Users construct workflows by connecting nodes—each representing a function—into a visual graph that processes data automatically.

______________________________________________________________________

## Architecture Overview

```
flowchart TB
    subgraph System["FuncNodes System"]
        UI["🖥️ Web UI<br/>(React Flow)"]
        WM["⚙️ Workermanager<br/>(orchestrates worker lifecycle)"]

        subgraph Workers["Worker Pool"]
            subgraph W1["Worker 1"]
                V1["venv"]
                NS1["Nodespace<br/>(graph)"]
            end
            subgraph W2["Worker 2"]
                V2["venv"]
                NS2["Nodespace<br/>(graph)"]
            end
            subgraph WN["Worker N"]
                VN["venv"]
                NSN["Nodespace<br/>(graph)"]
            end
        end
    end

    UI <-->|WebSocket| WM
    WM --> W1
    WM --> W2
    WM --> WN
```

______________________________________________________________________

## Core Concepts

### Nodes

Nodes are the fundamental building blocks of FuncNodes:

- Each node encapsulates a **function** with defined **inputs** and **outputs**
- Nodes execute automatically when all required inputs are available
- Creating nodes is **extremely** simple—just add a decorator to an existing function:

```python
import funcnodes as fn

@fn.NodeDecorator(node_id="add_numbers")
def add(a: int, b: int) -> int:
    return a + b
```

### Data Flow

- Nodes connect via inputs and outputs, forming a **directed acyclic graph (DAG)**
- Data flows from outputs to inputs, **triggering execution dynamically**
- The system automatically determines execution order based on dependencies

### Workers

Workers are **isolated execution environments** that run node graphs:

- Each worker has its own **virtual environment** for dependency isolation
- Workers are **sandboxed**, preventing conflicts between workflows
- Multiple workers can run simultaneously with different configurations

### Workermanager

The Workermanager is a **supervisory service** that:

- Orchestrates worker lifecycle (create, start, stop, delete)
- Provides a central discovery point for the UI
- Manages worker communication via WebSocket

______________________________________________________________________

## Execution Model

### Event-Driven Triggering

FuncNodes uses an **event-driven execution model**:

1. **Input Change** → A node's input value is set or updated
1. **Trigger Check** → System verifies all required inputs are available
1. **Execution** → Node function runs asynchronously
1. **Propagation** → Output values flow to connected downstream nodes
1. **Cascade** → Connected nodes trigger if their inputs are satisfied

### Parallel Processing

- Nodes without data dependencies execute **in parallel**
- Heavy computations can run in **separate threads or processes**
- The async architecture ensures the UI stays responsive

______________________________________________________________________

## Key Features

| Feature                   | Description                                                          |
| ------------------------- | -------------------------------------------------------------------- |
| **Visual Editor**         | Drag-and-drop workflow creation with live previews                   |
| **Live Data Preview**     | Hover over connections to see current values                         |
| **Modular Ecosystem**     | Install domain-specific node packages as needed                      |
| **Type-Aware UI**         | Inputs render as sliders, dropdowns, or custom widgets based on type |
| **Isolated Environments** | Each worker manages its own dependencies                             |
| **Async by Default**      | Non-blocking execution for responsive workflows                      |

______________________________________________________________________

## Example: Image Processing Pipeline

This image processing workflow demonstrates FuncNodes' **live preview** capabilities:

- Each node shows a preview of its current output
- Numeric inputs with `min`/`max` render as **interactive sliders**
- The workflow converts an image to grayscale except where the cat has red fur

______________________________________________________________________

## Next Steps

1. **[Install FuncNodes](https://linkdlab.github.io/FuncNodes/getting-started/installation/index.md)** — Set up your environment
1. **[First Steps](https://linkdlab.github.io/FuncNodes/getting-started/basic_usage/index.md)** — Launch the UI and create your first workflow
1. **[Creating Nodes](https://linkdlab.github.io/FuncNodes/components/node/index.md)** — Learn the two ways to define nodes
1. **[Inputs & Outputs](https://linkdlab.github.io/FuncNodes/components/inputs-outputs/index.md)** — Understand data flow and type hints
