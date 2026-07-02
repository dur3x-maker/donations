import logging
from secrets import token_urlsafe

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.email_sender import EmailSender
from app.models.user import User

logger = logging.getLogger("email_verification")


class EmailVerificationService:
    def __init__(self, email_sender: EmailSender) -> None:
        self.email_sender = email_sender

    async def create_and_send_token(self, session: AsyncSession, user: User) -> None:
        if user.is_verified:
            return
        user.verification_token = _new_token()
        await session.commit()
        await session.refresh(user)
        await self._send(user)

    async def resend(self, session: AsyncSession, user: User) -> None:
        if user.is_verified:
            return
        user.verification_token = _new_token()
        await session.commit()
        await session.refresh(user)
        await self._send(user)

    async def verify(self, session: AsyncSession, token: str) -> User:
        user = await session.scalar(select(User).where(User.verification_token == token))
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка подтверждения недействительна.")
        user.is_verified = True
        user.verification_token = None
        await session.commit()
        await session.refresh(user)
        return user

    async def _send(self, user: User) -> None:
        if not user.verification_token:
            return
        verify_url = f"{settings.frontend_public_url.rstrip('/')}/verify-email?token={user.verification_token}"
        try:
            await self.email_sender.send(
                user.email,
                "Подтвердите email",
                (
                    "Здравствуйте!\n\n"
                    "Подтвердите адрес электронной почты, чтобы завершить настройку профиля.\n\n"
                    f"{verify_url}\n\n"
                    "Если вы не регистрировались на платформе, просто проигнорируйте это письмо."
                ),
            )
        except Exception:
            logger.exception("email_verification_send_failed user_id=%s", user.id)


def get_email_verification_service() -> EmailVerificationService:
    return EmailVerificationService(
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
