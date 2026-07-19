# External Tool Contract

This document defines the portable contract for a tool module mounted into the broker at deployment time.

## Location and lifecycle

Deploy each tool as `/tools/<name>/tool.py` before starting or restarting the broker container. The mount is read-only to the broker. Tool discovery happens once during startup; changing tool code requires a container restart.

## Module contract

Every `tool.py` exports `register()` returning a list of `ToolDefinition` instances:

```python
from agents_tools.models import ToolDefinition


async def read_status(_: dict[str, object]) -> str:
    return "ok"


def register() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            tool_id="example_status",
            description="Return service status.",
            input_schema={"type": "object", "additionalProperties": False},
            handler=read_status,
            redact_fields=frozenset(),
        )
    ]
```

`handler` must be asynchronous and receives validated agent-supplied arguments as a dictionary. It returns a value that the broker serializes as MCP text content. `input_schema` is the JSON Schema object published to MCP clients.

## Tool IDs

Use lowercase underscore namespaces, for example `mail_read` or `calendar_events`. IDs must be unique across every mounted tool. Duplicate IDs, invalid definitions, missing `register()`, or import failures prevent broker startup.

## Secrets and audit fields

Provider credentials belong inside tool implementation or its deployment-provided runtime environment; they are never agent arguments. Never log credentials, bearer tokens, passwords, or provider secrets. Set `redact_fields` to each sensitive top-level agent-supplied argument name. Schemas must set `additionalProperties: false` and each declared argument must use a primitive JSON Schema type; nested agent arguments are not accepted.

## References

- [RUNTIME.md](RUNTIME.md)
- [PRINCIPALS.md](PRINCIPALS.md)
