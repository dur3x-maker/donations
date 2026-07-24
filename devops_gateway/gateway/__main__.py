import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message

from gateway.config import get_settings
from gateway.sessions import DevOpsSessionStore
from gateway.sophie_client import SophieDevOpsClient
from gateway.telegram import DevOpsTelegramAccess, TelegramDevOpsGateway

router = Router(name="donations_devops_gateway")


@router.message(F.text)
async def handle_text(message: Message, gateway: TelegramDevOpsGateway) -> None:
    await gateway.handle(message)


async def run() -> None:
    settings = get_settings()
    bot = Bot(token=settings.devops_telegram_bot_token)
    bot_user = await bot.get_me()
    if not bot_user.username:
        raise RuntimeError("Telegram DevOps bot must have a username")

    client = SophieDevOpsClient(
        base_url=settings.sophie_devops_api_url,
        token=settings.api_token,
        timeout_seconds=settings.sophie_devops_api_timeout_seconds,
    )
    gateway = TelegramDevOpsGateway(
        access=DevOpsTelegramAccess(
            allowed_user_ids=settings.allowed_user_ids,
            allowed_chat_ids=settings.allowed_chat_ids,
            bot_username=bot_user.username,
        ),
        sessions=DevOpsSessionStore(settings.devops_session_timeout_seconds),
        client=client,
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(
            bot,
            gateway=gateway,
            allowed_updates=["message"],
        )
    finally:
        await client.close()
        await bot.session.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run())


if __name__ == "__main__":
    main()
