from typing import Protocol
from uuid import UUID

import httpx
from pydantic import BaseModel


class SophieDevOpsClientError(RuntimeError):
    pass


class SophieDevOpsBusyError(SophieDevOpsClientError):
    pass


class SophieDevOpsTimeoutError(SophieDevOpsClientError):
    pass


class SophieDevOpsUnavailableError(SophieDevOpsClientError):
    pass


class SophieDevOpsReply(BaseModel):
    command_id: UUID
    success: bool
    message: str
    outcome: str


class DevOpsCommandClient(Protocol):
    async def execute(
        self,
        *,
        command_id: UUID,
        text: str,
        telegram_user_id: str,
        telegram_chat_id: str,
    ) -> SophieDevOpsReply: ...


class SophieDevOpsClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = token
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
        )

    async def execute(
        self,
        *,
        command_id: UUID,
        text: str,
        telegram_user_id: str,
        telegram_chat_id: str,
    ) -> SophieDevOpsReply:
        try:
            response = await self._client.post(
                "/api/v1/devops/commands",
                headers={"Authorization": f"Bearer {self._token}"},
                json={
                    "command_id": str(command_id),
                    "text": text,
                    "telegram_user_id": telegram_user_id,
                    "telegram_chat_id": telegram_chat_id,
                },
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise SophieDevOpsTimeoutError("Sophie DevOps API timed out") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 409:
                raise SophieDevOpsBusyError("Sophie DevOps API is busy") from exc
            if exc.response.status_code == 504:
                raise SophieDevOpsTimeoutError("Sophie DevOps command timed out") from exc
            raise SophieDevOpsUnavailableError(
                f"Sophie DevOps API returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise SophieDevOpsUnavailableError("Sophie DevOps API is unavailable") from exc
        return SophieDevOpsReply.model_validate(response.json())

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
