import json
from typing import Any, Optional


def _parse_command_value(value: str) -> Any:
    """Parse a string value into its appropriate Python type."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass

    lowered = value.lower()
    if lowered in ("true", "false"):
        return lowered == "true"

    if lowered in ("none", "null"):
        return None

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    return value


def parse_command_kwargs(argv: Optional[list[str]]) -> dict[str, Any]:
    """Parse command-line arguments into a kwargs dictionary."""
    if not argv:
        return {}

    kwargs: dict[str, Any] = {}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--":
            i += 1
            continue

        if not token.startswith("--") or token == "--":
            raise ValueError(f"Unexpected argument: {token}")

        key_with_value = token[2:]
        if not key_with_value:
            raise ValueError("Unexpected argument: --")

        if "=" in key_with_value:
            key, value = key_with_value.split("=", 1)
            kwargs[key] = _parse_command_value(value)
            i += 1
            continue

        key = key_with_value
        if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            kwargs[key] = _parse_command_value(argv[i + 1])
            i += 2
            continue

        kwargs[key] = True
        i += 1

    return kwargs
