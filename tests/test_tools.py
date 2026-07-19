from pathlib import Path
from typing import cast

import pytest

from agents_tools.models import ToolDefinition
from agents_tools.tools import ToolRegistrationError, discover_tools


async def _handler(_: dict[str, object]) -> None:
    return None


def test_tool_definition_rejects_non_string_description() -> None:
    with pytest.raises(TypeError, match="description"):
        ToolDefinition(
            tool_id="example_status",
            description=cast(str, 1),
            input_schema={"type": "object", "additionalProperties": False},
            handler=_handler,
        )


def test_tool_definition_rejects_redaction_of_undeclared_argument() -> None:
    with pytest.raises(ValueError, match="redact_fields"):
        ToolDefinition(
            tool_id="example_status",
            description="Return status.",
            input_schema={
                "type": "object",
                "properties": {"token": {"type": "string"}},
                "additionalProperties": False,
            },
            handler=_handler,
            redact_fields=frozenset({"unknown"}),
        )


def test_tool_definition_rejects_nested_agent_argument_schema() -> None:
    with pytest.raises(ValueError, match="flat top-level"):
        ToolDefinition(
            tool_id="example_status",
            description="Return status.",
            input_schema={
                "type": "object",
                "properties": {"payload": {"type": "object"}},
                "additionalProperties": False,
            },
            handler=_handler,
        )


def test_tool_definition_rejects_malformed_draft_2020_12_schema() -> None:
    with pytest.raises(ValueError, match="input_schema is invalid"):
        ToolDefinition(
            tool_id="example_status",
            description="Return status.",
            input_schema={
                "type": "object",
                "required": 1,
                "additionalProperties": False,
            },
            handler=_handler,
        )


def test_discover_tools_loads_explicit_registrations(tmp_path: Path) -> None:
    tool_file = tmp_path / "calculator" / "tool.py"
    tool_file.parent.mkdir()
    tool_file.write_text(
        """
from agents_tools.models import ToolDefinition


async def add(arguments: dict[str, object]) -> int:
    return int(arguments[\"left\"]) + int(arguments[\"right\"])


def register() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            tool_id=\"calc_add\",
            description=\"Add two numbers.\",
            input_schema={\"type\": \"object\", \"additionalProperties\": False},
            handler=add,
        )
    ]
""".strip()
    )

    tools = discover_tools(tmp_path)

    assert list(tools) == ["calc_add"]


def test_discover_tools_rejects_duplicate_tool_ids(tmp_path: Path) -> None:
    for name in ("first", "second"):
        tool_file = tmp_path / name / "tool.py"
        tool_file.parent.mkdir()
        tool_file.write_text(
            """
from agents_tools.models import ToolDefinition


async def handler(arguments: dict[str, object]) -> str:
    return "ok"


def register() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            "duplicate",
            "Duplicate.",
            {"type": "object", "additionalProperties": False},
            handler,
        )
    ]
""".strip()
        )

    with pytest.raises(ToolRegistrationError, match="duplicate tool ID"):
        discover_tools(tmp_path)


def test_discover_tools_rejects_module_without_register_contract(
    tmp_path: Path,
) -> None:
    tool_file = tmp_path / "invalid" / "tool.py"
    tool_file.parent.mkdir()
    tool_file.write_text("value = 1\n")

    with pytest.raises(ToolRegistrationError, match="must expose register"):
        discover_tools(tmp_path)
