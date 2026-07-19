import httpx

from agents_tools.app import create_app


async def _get(app, path: str) -> httpx.Response:
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            return await client.get(path)


async def test_healthz_is_available_without_bearer_authentication() -> None:
    response = await _get(
        create_app(principal_tokens={}, policies={}, tools={}), "/healthz"
    )

    assert response.status_code == 200


async def test_mcp_requires_bearer_authentication() -> None:
    app = create_app(principal_tokens={"reader": "test-token"}, policies={}, tools={})

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.post("/mcp/")

    assert response.status_code == 401


async def test_metrics_is_available_without_bearer_authentication() -> None:
    response = await _get(
        create_app(principal_tokens={}, policies={}, tools={}), "/metrics/"
    )

    assert response.status_code == 200
