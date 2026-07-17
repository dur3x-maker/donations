import logging
from datetime import timedelta
from secrets import token_urlsafe

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.public_urls import build_public_web_url
from app.core.security import hash_password
from app.db.base import utcnow
from app.integrations.email_sender import EmailSender
from app.models.user import User

logger = logging.getLogger("password_reset")
PASSWORD_RESET_TTL = timedelta(hours=1)


class PasswordResetService:
    def __init__(self, email_sender: EmailSender) -> None:
        self.email_sender = email_sender

    async def request_reset(self, session: AsyncSession, email: str) -> None:
        user = await session.scalar(select(User).where(User.email == email.lower()))
        if user is None or not user.is_active:
            return

        user.password_reset_token = _new_token()
        user.password_reset_expires_at = utcnow() + PASSWORD_RESET_TTL
        await session.commit()
        await session.refresh(user)
        await self._send(user)

    async def reset_password(self, session: AsyncSession, token: str, password: str) -> User:
        user = await session.scalar(select(User).where(User.password_reset_token == token))
        if user is None or user.password_reset_expires_at is None or user.password_reset_expires_at < utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ссылка для восстановления пароля недействительна или устарела.")

        user.password_hash = hash_password(password)
        user.password_reset_token = None
        user.password_reset_expires_at = None
        await session.commit()
        await session.refresh(user)
        return user

    async def _send(self, user: User) -> None:
        if not user.password_reset_token:
            return
        reset_url = build_public_web_url("/reset-password", {"token": user.password_reset_token})
        try:
            await self.email_sender.send(
                user.email,
                "Восстановление пароля TipForTea",
                (
                    "Здравствуйте!\n\n"
                    "Вы запросили восстановление пароля на TipForTea. Перейдите по ссылке и задайте новый пароль:\n\n"
                    f"{reset_url}\n\n"
                    "Ссылка действует 1 час. Если вы не запрашивали восстановление, просто проигнорируйте это письмо."
                ),
            )
        except Exception:
            logger.exception("password_reset_send_failed user_id=%s", user.id)


def get_password_reset_service() -> PasswordResetService:
    return PasswordResetService(
        EmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            from_email=settings.smtp_from_email,
            use_tls=settings.smtp_use_tls,
        )
    )


def _new_token() -> str:
    return token_urlsafe(48)
