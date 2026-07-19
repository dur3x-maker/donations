import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import log_event
from app.db.session import get_session
from app.integrations.telegram_notifier import TelegramNotifier
from app.services.telegram_moderation_service import handle_telegram_update

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger("telegram_webhook")


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    secret_token: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> dict[str, bool]:
    if settings.telegram_webhook_secret and secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Telegram webhook secret")

    update = await request.json()
    update_type = next(
        (key for key in ("callback_query", "message", "edited_message", "channel_post") if update.get(key)),
        "unknown",
    )
    log_event(
        logger,
        logging.INFO,
        "telegram_promo_trace",
        step="webhook_received",
        update_id=update.get("update_id"),
        update_type=update_type,
        bot_token_configured=bool(settings.telegram_bot_token),
        admin_chat_id_configured=bool(settings.telegram_chat_id),
        webhook_secret_configured=bool(settings.telegram_webhook_secret),
    )
    await handle_telegram_update(
        session,
        update,
        TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        ),
    )
    log_event(
        logger,
        logging.INFO,
        "telegram_promo_trace",
        step="webhook_completed",
        update_id=update.get("update_id"),
        update_type=update_type,
    )
    return {"ok": True}
