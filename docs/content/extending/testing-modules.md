# Testing FuncNodes Modules

This guide covers testing strategies for FuncNodes modules using `pytest_funcnodes` — the official testing plugin that provides decorators, fixtures, and utilities for comprehensive node testing.

---

## Setup

### Install pytest_funcnodes

```bash
pip install pytest-funcnodes
```

### Project Structure

```
funcnodes_mymodule/
├── src/funcnodes_mymodule/
│   ├── __init__.py
│   └── nodes.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_nodes.py
│   └── test_all_nodes_pytest.py
├── pyproject.toml
└── pytest.ini
```

### Configure pytest

Create `pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
testpaths = tests
python_files = test_*.py
python_functions = test_*
```

Or in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
```

---

## Two Testing Decorators

The plugin provides two main decorators:

| Decorator                                             | Purpose                                           | Sync/Async |
| ----------------------------------------------------- | ------------------------------------------------- | ---------- |
| `@nodetest(NodeClass)` or `@nodetest([Node1, Node2])` | Test specific node classes with coverage tracking | Async only |
| `@funcnodes_test`                                     | General FuncNodes testing with isolated context   | Both       |

---

## The `@nodetest` Decorator

Use `@nodetest` to mark async tests that test specific node classes. **The decorator takes a node class or list of node classes** to track test coverage.

### Signature

```python
@nodetest(node: Union[None, Type[Node], List[Type[Node]]] = None)
```

### Basic Usage

```python
from pytest_funcnodes import nodetest
import funcnodes_core as fn

@fn.NodeDecorator("my_module.add")
def add_numbers(a: int, b: int) -> int:
    return a + b

# Pass a single node CLASS to @nodetest for coverage tracking
@nodetest(add_numbers)
async def test_add_numbers():
    node = add_numbers()  # Create instance

    node.inputs["a"].value = 5
    node.inputs["b"].value = 3

    await node

    assert node.outputs["out"].value == 8
```

### What `@nodetest` Does

1. **Registers node for coverage** — The `NodeClass` argument is added to `session.tested_nodes`
2. **Applies markers** — Adds `@pytest.mark.nodetest` and `@pytest.mark.asyncio`
3. **Isolates environment** — Wraps test in `test_context()` for clean state
4. **Sets temp config dir** — Uses isolated `FUNCNODES_CONFIG_DIR` in temp folder

### Testing Multiple Node Classes

Pass a **list** of node classes to track coverage for multiple nodes in one test:

```python
from pytest_funcnodes import nodetest

# Test multiple related nodes - pass list of classes
@nodetest([add_numbers, multiply_numbers])
async def test_math_operations():
    add_node = add_numbers()
    mult_node = multiply_numbers()

    add_node.inputs["a"].value = 2
    add_node.inputs["b"].value = 3
    await add_node
    assert add_node.outputs["out"].value == 5

    mult_node.inputs["a"].value = 4
    mult_node.inputs["b"].value = 2
    await mult_node
    assert mult_node.outputs["out"].value == 8
```

Both `add_numbers` and `multiply_numbers` will be marked as tested for coverage tracking.

### Without Coverage Tracking

If you don't need coverage tracking, use empty `@nodetest()`:

```python
@nodetest()
async def test_node_behavior():
    # Test won't be counted toward coverage
    node = some_node()
    await node
```

---

## The `@funcnodes_test` Decorator

Use `@funcnodes_test` for general FuncNodes testing. It works with both sync and async functions and accepts configuration options.

### Basic Usage

```python
from pytest_funcnodes import funcnodes_test

# Async test
@funcnodes_test
async def test_async_operation():
    node = my_node()
    await node
    assert node.outputs["out"].value is not None

# Sync test (also works!)
@funcnodes_test
def test_sync_operation():
    node = my_node()
    assert "input1" in node.inputs
```

### With Configuration Options

Pass keyword arguments to customize the test context:

```python
@funcnodes_test(
    clear=True,           # Clear temp directory before test
    no_prefix=False,      # Use unique prefix for isolation
    disable_file_handler=True,  # Disable file logging
    fail_on_warnings=[FuncNodesDeprecationWarning],  # Fail on these warnings
)
async def test_with_options():
    node = my_node()
    await node
```

### Available Options

| Option                 | Type   | Default                         | Description                                  |
| ---------------------- | ------ | ------------------------------- | -------------------------------------------- |
| `clear`                | `bool` | `True`                          | Clear config directory before test           |
| `no_prefix`            | `bool` | `False`                         | If `True`, use fixed temp dir (not isolated) |
| `disable_file_handler` | `bool` | `True`                          | Disable file logging handler                 |
| `config`               | `dict` | `None`                          | Custom FuncNodes config to apply             |
| `fail_on_warnings`     | `list` | `[FuncNodesDeprecationWarning]` | Warning types that fail tests                |

---

## Coverage Testing with `all_nodes_tested`

### How Coverage Tracking Works

1. Decorate tests with `@nodetest(NodeClass)` to register tested nodes
2. The `all_nodes` fixture collects all registered node classes
3. Call `all_nodes_tested(all_nodes, shelf)` to verify complete coverage

### Complete Example

```python
# tests/test_all_nodes_pytest.py
from pytest_funcnodes import all_nodes_tested
import funcnodes_mymodule as fnmodule

def test_all_nodes_tested(all_nodes):
    """Ensure every node in the shelf has at least one test."""
    all_nodes_tested(all_nodes, fnmodule.NODE_SHELF)
```

### The `all_nodes` Fixture

The `all_nodes` fixture is a **set of node classes** (not instances) that have been passed to `@nodetest()`:

```python
# This fixture is automatically provided by pytest_funcnodes
@pytest.fixture(scope="session", autouse=True)
def all_nodes(request):
    return request.session.tested_nodes  # Set of node classes
```

### `all_nodes_tested` Function Signature

```python
def all_nodes_tested(
    tested_nodes: List[Type[fn.Node]],  # From all_nodes fixture
    shelf: fn.Shelf,                     # Shelf to check coverage
    ignore: Optional[List[Union[Type[fn.Node], fn.Shelf]]] = None,  # Skip these
):
```

### Ignoring Nodes or Shelves

You can ignore specific nodes or entire shelves:

```python
def test_all_nodes_tested(all_nodes):
    all_nodes_tested(
        all_nodes,
        fnmodule.NODE_SHELF,
        ignore=[
            fnmodule.deprecated_node,      # Ignore single node class
            fnmodule.EXPERIMENTAL_SHELF,   # Ignore entire shelf
        ]
    )
```

---

## Test Context and Isolation

### What `test_context()` Does

Every `@nodetest` and `@funcnodes_test` test runs inside a `test_context()` that:

1. **Creates temp config directory** — `{tempdir}/funcnodes_test_{pid}_{uuid}/`
2. **Isolates state** — Fresh config, logging, and node registry
3. **Cleans up after** — Removes temp directory and clears registered nodes

### Manual Test Context

For custom test scenarios:

```python
from pytest_funcnodes import test_context

def test_manual_context():
    with test_context(clear=True, config={"logging": {"level": "DEBUG"}}):
        # Test code runs in isolated environment
        node = my_node()
        # ...
    # Context is cleaned up automatically
```

### Checking Test Mode

```python
from pytest_funcnodes import get_in_test

def test_check_mode():
    assert get_in_test() is True  # Inside test context
```

---

## Testing Patterns

### Testing Node Structure

```python
@funcnodes_test
def test_node_structure():
    node = my_node()

    # Check inputs exist
    assert "input1" in node.inputs
    assert "input2" in node.inputs

    # Check outputs exist
    assert "result" in node.outputs

    # Check default values
    assert node.inputs["threshold"].value == 0.5
```

### Testing Node Execution

```python
@nodetest(process_data)
async def test_process_data():
    node = process_data()

    node.inputs["data"].value = [1, 2, 3, 4, 5]
    node.inputs["operation"].value = "sum"

    await node

    assert node.outputs["result"].value == 15
```

### Testing Multiple Cases

```python
@nodetest(add_numbers)
async def test_add_numbers_cases():
    node = add_numbers()

    test_cases = [
        (1, 2, 3),
        (0, 0, 0),
        (-5, 5, 0),
        (1.5, 2.5, 4.0),
    ]

    for a, b, expected in test_cases:
        node.inputs["a"].value = a
        node.inputs["b"].value = b
        await node
        assert node.outputs["out"].value == expected, f"Failed for {a} + {b}"
```

### Testing Error Handling

```python
import pytest

@nodetest(divide)
async def test_division_by_zero():
    node = divide()
    node.inputs["a"].value = 10
    node.inputs["b"].value = 0

    with pytest.raises(ZeroDivisionError):
        await node
```

### Testing Dynamic IO Updates

```python
@nodetest(column_selector)
async def test_dynamic_options():
    import pandas as pd

    node = column_selector()
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})

    node.inputs["dataframe"].value = df

    # Check that column options are updated
    options = node.inputs["column"].value_options.get("options", [])
    assert "a" in options
    assert "b" in options
    assert "c" in options
```

### Testing Node Chains

```python
import funcnodes_core as fn

@funcnodes_test
async def test_node_chain():
    # Create connected nodes
    add = add_numbers()
    mult = multiply_numbers()

    # Connect output to input
    add.outputs["out"].connect(mult.inputs["a"])

    # Set values
    add.inputs["a"].value = 2
    add.inputs["b"].value = 3
    mult.inputs["b"].value = 4

    # Wait for execution cascade
    await fn.run_until_complete(add, mult)

    # Result: (2+3) * 4 = 20
    assert mult.outputs["out"].value == 20
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_nodes.py

# Run specific test
pytest tests/test_nodes.py::test_add_numbers
```

### Node Tests Only

```bash
# Run only tests marked with @nodetest
pytest --nodetests-only
```

### With Coverage

```bash
# Install coverage
pip install pytest-cov

# Run with coverage report
pytest --cov=funcnodes_mymodule --cov-report=html
```

---

## Complete Test File Example

```python
# tests/test_nodes.py
import pytest
from pytest_funcnodes import nodetest, funcnodes_test

# Import your module
from funcnodes_mymodule import add_numbers, multiply_numbers, divide

# Test specific node with coverage tracking
@nodetest(add_numbers)
async def test_add_numbers():
    node = add_numbers()
    node.inputs["a"].value = 5
    node.inputs["b"].value = 3
    await node
    assert node.outputs["out"].value == 8

@nodetest(multiply_numbers)
async def test_multiply_numbers():
    node = multiply_numbers()
    node.inputs["a"].value = 4
    node.inputs["b"].value = 7
    await node
    assert node.outputs["out"].value == 28

@nodetest(divide)
async def test_divide():
    node = divide()
    node.inputs["a"].value = 10
    node.inputs["b"].value = 2
    await node
    assert node.outputs["out"].value == 5

@nodetest(divide)
async def test_divide_by_zero():
    node = divide()
    node.inputs["a"].value = 10
    node.inputs["b"].value = 0
    with pytest.raises(ZeroDivisionError):
        await node
```

```python
# tests/test_all_nodes_pytest.py
from pytest_funcnodes import all_nodes_tested
import funcnodes_mymodule as fnmodule

def test_all_nodes_tested(all_nodes):
    """Verify all nodes in the shelf have tests."""
    all_nodes_tested(all_nodes, fnmodule.NODE_SHELF, ignore=[])
```

---

## Best Practices

### Do

✅ Use `@nodetest(NodeClass)` to track coverage
✅ Create a `test_all_nodes_pytest.py` for coverage verification
✅ Test both happy path and error cases
✅ Use `@funcnodes_test` for sync tests and general utilities
✅ Test dynamic IO updates and value_options changes

### Don't

❌ Use `@nodetest()` without the node class (no coverage tracking)
❌ Forget to pass node classes to `@nodetest` decorator
❌ Skip the `all_nodes_tested` check in CI
❌ Test implementation details instead of behavior
❌ Use real network calls in unit tests

---

## Troubleshooting

### "Already in test mode" Error

```python
# Wrong: nested test contexts
@funcnodes_test
async def test_outer():
    with test_context():  # Error!
        pass

# Right: let decorator handle context
@funcnodes_test
async def test_correct():
    # No manual test_context needed
    pass
```

### Coverage Shows Missing Nodes

Make sure you pass the node **class** (not instance) to `@nodetest`:

```python
# Wrong: passing instance
@nodetest(add_numbers())  # Creates instance - won't track!
async def test_wrong():
    pass

# Right: passing single class
@nodetest(add_numbers)  # Pass the class itself
async def test_correct():
    node = add_numbers()  # Create instance inside
    pass

# Right: passing list of classes
@nodetest([add_numbers, multiply_numbers])  # Pass list of classes
async def test_multiple():
    pass
```

### Tests Not Isolated

Ensure you're using the decorators, not running tests without them:

```python
# Wrong: no isolation
async def test_no_isolation():  # Missing decorator!
    pass

# Right: proper isolation
@funcnodes_test
async def test_isolated():
    pass
```

---

## See Also

- [Writing Modules](writing-modules.md) — Complete module guide
- [React Plugins](react-plugins.md) — UI plugin testing
- [Creating Nodes](../components/node.md) — Node fundamentals
