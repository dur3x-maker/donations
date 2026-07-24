import asyncio
from dataclasses import dataclass, field
from uuid import UUID

from gateway.sessions import DevOpsSessionStore
from gateway.sophie_client import SophieDevOpsReply
from gateway.telegram import DevOpsTelegramAccess, TelegramDevOpsGateway


@dataclass
class FakeUser:
    id: int


@dataclass
class FakeChat:
    id: int = -100500
    type: str = "supergroup"


@dataclass
class FakeMessage:
    text: str | None
    from_user: FakeUser | None = field(default_factory=lambda: FakeUser(42))
    chat: FakeChat = field(default_factory=FakeChat)
    message_id: int = 1
    answers: list[str] = field(default_factory=list)

    async def answer(self, text: str, **kwargs: object) -> None:
        del kwargs
        self.answers.append(text)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def execute(
        self,
        *,
        command_id: UUID,
        text: str,
        telegram_user_id: str,
        telegram_chat_id: str,
    ) -> SophieDevOpsReply:
        self.calls.append(
            {
                "command_id": command_id,
                "text": text,
                "telegram_user_id": telegram_user_id,
                "telegram_chat_id": telegram_chat_id,
            }
        )
        return SophieDevOpsReply(
            command_id=command_id,
            success=True,
            message="Готово.",
            outcome="SUCCESS",
        )


class BlockingClient(FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def execute(
        self,
        *,
        command_id: UUID,
        text: str,
        telegram_user_id: str,
        telegram_chat_id: str,
    ) -> SophieDevOpsReply:
        self.started.set()
        await self.release.wait()
        return await super().execute(
            command_id=command_id,
            text=text,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
        )


def _gateway(client: FakeClient | None = None) -> tuple[TelegramDevOpsGateway, FakeClient]:
    command_client = client or FakeClient()
    return (
        TelegramDevOpsGateway(
            access=DevOpsTelegramAccess(
                allowed_user_ids=frozenset({"42"}),
                allowed_chat_ids=frozenset({"-100500"}),
                bot_username="SophieDevOpsBot",
            ),
            sessions=DevOpsSessionStore(timeout_seconds=60),
            client=command_client,
        ),
        command_client,
    )


def test_ordinary_group_messages_are_silent_until_wakeup() -> None:
    gateway, client = _gateway()
    message = FakeMessage("Никит, глянь фронт.")

    asyncio.run(gateway.handle(message))

    assert message.answers == []
    assert client.calls == []


def test_mention_starts_session_and_followup_does_not_require_name() -> None:
    gateway, client = _gateway()
    first = FakeMessage("@SophieDevOpsBot, обнови донаты", message_id=10)
    followup = FakeMessage("Покажи логи.", message_id=11)

    async def scenario() -> None:
        await gateway.handle(first)
        await gateway.handle(followup)

    asyncio.run(scenario())

    assert first.answers == ["Поняла.\n\nНачинаю...", "Готово."]
    assert followup.answers == ["Поняла.\n\nНачинаю...", "Готово."]
    assert [call["text"] for call in client.calls] == ["обнови донаты", "Покажи логи."]


def test_russian_name_can_wake_gateway() -> None:
    gateway, client = _gateway()
    message = FakeMessage("Софи, проверь контейнеры")

    asyncio.run(gateway.handle(message))

    assert client.calls[0]["text"] == "проверь контейнеры"


def test_foreign_user_cannot_execute_commands() -> None:
    gateway, client = _gateway()
    addressed = FakeMessage("Софи, обнови донаты", from_user=FakeUser(777))
    ordinary = FakeMessage("обнови донаты", from_user=FakeUser(777), message_id=2)

    async def scenario() -> None:
        await gateway.handle(addressed)
        await gateway.handle(ordinary)

    asyncio.run(scenario())

    assert addressed.answers == ["Недостаточно прав для выполнения этой операции."]
    assert ordinary.answers == []
    assert client.calls == []


def test_foreign_chat_is_always_ignored() -> None:
    gateway, client = _gateway()
    message = FakeMessage("Софи, обнови донаты", chat=FakeChat(id=-999))

    asyncio.run(gateway.handle(message))

    assert message.answers == []
    assert client.calls == []


def test_private_chat_is_not_a_devops_entrypoint() -> None:
    gateway, client = _gateway()
    message = FakeMessage("Софи, обнови донаты", chat=FakeChat(type="private"))

    asyncio.run(gateway.handle(message))

    assert message.answers == []
    assert client.calls == []


def test_second_command_does_not_run_while_long_operation_is_busy() -> None:
    client = BlockingClient()
    gateway, _ = _gateway(client)
    deployment = FakeMessage("Софи, обнови донаты", message_id=20)
    logs = FakeMessage("Покажи логи", message_id=21)

    async def scenario() -> None:
        deployment_task = asyncio.create_task(gateway.handle(deployment))
        await client.started.wait()
        await gateway.handle(logs)
        client.release.set()
        await deployment_task

    asyncio.run(scenario())

    assert logs.answers == ["Предыдущая операция ещё выполняется."]
    assert len(client.calls) == 1
