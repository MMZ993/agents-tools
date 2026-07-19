"""Starlette host for principal-isolated MCP streamable HTTP servers."""

from collections.abc import AsyncIterator, Mapping
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

import jsonschema
import mcp.types as mcp_types
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from prometheus_client import make_asgi_app
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from agents_tools.auth import authenticate
from agents_tools.logging import audit_debug, audit_event, redact_arguments
from agents_tools.metrics import record_authentication, record_invocation
from agents_tools.models import ToolDefinition
from agents_tools.policy import Policy


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Require a valid bearer token for every MCP request."""

    def __init__(self, app: ASGIApp, principal_tokens: Mapping[str, str]) -> None:
        super().__init__(app)
        self.principal_tokens = principal_tokens

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if request.url.path in {"/healthz", "/metrics", "/metrics/"}:
            return await call_next(request)
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        principal = (
            authenticate(token, self.principal_tokens) if scheme == "Bearer" else None
        )
        if principal is None:
            record_authentication("unknown", "denied")
            audit_event("authentication", outcome="denied")
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
        record_authentication(principal, "allowed")
        audit_event("authentication", principal=principal, outcome="allowed")
        request.scope["principal"] = principal
        return await call_next(request)


class PrincipalMcpEndpoint:
    """Dispatch one authenticated HTTP request to its principal's MCP manager."""

    def __init__(self, managers: Mapping[str, StreamableHTTPSessionManager]) -> None:
        self.managers = managers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        principal = scope.get("principal")
        manager = self.managers.get(principal) if isinstance(principal, str) else None
        if manager is None:
            response = JSONResponse({"detail": "unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return
        await manager.handle_request(scope, receive, send)


def create_app(
    *,
    principal_tokens: Mapping[str, str],
    policies: Mapping[str, Policy],
    tools: Mapping[str, ToolDefinition],
) -> Starlette:
    """Create a broker with an in-memory MCP server isolated per principal."""
    managers = {
        principal: StreamableHTTPSessionManager(
            _create_server(principal, policies.get(principal), tools),
            json_response=True,
        )
        for principal in principal_tokens
    }

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            for manager in managers.values():
                await stack.enter_async_context(manager.run())
            yield

    return Starlette(
        routes=[
            Route("/healthz", lambda _: JSONResponse({"status": "ok"})),
            Mount("/metrics", app=make_asgi_app()),
            Mount("/mcp", app=PrincipalMcpEndpoint(managers)),
        ],
        lifespan=lifespan,
        middleware=[
            Middleware(AuthenticationMiddleware, principal_tokens=principal_tokens),
        ],
    )


def _create_server(
    principal: str, policy: Policy | None, tools: Mapping[str, ToolDefinition]
) -> Server:
    server = Server(f"agents-tools-{principal}")
    allowed_tools = {
        tool_id: definition
        for tool_id, definition in tools.items()
        if policy is not None and policy.permits(tool_id)
    }

    @server.list_tools()
    async def list_tools() -> list[mcp_types.Tool]:
        return [
            mcp_types.Tool(
                name=definition.tool_id,
                description=definition.description,
                inputSchema=dict(definition.input_schema),
            )
            for definition in allowed_tools.values()
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict[str, object]
    ) -> mcp_types.CallToolResult:
        definition = allowed_tools.get(name)
        if definition is None or policy is None or not policy.permits(name):
            record_invocation(principal, "unknown", "denied")
            audit_event(
                "tool_invocation", principal=principal, tool=name, outcome="denied"
            )
            return mcp_types.CallToolResult(
                content=[mcp_types.TextContent(type="text", text="tool access denied")],
                isError=True,
            )
        redacted_arguments = redact_arguments(arguments, definition.redact_fields)
        try:
            jsonschema.validate(arguments, definition.input_schema)
        except jsonschema.ValidationError:
            record_invocation(principal, name, "denied")
            audit_event(
                "tool_invocation", principal=principal, tool=name, outcome="denied"
            )
            return mcp_types.CallToolResult(
                content=[
                    mcp_types.TextContent(type="text", text="invalid tool arguments")
                ],
                isError=True,
            )
        try:
            result = await definition.handler(arguments)
            serialized_result = str(result)
        except Exception:
            record_invocation(principal, name, "error")
            audit_event(
                "tool_invocation", principal=principal, tool=name, outcome="error"
            )
            return mcp_types.CallToolResult(
                content=[
                    mcp_types.TextContent(type="text", text="tool invocation failed")
                ],
                isError=True,
            )
        audit_debug(
            "tool_result",
            principal=principal,
            tool=name,
            arguments=redacted_arguments,
        )
        record_invocation(principal, name, "allowed")
        audit_event(
            "tool_invocation", principal=principal, tool=name, outcome="allowed"
        )
        return mcp_types.CallToolResult(
            content=[mcp_types.TextContent(type="text", text=serialized_result)]
        )

    return server
