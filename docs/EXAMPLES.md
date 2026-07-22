# Examples

This document provides minimal tool, policy, and principal-token examples for a broker deployment.

## Tool module

Deploy this module as `/tools/status/tool.py` before starting or restarting the broker:

```python
from agents_tools.models import ToolDefinition


async def status(_: dict[str, object]) -> str:
    return "ok"


def register() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            tool_id="status_read",
            description="Return the service status.",
            input_schema={"type": "object", "additionalProperties": False},
            handler=status,
            redact_fields=frozenset(),
        )
    ]
```

## Principal policy

Deploy this non-secret policy as `/policies/status-reader.yaml`:

```yaml
principal: status-reader
allow:
  - status_read
deny: []
```

## Principal bearer token

Deployment automation must render this file as `/run/secrets/tokens.yml` with mode `0600`. Replace the placeholder with a unique token from a secret manager; never commit a real token.

```yaml
principals:
  status-reader: REPLACE_WITH_A_SECRET_MANAGER_TOKEN
```

The client sends the token in the `Authorization: Bearer <token>` header.

## References

- [External tool contract](TOOLS.md)
- [Principal and policy contract](PRINCIPALS.md)
- [Broker runtime](RUNTIME.md)
