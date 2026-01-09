# Serialization

FuncNodes uses a custom JSON serialization system to persist workflows, transfer data between workers, and render previews in the UI. This page covers the complete serialization API.

______________________________________________________________________

## Overview

The serialization system consists of:

| Component      | Purpose                                          |
| -------------- | ------------------------------------------------ |
| `JSONEncoder`  | Converts Python objects to JSON-compatible types |
| `JSONDecoder`  | Restores Python objects from JSON                |
| `ByteEncoder`  | Converts objects to binary data with MIME types  |
| `Encdata`      | Return type for JSON encoders                    |
| `BytesEncdata` | Return type for byte encoders                    |

______________________________________________________________________

## JSONEncoder

`JSONEncoder` extends Python's `json.JSONEncoder` with a registry of custom handlers.

### Basic Usage

```python
import json
from funcnodes_core.utils.serialization import JSONEncoder

# Encode an object
data = {"array": my_numpy_array, "figure": my_plotly_figure}
json_string = json.dumps(data, cls=JSONEncoder)

# Apply encoding without full JSON serialization
encoded = JSONEncoder.apply_custom_encoding(my_object, preview=False)
```

### The `preview` Parameter

Encoders receive a `preview` flag that indicates lightweight encoding for UI display:

- **`preview=False`** — Full serialization for persistence/transfer
- **`preview=True`** — Truncated/simplified output for UI previews

Built-in preview behaviors:

- Strings longer than 1000 characters are truncated with `...`
- Lists are limited to the first 10 items
- Large arrays may use simplified representations

______________________________________________________________________

## Registering Custom Encoders

### Simple Encoder (Tuple Return)

```python
from funcnodes_core.utils.serialization import JSONEncoder

def my_encoder(obj, preview=False):
    """Simple encoder returning (data, handled) tuple."""
    if isinstance(obj, MyCustomType):
        return obj.to_dict(), True  # (encoded_data, was_handled)
    return obj, False  # Not handled, pass to next encoder

JSONEncoder.add_encoder(my_encoder)
```

### Advanced Encoder (Encdata Return)

For more control, return an `Encdata` object:

```python
from funcnodes_core.utils.serialization import JSONEncoder, Encdata

def my_encoder(obj, preview=False):
    """Advanced encoder with Encdata control."""
    if isinstance(obj, MyCustomType):
        return Encdata(
            data=obj.to_dict(),
            handeled=True,
            done=False,           # Continue encoding nested objects
            continue_preview=None # Inherit preview setting
        )
    return Encdata(data=obj, handeled=False)

JSONEncoder.add_encoder(my_encoder)
```

### Encdata Parameters

| Parameter          | Type             | Description                                                                                                  |
| ------------------ | ---------------- | ------------------------------------------------------------------------------------------------------------ |
| `data`             | `Any`            | The encoded data                                                                                             |
| `handeled`         | `bool`           | Whether this encoder processed the object                                                                    |
| `done`             | `bool`           | If `True`, stop encoding (return data as-is). If `False`, continue encoding nested objects. Default: `False` |
| `continue_preview` | `Optional[bool]` | Override preview flag for nested encoding. `None` inherits current setting.                                  |

### Type-Specific Registration

Register encoders for specific types to improve performance:

```python
from pathlib import Path
from funcnodes_core.utils.serialization import JSONEncoder, Encdata

def path_encoder(obj, preview=False):
    if isinstance(obj, Path):
        return Encdata(data=obj.as_posix(), handeled=True)
    return Encdata(data=obj, handeled=False)

# Only called for Path objects (and subclasses)
JSONEncoder.add_encoder(path_encoder, enc_cls=[Path])
```

### Encoder Priority

Use `prepend_encoder` to add an encoder at the front of the queue (higher priority):

```python
# This encoder will be tried before others for the specified types
JSONEncoder.prepend_encoder(my_high_priority_encoder, enc_cls=[MyType])
```

______________________________________________________________________

## Real-World Encoder Examples

### NumPy Arrays

```python
import numpy as np
import funcnodes_core as fn

def numpy_encoder(obj, preview=False):
    if isinstance(obj, np.ndarray):
        if preview:
            # Simplified preview for UI
            return obj.tolist()[:10], True
        return obj.tolist(), True
    return obj, False

fn.JSONEncoder.add_encoder(numpy_encoder)
```

### Plotly Figures

```python
import plotly.graph_objects as go
import funcnodes_core as fn

def figure_encoder(figure: go.Figure, preview=False):
    if isinstance(figure, go.Figure):
        return fn.Encdata(
            data=figure.to_plotly_json(),
            handeled=True,
            done=False,              # Allow nested encoding
            continue_preview=False,  # Disable preview for nested data
        )
    return fn.Encdata(data=figure, handeled=False)

fn.JSONEncoder.add_encoder(figure_encoder, enc_cls=[go.Figure])
```

### Pydantic Models

```python
from pydantic import BaseModel
from funcnodes_core.utils.serialization import JSONEncoder, Encdata

def pydantic_encoder(obj, preview=False):
    if isinstance(obj, BaseModel):
        return Encdata(
            data=obj.model_dump(mode="json"),
            handeled=True,
            done=True,  # Already JSON-compatible
        )
    return Encdata(data=obj, handeled=False)

JSONEncoder.add_encoder(pydantic_encoder, enc_cls=[BaseModel])
```

______________________________________________________________________

## JSONDecoder

`JSONDecoder` restores Python objects from JSON using registered decoders.

### Basic Usage

```python
import json
from funcnodes_core.utils.serialization import JSONDecoder

# Decode JSON string
data = json.loads(json_string, cls=JSONDecoder)
```

### Registering Decoders

Decoders are called for each dict/value during parsing:

```python
from funcnodes_core.utils.serialization import JSONDecoder

def my_decoder(obj):
    """Decoder returning (result, handled) tuple."""
    if isinstance(obj, dict) and obj.get("__type__") == "MyCustomType":
        return MyCustomType.from_dict(obj), True
    return obj, False

JSONDecoder.add_decoder(my_decoder)
```

### Decoder Signature

```python
def decoder(obj: Any) -> Tuple[Any, bool]:
    """
    Args:
        obj: The JSON value (dict, list, str, int, float, bool, None)

    Returns:
        Tuple of (decoded_object, was_handled)
    """
```

______________________________________________________________________

## ByteEncoder

`ByteEncoder` converts objects to binary data with MIME types for efficient transfer.

### Basic Usage

```python
from funcnodes_core.utils.serialization import ByteEncoder

result = ByteEncoder.encode(my_object, preview=False)
# result.data: bytes
# result.mime: str (e.g., "application/json", "image/png")
# result.handeled: bool
```

### Registering Byte Encoders

```python
from funcnodes_core.utils.serialization import ByteEncoder, BytesEncdata

def image_byte_encoder(obj, preview=False):
    if isinstance(obj, MyImageType):
        return BytesEncdata(
            data=obj.to_png_bytes(),
            handeled=True,
            mime="image/png"
        )
    return BytesEncdata(data=obj, handeled=False)

ByteEncoder.add_encoder(image_byte_encoder, enc_cls=[MyImageType])
```

### BytesEncdata Parameters

| Parameter  | Type            | Description                               |
| ---------- | --------------- | ----------------------------------------- |
| `data`     | `bytes \| Any`  | The encoded binary data                   |
| `handeled` | `bool`          | Whether this encoder processed the object |
| `mime`     | `Optional[str]` | MIME type of the encoded data             |

### Built-in MIME Types

| Type          | MIME                       |
| ------------- | -------------------------- |
| `str`         | `text/plain`               |
| `bytes`       | `application/octet-stream` |
| `int`         | `application/fn.struct.!q` |
| `float`       | `application/fn.struct.!d` |
| `bool`        | `application/fn.struct.?`  |
| `None`        | `application/fn.null`      |
| JSON fallback | `application/json`         |

______________________________________________________________________

## Built-in Type Handlers

### Bytes

Bytes are Base64 encoded for JSON:

```python
import base64

# Encoding: bytes → base64 string
encoded = base64.b64encode(my_bytes).decode("utf-8")

# Built-in handler does this automatically
```

### Dataclasses

Dataclasses are automatically converted to dictionaries:

```python
from dataclasses import dataclass

@dataclass
class MyData:
    name: str
    value: int

# Automatically serializes to {"name": "...", "value": ...}
```

### Objects with `_repr_json_`

Objects implementing `_repr_json_()` method are automatically encoded:

```python
class MyType:
    def _repr_json_(self):
        """Return JSON-serializable representation."""
        return {"type": "MyType", "data": self._internal_data}
```

______________________________________________________________________

## Persistence Files

FuncNodes uses these files for persistence:

| File                 | Content                                       | Format  |
| -------------------- | --------------------------------------------- | ------- |
| `nodespace.json`     | Serialized graph state (nodes, edges, groups) | JSON    |
| `worker_<uuid>.json` | Worker configuration and metadata             | JSON    |
| `config.json`        | Global FuncNodes settings                     | JSON    |
| `io_values/`         | Large IO values stored separately             | Various |

### Nodespace Serialization

```python
# Save nodespace
nodespace.serialize()  # Returns dict
json.dumps(nodespace.serialize(), cls=JSONEncoder)

# Load nodespace
nodespace.deserialize(data)
```

### Node Serialization

```python
# Full serialization (for persistence)
node.full_serialize()

# Returns:
{
    "node_id": "my_node",
    "uuid": "abc123...",
    "io": [...],  # Serialized inputs/outputs
    "render_options": {...},
    "properties": {...}
}
```

______________________________________________________________________

## Performance Considerations

### Large Data

For large arrays or binary data:

1. **Use file references** instead of embedding data:

```python
# Instead of storing array in JSON
# Store path to file and load on demand
{"__file__": "data/large_array.npy"}
```

1. **Use ByteEncoder** for binary transfer (more efficient than Base64)
1. **Enable preview mode** for UI display to truncate large data

### Circular References

The encoder detects circular references and raises `ValueError`:

```python
# This will raise ValueError
a = {}
a["self"] = a
JSONEncoder.apply_custom_encoding(a)  # ValueError: Circular reference detected
```

### Encoder Ordering

- Register type-specific encoders with `enc_cls` for better performance
- Use `prepend_encoder` for high-priority handlers
- The encoder chain stops at the first handler that returns `handeled=True`

______________________________________________________________________

## Module Integration

### Registering Encoders in Modules

Add encoders in your module's `__init__.py`:

```python
# mymodule/__init__.py
import funcnodes_core as fn
from .types import MyCustomType

def my_encoder(obj, preview=False):
    if isinstance(obj, MyCustomType):
        return fn.Encdata(
            data={"__type__": "MyCustomType", **obj.to_dict()},
            handeled=True
        )
    return fn.Encdata(data=obj, handeled=False)

# Register when module is imported
fn.JSONEncoder.add_encoder(my_encoder, enc_cls=[MyCustomType])
```

### Render Options for Custom Types

Tell the UI how to display your type:

```python
FUNCNODES_RENDER_OPTIONS: fn.RenderOptions = {
    "typemap": {
        "mymodule.MyCustomType": "json",  # Render as JSON viewer
    },
    "inputconverter": {
        "mymodule.MyCustomType": "str_to_json",  # Parse JSON input
    },
}
```

______________________________________________________________________

## Complete Example

```python
import funcnodes_core as fn
from funcnodes_core.utils.serialization import (
    JSONEncoder, JSONDecoder, ByteEncoder,
    Encdata, BytesEncdata
)
from dataclasses import dataclass

@dataclass
class Measurement:
    timestamp: float
    values: list[float]
    unit: str

# JSON Encoder
def measurement_encoder(obj, preview=False):
    if isinstance(obj, Measurement):
        data = {
            "__type__": "Measurement",
            "timestamp": obj.timestamp,
            "values": obj.values[:10] if preview else obj.values,
            "unit": obj.unit,
        }
        return Encdata(data=data, handeled=True, done=True)
    return Encdata(data=obj, handeled=False)

JSONEncoder.add_encoder(measurement_encoder, enc_cls=[Measurement])

# JSON Decoder
def measurement_decoder(obj):
    if isinstance(obj, dict) and obj.get("__type__") == "Measurement":
        return Measurement(
            timestamp=obj["timestamp"],
            values=obj["values"],
            unit=obj["unit"]
        ), True
    return obj, False

JSONDecoder.add_decoder(measurement_decoder)

# Byte Encoder (for efficient binary transfer)
def measurement_byte_encoder(obj, preview=False):
    if isinstance(obj, Measurement):
        import json
        data = json.dumps({
            "timestamp": obj.timestamp,
            "values": obj.values,
            "unit": obj.unit,
        }).encode("utf-8")
        return BytesEncdata(data=data, handeled=True, mime="application/json")
    return BytesEncdata(data=obj, handeled=False)

ByteEncoder.add_encoder(measurement_byte_encoder, enc_cls=[Measurement])
```

______________________________________________________________________

## Best Practices

1. **Keep IO values serializable** — Use JSON-compatible types or register encoders
1. **Use `enc_cls` for type-specific encoders** — Improves performance by skipping irrelevant handlers
1. **Support preview mode** — Truncate large data for UI display
1. **Use `done=True` for terminal encodings** — When data is already JSON-compatible
1. **Avoid embedding large binary data** — Use file references or ByteEncoder
1. **Register decoders for round-trip support** — Ensure deserialization works correctly
1. **Handle edge cases** — `None`, empty collections, `NaN` values

______________________________________________________________________

## See Also

- [Nodespace](https://linkdlab.github.io/FuncNodes/v1.5.1/components/nodespace/index.md) — Graph state and persistence
- [Inputs & Outputs](https://linkdlab.github.io/FuncNodes/v1.5.1/components/inputs-outputs/index.md) — IO serialization
- [Writing Modules](https://linkdlab.github.io/FuncNodes/v1.5.1/extending/writing-modules/index.md) — Module development
