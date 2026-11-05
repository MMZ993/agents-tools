"""Exercise the built CLI against a local broker with isolated principals."""

import asyncio
import json
import os
from pathlib import Path
import socket

import uvicorn

from agents_tools.app import create_app
from agents_tools.policy import Policy
from agents_tools.tools import discover_tools


async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    app = create_app(
        principal_tokens={
            "reader": "reader-test-token",
            "restricted": "restricted-test-token",
        },
        policies={
            "reader": Policy("reader", ("broker_discover", "static_*"), ()),
            "restricted": Policy("restricted", ("calc_*",), ("broker_discover",)),
        },
        tools=discover_tools(root / "tests/fixtures/tools"),
    )
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", lifespan="on"))
    task = asyncio.create_task(server.serve(sockets=[sock]))

    async def cli(principal: str, *args: str, success: bool = True) -> str:
        env = {
            **os.environ,
            "AGENTS_TOOLS_URL": f"http://127.0.0.1:{port}",
            "AGENTS_TOOLS_MCP_ADMIN_TOKEN": f"{principal}-test-token",
        }
        process = await asyncio.create_subprocess_exec(
            str(root / "cli/dist/agents-tools"),
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
        assert (process.returncode == 0) == success, (args, stdout, stderr)
        return (stdout if success else stderr).decode()

    try:
        for _ in range(200):
            if server.started:
                break
            if task.done():
                await task
                raise AssertionError("broker stopped before startup")
            await asyncio.sleep(0.01)
        else:
            raise AssertionError("broker did not start")

        groups = json.loads(await cli("reader", "tools", "list"))
        assert groups == {"version": 1, "groups": [{"name": "static", "count": 1}]}
        group = json.loads(await cli("reader", "tools", "list", "--group", "static"))
        assert group == {
            "version": 1,
            "group": "static",
            "tools": [
                {"name": "static_text", "description": "Return static fixture text."}
            ],
        }
        assert "unknown group" in await cli(
            "reader", "tools", "list", "--group", "calc", success=False
        )
        assert "discovery" in await cli("restricted", "tools", "list", success=False)
        schema = json.loads(await cli("reader", "tools", "schema", "static_text"))
        assert schema == {"type": "object", "additionalProperties": False}
        result = json.loads(await cli("reader", "tools", "call", "static_text"))
        assert not result["isError"] and result["content"][0]["text"] == "fixture text"
        result = json.loads(
            await cli(
                "restricted",
                "tools",
                "call",
                "calc_add",
                "--arg",
                "left=1",
                "--arg",
                "right=2",
            )
        )
        assert not result["isError"] and result["content"][0]["text"] == "3"
        print("CLI broker integration passed")
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, timeout=10)
        sock.close()


if __name__ == "__main__":
    asyncio.run(main())
