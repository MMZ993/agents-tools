from agents_tools.models import ToolDefinition


async def subtract(arguments: dict[str, object]) -> int:
    left = arguments["left"]
    right = arguments["right"]
    if not isinstance(left, int) or not isinstance(right, int):
        raise ValueError("left and right must be integers")
    return left - right


def register() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            tool_id="calc_sub",
            description="Subtract fixture integers.",
            input_schema={
                "type": "object",
                "properties": {
                    "left": {"type": "integer"},
                    "right": {"type": "integer"},
                },
                "required": ["left", "right"],
                "additionalProperties": False,
            },
            handler=subtract,
        )
    ]
