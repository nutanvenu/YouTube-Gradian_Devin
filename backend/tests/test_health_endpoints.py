import pytest


@pytest.mark.asyncio
async def test_plain_liveness_and_readiness_endpoints(client) -> None:
    live = await client.get("/health")
    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    ready = await client.get("/readiness")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}
