# Creating Custom Modules

This guide walks you through creating a FuncNodes module from scratch — a Python package that provides nodes for the FuncNodes ecosystem.

______________________________________________________________________

## Overview

A FuncNodes module is a standard Python package with:

1. **Node definitions** — Functions or classes decorated as nodes
1. **Shelf organization** — Grouping nodes into a browsable hierarchy
1. **Entry points** — Registration so FuncNodes discovers your module
1. **Optional: React plugin** — Custom UI components for your nodes

```text
my_funcnodes_module/
├── pyproject.toml          # Package metadata + entry points
├── src/
│   └── funcnodes_mymodule/
│       ├── __init__.py     # Exports NODE_SHELF
│       ├── nodes.py        # Node definitions
│       └── _react_plugin.py  # Optional: React plugin info
└── react_plugin/           # Optional: React UI components
    ├── package.json
    ├── vite.config.ts
    └── src/
        └── index.tsx
```

______________________________________________________________________

## Quick Start with funcnodes_module

The fastest way to create a module is using the `funcnodes_module` scaffolding tool:

```bash
# Install the tool
pip install funcnodes-module

# Create a new module
funcnodes_module create funcnodes_mymodule

# Or with options
funcnodes_module create funcnodes_mymodule \
    --description "My awesome nodes" \
    --author "Your Name" \
    --with-react-plugin
```

This generates a complete project structure with:

- Pre-configured `pyproject.toml`
- Example node definitions
- Test setup with `funcnodes_pytest`
- Optional React plugin scaffold

______________________________________________________________________

## Manual Setup

### Step 1: Project Structure

Create your package structure:

```bash
mkdir funcnodes_mymodule
cd funcnodes_mymodule
mkdir -p src/funcnodes_mymodule
touch src/funcnodes_mymodule/__init__.py
touch src/funcnodes_mymodule/nodes.py
touch pyproject.toml
```

### Step 2: pyproject.toml

Configure your package with the required entry points:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "funcnodes-mymodule"
version = "0.1.0"
description = "My custom FuncNodes module"
readme = "README.md"
license = "MIT"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
]
dependencies = [
    "funcnodes-core>=0.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "funcnodes-pytest",
]

# CRITICAL: Entry points for FuncNodes discovery
[project.entry-points."funcnodes.module"]
module = "funcnodes_mymodule"
shelf = "funcnodes_mymodule:NODE_SHELF"

[tool.hatch.build.targets.wheel]
packages = ["src/funcnodes_mymodule"]
```

### Step 3: Define Nodes

Create your nodes in `src/funcnodes_mymodule/nodes.py`:

```python
import funcnodes_core as fn
from typing import List

@fn.NodeDecorator(
    node_id="funcnodes_mymodule.greet",
    name="Greet",
    description="Creates a greeting message"
)
def greet(name: str = "World") -> str:
    """Generate a greeting for the given name."""
    return f"Hello, {name}!"


@fn.NodeDecorator(
    node_id="funcnodes_mymodule.sum_list",
    name="Sum List",
    description="Sums all numbers in a list"
)
def sum_list(numbers: List[float]) -> float:
    """Calculate the sum of a list of numbers."""
    return sum(numbers)


@fn.NodeDecorator(
    node_id="funcnodes_mymodule.multiply",
    name="Multiply",
    description="Multiplies two numbers"
)
def multiply(
    a: float = 1.0,
    b: float = 1.0
) -> float:
    """Multiply two numbers together."""
    return a * b
```

### Step 4: Create the Shelf

Export your nodes in `src/funcnodes_mymodule/__init__.py`:

```python
from funcnodes_core import Shelf

from .nodes import greet, sum_list, multiply

# Define the shelf structure
NODE_SHELF = Shelf(
    name="My Module",
    description="Custom nodes for demonstration",
    nodes=[greet, sum_list, multiply],
    subshelves=[]
)

# Export for convenience
__all__ = ["NODE_SHELF", "greet", "sum_list", "multiply"]
```

### Step 5: Install and Test

```bash
# Install in development mode
pip install -e .

# Verify discovery
funcnodes modules list
# Should show: funcnodes_mymodule

# Test in the UI
funcnodes runserver
```

______________________________________________________________________

## Entry Points Reference

The `[project.entry-points."funcnodes.module"]` section tells FuncNodes how to load your module:

| Entry Point       | Required    | Description                      |
| ----------------- | ----------- | -------------------------------- |
| `module`          | Yes         | Import path to your module root  |
| `shelf`           | Recommended | Path to your `NODE_SHELF` object |
| `react_plugin`    | Optional    | Path to React plugin info dict   |
| `render_options`  | Optional    | Custom render options for types  |
| `external_worker` | Optional    | Custom worker class              |

### Example with All Entry Points

```toml
[project.entry-points."funcnodes.module"]
module = "funcnodes_mymodule"
shelf = "funcnodes_mymodule:NODE_SHELF"
react_plugin = "funcnodes_mymodule:REACT_PLUGIN"
render_options = "funcnodes_mymodule:RENDER_OPTIONS"
```

______________________________________________________________________

## Shelf Organization

### Flat Structure

For simple modules with few nodes:

```python
NODE_SHELF = Shelf(
    name="My Module",
    nodes=[node1, node2, node3]
)
```

### Nested Structure

For larger modules, use subshelves:

```python
from funcnodes_core import Shelf

from .math_nodes import add, subtract, multiply, divide
from .string_nodes import concat, split, upper, lower
from .io_nodes import read_file, write_file

NODE_SHELF = Shelf(
    name="My Module",
    description="Comprehensive utility nodes",
    subshelves=[
        Shelf(
            name="Math",
            description="Mathematical operations",
            nodes=[add, subtract, multiply, divide]
        ),
        Shelf(
            name="Strings",
            description="String manipulation",
            nodes=[concat, split, upper, lower]
        ),
        Shelf(
            name="I/O",
            description="File operations",
            nodes=[read_file, write_file]
        ),
    ]
)
```

### Best Practices

1. **Consistent naming**: Use lowercase with underscores for node_id
1. **Prefix with module name**: `funcnodes_mymodule.category.node_name`
1. **Group by function**: Math, I/O, Transforms, etc.
1. **Limit depth**: 2-3 levels of subshelves maximum
1. **Add descriptions**: Help users understand each shelf's purpose

______________________________________________________________________

## Advanced Node Patterns

### Nodes with Multiple Outputs

```python
from typing import Tuple

@fn.NodeDecorator(
    node_id="funcnodes_mymodule.divmod",
    name="Divmod",
    outputs=[
        {"name": "quotient"},
        {"name": "remainder"}
    ]
)
def divmod_node(a: int, b: int) -> Tuple[int, int]:
    """Return quotient and remainder of division."""
    return divmod(a, b)
```

### Nodes with Dynamic Options

```python
from funcnodes_core.io_hooks import update_other_io_options

@fn.NodeDecorator(node_id="funcnodes_mymodule.select_column")
@update_other_io_options("column", modifier=lambda df: df.columns.tolist())
def select_column(df: "pd.DataFrame", column: str) -> "pd.Series":
    """Select a column from a DataFrame."""
    return df[column]
```

### Nodes with Value Constraints

```python
@fn.NodeDecorator(
    node_id="funcnodes_mymodule.clamp",
    name="Clamp Value"
)
def clamp(
    value: float,
    min_val: float = 0.0,
    max_val: float = 1.0
) -> float:
    """Clamp a value to a range."""
    return max(min_val, min(max_val, value))

# Add constraints via class-based approach for more control
class ClampNode(fn.Node):
    node_id = "funcnodes_mymodule.clamp_v2"
    node_name = "Clamp (Advanced)"

    value = fn.NodeInput(id="value", type=float, default=0.5)
    min_val = fn.NodeInput(
        id="min_val",
        type=float,
        default=0.0,
        value_options={"max": 1.0}
    )
    max_val = fn.NodeInput(
        id="max_val",
        type=float,
        default=1.0,
        value_options={"min": 0.0}
    )
    result = fn.NodeOutput(id="result", type=float)

    async def func(self, value, min_val, max_val):
        self.outputs["result"].value = max(min_val, min(max_val, value))
```

### Async Nodes

```python
import aiohttp

@fn.NodeDecorator(node_id="funcnodes_mymodule.fetch_url")
async def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

### Heavy Computation Nodes

```python
@fn.NodeDecorator(
    node_id="funcnodes_mymodule.heavy_compute",
    separate_thread=True  # Run in thread pool
)
def heavy_compute(data: list) -> list:
    """CPU-intensive operation."""
    import time
    time.sleep(2)  # Simulating heavy work
    return [x * 2 for x in data]


@fn.NodeDecorator(
    node_id="funcnodes_mymodule.very_heavy",
    separate_process=True  # Run in separate process
)
def very_heavy_compute(data: list) -> list:
    """Very CPU-intensive operation (process isolation)."""
    # This runs in a completely separate process
    return expensive_operation(data)
```

### Nodes with Progress

```python
@fn.NodeDecorator(node_id="funcnodes_mymodule.process_items")
async def process_items(items: list, node: fn.Node = None) -> list:
    """Process items with progress reporting."""
    results = []
    for item in node.progress(items):
        results.append(await process_single(item))
    return results
```

______________________________________________________________________

## Custom Types and Rendering

### DataEnum for Dropdowns

```python
from funcnodes_core import DataEnum

class ColorMode(DataEnum):
    RGB = ("rgb", "RGB Color")
    HSV = ("hsv", "HSV Color")
    GRAYSCALE = ("gray", "Grayscale")

@fn.NodeDecorator(node_id="funcnodes_mymodule.convert_color")
def convert_color(image: "np.ndarray", mode: ColorMode = ColorMode.RGB) -> "np.ndarray":
    """Convert image color mode."""
    return do_conversion(image, mode.v())
```

### Custom Render Options

Register custom render options for your types:

```python
# In __init__.py
RENDER_OPTIONS = {
    "typemap": {
        "MyCustomType": "custom_renderer"
    },
    "inputconverter": {
        "MyCustomType": "custom_input"
    }
}
```

### Preview Rendering

Configure how node outputs are previewed:

```python
class ImageProcessorNode(fn.Node):
    node_id = "funcnodes_mymodule.image_processor"

    # Tell UI to render the 'output_image' as the preview
    default_render_options = {
        "data": {"src": "output_image"}
    }

    input_image = fn.NodeInput(id="input_image", type="np.ndarray")
    output_image = fn.NodeOutput(id="output_image", type="np.ndarray")
```

______________________________________________________________________

## Publishing Your Module

### 1. Prepare for Release

```bash
# Update version in pyproject.toml
# Write changelog
# Ensure tests pass
pytest
```

### 2. Build the Package

```bash
pip install build
python -m build
```

### 3. Publish to PyPI

```bash
pip install twine
twine upload dist/*
```

### 4. Register with funcnodes_repositories (Optional)

To appear in the official module list:

1. Fork [funcnodes_repositories](https://github.com/Linkdlab/funcnodes_repositories)
1. Add your module to `available_repositories.yaml`:

```yaml
funcnodes-mymodule:
  package: funcnodes-mymodule
  description: My awesome nodes
  category: utilities
```

1. Submit a pull request

______________________________________________________________________

## Testing Your Module

### Setup pytest-funcnodes

```bash
pip install funcnodes-pytest
```

### Write Node Tests

```python
# tests/test_nodes.py
import pytest
from funcnodes_pytest import nodetest, all_nodes_tested

from funcnodes_mymodule import NODE_SHELF
from funcnodes_mymodule.nodes import greet, sum_list, multiply


@nodetest
async def test_greet():
    node = greet()
    node.inputs["name"].value = "Alice"
    await node
    assert node.outputs["out"].value == "Hello, Alice!"


@nodetest
async def test_sum_list():
    node = sum_list()
    node.inputs["numbers"].value = [1, 2, 3, 4, 5]
    await node
    assert node.outputs["out"].value == 15


@nodetest
async def test_multiply():
    node = multiply()
    node.inputs["a"].value = 3.0
    node.inputs["b"].value = 4.0
    await node
    assert node.outputs["out"].value == 12.0


def test_all_nodes_covered(all_nodes):
    """Ensure all nodes in the shelf have tests."""
    all_nodes_tested(all_nodes, NODE_SHELF)
```

### Run Tests

```bash
# Run all tests
pytest

# Run only node tests
pytest --nodetests-only

# With coverage
pytest --cov=funcnodes_mymodule
```

See [Testing Modules](https://linkdlab.github.io/FuncNodes/v1.5.1/extending/testing-modules/index.md) for comprehensive testing guidance.

______________________________________________________________________

## React Plugin Development

For custom UI components (editors, previews, widgets), see [React Plugins](https://linkdlab.github.io/FuncNodes/v1.5.1/extending/react-plugins/index.md).

Quick overview:

```typescript
// react_plugin/src/index.tsx
import { FuncNodesReactPlugin } from "@linkdlab/funcnodes_react_flow";

const MyPlugin: FuncNodesReactPlugin = {
  renderNodeOutput: (props) => {
    if (props.type === "MyCustomType") {
      return <MyCustomPreview data={props.value} />;
    }
    return null;
  }
};

export default MyPlugin;
```

______________________________________________________________________

## Common Patterns

### File-Based Nodes

```python
from pathlib import Path

@fn.NodeDecorator(node_id="funcnodes_mymodule.read_json")
def read_json(filepath: str) -> dict:
    """Read a JSON file."""
    import json
    with open(filepath) as f:
        return json.load(f)
```

### Configuration Nodes

```python
from dataclasses import dataclass

@dataclass
class Config:
    threshold: float = 0.5
    max_iterations: int = 100

@fn.NodeDecorator(node_id="funcnodes_mymodule.create_config")
def create_config(
    threshold: float = 0.5,
    max_iterations: int = 100
) -> Config:
    """Create a configuration object."""
    return Config(threshold=threshold, max_iterations=max_iterations)
```

### Wrapper Nodes for External Libraries

```python
@fn.NodeDecorator(
    node_id="funcnodes_mymodule.sklearn_fit",
    name="Fit Model"
)
def fit_model(
    model: "sklearn.base.BaseEstimator",
    X: "np.ndarray",
    y: "np.ndarray"
) -> "sklearn.base.BaseEstimator":
    """Fit a scikit-learn model."""
    return model.fit(X, y)
```

______________________________________________________________________

## Checklist

Before publishing, ensure:

- [ ] All nodes have unique `node_id` with module prefix
- [ ] All nodes have `name` and `description`
- [ ] All inputs have type hints
- [ ] All outputs have type hints
- [ ] Shelf is properly organized
- [ ] Entry points are configured in `pyproject.toml`
- [ ] Tests cover all nodes
- [ ] README documents installation and usage
- [ ] Version follows semantic versioning

______________________________________________________________________

## See Also

- [React Plugins](https://linkdlab.github.io/FuncNodes/v1.5.1/extending/react-plugins/index.md) — Custom UI components
- [Testing Modules](https://linkdlab.github.io/FuncNodes/v1.5.1/extending/testing-modules/index.md) — Comprehensive testing guide
- [Creating Nodes](https://linkdlab.github.io/FuncNodes/v1.5.1/components/node/index.md) — Node fundamentals
- [Shelves](https://linkdlab.github.io/FuncNodes/v1.5.1/components/shelf/index.md) — Shelf organization
- [Available Modules](https://linkdlab.github.io/FuncNodes/v1.5.1/modules/index.md) — Official module examples
