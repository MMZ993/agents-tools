from __future__ import annotations

from dataclasses import dataclass

from agents_tools.models import ToolDefinition


@dataclass(frozen=True, slots=True)
class _Credentials:
    api_key: str


_CREDENTIALS = _Credentials(api_key="fixture")


async def configured_text(_: dict[str, object]) -> str:
    return _CREDENTIALS.api_key


def register() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            tool_id="dataclass_configured",
            description="Return a value configured with dataclass credentials.",
            input_schema={"type": "object", "additionalProperties": False},
            handler=configured_text,
        )
    ]
