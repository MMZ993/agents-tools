import mcp.types as mcp_types

from agents_tools.app import _create_server
from agents_tools.models import ToolDefinition
from agents_tools.policy import Policy


async def _add(_: dict[str, object]) -> int:
    return 3


async def _raise_secret(arguments: dict[str, object]) -> None:
    raise RuntimeError(f"provider rejected {arguments['token']}")


class _ResultWithBrokenString:
    def __str__(self) -> str:
        raise RuntimeError("provider secret")


async def _return_unserializable_result(
    _: dict[str, object],
) -> _ResultWithBrokenString:
    return _ResultWithBrokenString()


async def test_handler_exception_returns_generic_mcp_error_without_raising() -> None:
    server = _create_server(
        "calculator",
        Policy("calculator", ("calc_add",), ()),
        {
            "calc_add": ToolDefinition(
                tool_id="calc_add",
                description="Add.",
                input_schema={
                    "type": "object",
                    "properties": {"token": {"type": "string"}},
                    "additionalProperties": False,
                },
                handler=_raise_secret,
                redact_fields=frozenset({"token"}),
            )
        },
    )

    result = await server.request_handlers[mcp_types.CallToolRequest](
        mcp_types.CallToolRequest(
            method="tools/call",
            params=mcp_types.CallToolRequestParams(
                name="calc_add", arguments={"token": "secret"}
            ),
        )
    )

    assert isinstance(result.root, mcp_types.CallToolResult)
    assert result.root.isError
    assert isinstance(result.root.content[0], mcp_types.TextContent)
    assert result.root.content[0].text == "tool invocation failed"


async def test_result_serialization_failure_returns_generic_mcp_error() -> None:
    server = _create_server(
        "calculator",
        Policy("calculator", ("calc_add",), ()),
        {
            "calc_add": ToolDefinition(
                tool_id="calc_add",
                description="Add.",
                input_schema={"type": "object", "additionalProperties": False},
                handler=_return_unserializable_result,
            )
        },
    )

    result = await server.request_handlers[mcp_types.CallToolRequest](
        mcp_types.CallToolRequest(
            method="tools/call",
            params=mcp_types.CallToolRequestParams(name="calc_add", arguments={}),
        )
    )

    assert isinstance(result.root, mcp_types.CallToolResult)
    assert result.root.isError
    assert isinstance(result.root.content[0], mcp_types.TextContent)
    assert result.root.content[0].text == "tool invocation failed"


async def test_successful_invocation_logs_arguments_only_at_debug_with_redaction(
    monkeypatch,
) -> None:
    info_records: list[dict[str, object]] = []
    debug_records: list[dict[str, object]] = []
    monkeypatch.setattr(
        "agents_tools.app.audit_event",
        lambda _event, **fields: info_records.append(fields),
    )
    monkeypatch.setattr(
        "agents_tools.app.audit_debug",
        lambda _event, **fields: debug_records.append(fields),
    )
    server = _create_server(
        "calculator",
        Policy("calculator", ("calc_add",), ()),
        {
            "calc_add": ToolDefinition(
                tool_id="calc_add",
                description="Add.",
                input_schema={
                    "type": "object",
                    "properties": {"token": {"type": "string"}},
                    "additionalProperties": False,
                },
                handler=_add,
                redact_fields=frozenset({"token"}),
            )
        },
    )

    await server.request_handlers[mcp_types.CallToolRequest](
        mcp_types.CallToolRequest(
            method="tools/call",
            params=mcp_types.CallToolRequestParams(
                name="calc_add", arguments={"token": "secret"}
            ),
        )
    )

    assert info_records == [
        {"principal": "calculator", "tool": "calc_add", "outcome": "allowed"}
    ]
    assert debug_records == [
        {
            "principal": "calculator",
            "tool": "calc_add",
            "arguments": {"token": "[REDACTED]"},
        }
    ]


async def test_list_tools_excludes_tools_denied_by_principal_policy() -> None:
    server = _create_server(
        "calculator",
        Policy(principal="calculator", allow=("calc_*",), deny=("calc_sub",)),
        {
            "calc_add": ToolDefinition(
                tool_id="calc_add",
                description="Add.",
                input_schema={"type": "object", "additionalProperties": False},
                handler=_add,
            ),
            "calc_sub": ToolDefinition(
                tool_id="calc_sub",
                description="Subtract.",
                input_schema={"type": "object", "additionalProperties": False},
                handler=_add,
            ),
        },
    )

    result = await server.request_handlers[mcp_types.ListToolsRequest](
        mcp_types.ListToolsRequest(method="tools/list")
    )

    assert isinstance(result.root, mcp_types.ListToolsResult)
    assert [tool.name for tool in result.root.tools] == ["calc_add"]
