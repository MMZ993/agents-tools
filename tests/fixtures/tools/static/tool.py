from agents_tools.models import ToolDefinition


async def static_text(_: dict[str, object]) -> str:
    return "fixture text"


def register() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            tool_id="static_text",
            description="Return static fixture text.",
            input_schema={"type": "object", "additionalProperties": False},
            handler=static_text,
        )
    ]
