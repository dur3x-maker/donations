import logging
import re
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from gateway.sessions import DevOpsSessionStore
from gateway.sophie_client import (
    DevOpsCommandClient,
    SophieDevOpsBusyError,
    SophieDevOpsTimeoutError,
    SophieDevOpsUnavailableError,
)

logger = logging.getLogger("donations.devops_gateway")


class TelegramMessage(Protocol):
    text: str | None
    from_user: Any
    chat: Any
    message_id: int

    def answer(self, text: str, **kwargs: Any) -> Awaitable[Any]: ...


@dataclass(frozen=True)
class DevOpsTelegramAccess:
    allowed_user_ids: frozenset[str]
    allowed_chat_ids: frozenset[str]
    bot_username: str

    def addressed_command(self, text: str) -> str | None:
        prefixes = ("софи", "sophie", f"@{self.bot_username.lstrip('@')}")
        for prefix in sorted(set(prefixes), key=len, reverse=True):
            match = re.match(
                rf"^{re.escape(prefix)}(?=$|[\s,.:;!?])[\s,.:;!?]*",
                text,
                flags=re.IGNORECASE,
            )
            if match is not None:
                return text[match.end() :].strip()
        return None


class TelegramDevOpsGateway:
    def __init__(
        self,
        *,
        access: DevOpsTelegramAccess,
        sessions: DevOpsSessionStore,
        client: DevOpsCommandClient,
    ) -> None:
        self._access = access
        self._sessions = sessions
        self._client = client

    async def handle(self, message: TelegramMessage) -> None:
        text = (message.text or "").strip()
        if not text or message.chat.type not in {"group", "supergroup"}:
            return

        chat_id = str(message.chat.id)
        if chat_id not in self._access.allowed_chat_ids:
            return

        user_id = str(message.from_user.id) if message.from_user is not None else ""
        addressed_command = self._access.addressed_command(text)
        is_addressed = addressed_command is not None
        if user_id not in self._access.allowed_user_ids:
            if is_addressed:
                await message.answer("Недостаточно прав для выполнения этой операции.")
            return

        if not is_addressed and not self._sessions.is_active(chat_id, user_id):
            return
        if self._sessions.is_busy(chat_id, user_id):
            await message.answer("Предыдущая операция ещё выполняется.")
            return

        command_text = addressed_command if addressed_command is not None else text
        if not command_text:
            await message.answer("Слушаю. Что нужно проверить?")
            self._sessions.finish_after_response(chat_id, user_id)
            return

        self._sessions.begin_operation(chat_id, user_id)
        try:
            await message.answer("Поняла.\n\nНачинаю...")
            reply = await self._client.execute(
                command_id=_command_id(message),
                text=command_text,
                telegram_user_id=user_id,
                telegram_chat_id=chat_id,
            )
            for chunk in split_telegram_message(reply.message or "Операция завершена без ответа."):
                await message.answer(chunk)
        except SophieDevOpsBusyError:
            await message.answer("Sophie DevOps сейчас выполняет другую операцию. Повтори позже.")
        except SophieDevOpsTimeoutError:
            await message.answer(
                "Sophie DevOps не ответила вовремя. Статус операции неизвестен; "
                "перед повтором сначала проверь состояние Donations."
            )
        except SophieDevOpsUnavailableError:
            await message.answer(
                "Sophie DevOps API сейчас недоступен. Команда не подтверждена; попробуй позже."
            )
        except Exception:
            logger.exception(
                "DevOps command failed chat_id=%s user_id=%s message_id=%s",
                chat_id,
                user_id,
                message.message_id,
            )
            try:
                await message.answer(
                    "Не удалось выполнить операцию. Подробности записаны в лог Gateway."
                )
            except Exception:
                self._sessions.close(chat_id, user_id)
                raise
        self._sessions.finish_after_response(chat_id, user_id)


def _command_id(message: TelegramMessage) -> UUID:
    if isinstance(message.message_id, int):
        return uuid5(
            NAMESPACE_URL,
            f"donations-devops:{message.chat.id}:{message.message_id}",
        )
    return uuid4()


def split_telegram_message(text: str, limit: int = 4096) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        boundary = remaining.rfind("\n", 0, limit + 1)
        if boundary <= 0:
            boundary = remaining.rfind(" ", 0, limit + 1)
        if boundary <= 0:
            boundary = limit
        chunks.append(remaining[:boundary].rstrip())
        remaining = remaining[boundary:].lstrip()
    return chunks
