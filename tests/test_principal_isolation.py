import mcp.types as mcp_types
from mcp.server import Server

from agents_tools.app import _create_server
from agents_tools.models import ToolDefinition
from agents_tools.policy import Policy


async def _fixture_handler(_: dict[str, object]) -> str:
    return "ok"


async def _listed_tool_names(server: Server) -> list[str]:
    result = await server.request_handlers[mcp_types.ListToolsRequest](
        mcp_types.ListToolsRequest(method="tools/list")
    )
    assert isinstance(result.root, mcp_types.ListToolsResult)
    return [tool.name for tool in result.root.tools]


async def test_principals_receive_distinct_mcp_tool_sets() -> None:
    tools = {
        "calc_add": ToolDefinition(
            tool_id="calc_add",
            description="Add.",
            input_schema={"type": "object", "additionalProperties": False},
            handler=_fixture_handler,
        ),
        "static_text": ToolDefinition(
            tool_id="static_text",
            description="Static.",
            input_schema={"type": "object", "additionalProperties": False},
            handler=_fixture_handler,
        ),
    }
    calculator_server = _create_server(
        "calculator", Policy("calculator", ("calc_*",), ()), tools
    )
    reader_server = _create_server(
        "reader", Policy("reader", ("static_text",), ()), tools
    )

    assert await _listed_tool_names(calculator_server) == ["calc_add"]
    assert await _listed_tool_names(reader_server) == ["static_text"]
