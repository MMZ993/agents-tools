from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from agents_tools.app import create_app
from agents_tools.config import load_policies
from agents_tools.tools import discover_tools


async def test_http_mcp_discovery_is_isolated_by_bearer_principal() -> None:
    fixtures = Path(__file__).parent / "fixtures"
    app = create_app(
        principal_tokens={"calculator": "calculator-token", "reader": "reader-token"},
        policies=load_policies(fixtures / "policies"),
        tools=discover_tools(fixtures / "tools"),
    )

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            headers={"Authorization": "Bearer reader-token"},
        ) as http_client:
            async with streamable_http_client(
                "http://testserver/mcp/", http_client=http_client
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    denied_result = await session.call_tool(
                        "calc_add", {"left": 1, "right": 2}
                    )

    assert [tool.name for tool in tools.tools] == ["static_text"]
    assert denied_result.isError


async def test_http_mcp_rejects_arguments_outside_tool_schema() -> None:
    fixtures = Path(__file__).parent / "fixtures"
    app = create_app(
        principal_tokens={"calculator": "calculator-token"},
        policies=load_policies(fixtures / "policies"),
        tools=discover_tools(fixtures / "tools"),
    )

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            headers={"Authorization": "Bearer calculator-token"},
        ) as http_client:
            async with streamable_http_client(
                "http://testserver/mcp/", http_client=http_client
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    allowed_result = await session.call_tool(
                        "calc_add", {"left": 1, "right": 2}
                    )
                    result = await session.call_tool(
                        "calc_add", {"left": "bad", "right": 2}
                    )

    assert not allowed_result.isError
    assert result.isError
