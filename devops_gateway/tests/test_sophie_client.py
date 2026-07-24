import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from gateway.sophie_client import (
    SophieDevOpsBusyError,
    SophieDevOpsClient,
    SophieDevOpsTimeoutError,
)


def test_client_uses_versioned_authenticated_contract() -> None:
    command_id = uuid4()
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "command_id": str(command_id),
                "success": True,
                "message": "Готово.",
                "outcome": "SUCCESS",
            },
        )

    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://sophie.internal",
        ) as http_client:
            client = SophieDevOpsClient(
                base_url="http://sophie.internal",
                token="service-secret",
                timeout_seconds=1200,
                client=http_client,
            )
            reply = await client.execute(
                command_id=command_id,
                text="обнови донаты",
                telegram_user_id="42",
                telegram_chat_id="-100500",
            )
            assert reply.message == "Готово."

    asyncio.run(scenario())

    assert captured == {
        "path": "/api/v1/devops/commands",
        "authorization": "Bearer service-secret",
        "payload": {
            "command_id": str(command_id),
            "text": "обнови донаты",
            "telegram_user_id": "42",
            "telegram_chat_id": "-100500",
        },
    }


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    (
        (409, SophieDevOpsBusyError),
        (504, SophieDevOpsTimeoutError),
    ),
)
def test_client_maps_service_failures(
    status_code: int,
    error_type: type[Exception],
) -> None:
    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(status_code, request=request)
            ),
            base_url="http://sophie.internal",
        ) as http_client:
            client = SophieDevOpsClient(
                base_url="http://sophie.internal",
                token="service-secret",
                timeout_seconds=1200,
                client=http_client,
            )
            with pytest.raises(error_type):
                await client.execute(
                    command_id=uuid4(),
                    text="покажи логи",
                    telegram_user_id="42",
                    telegram_chat_id="-100500",
                )

    asyncio.run(scenario())
