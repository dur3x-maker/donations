from uuid import UUID

import logging
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import log_event
from app.core.rate_limit import rate_limiter
from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User
from app.models.user import UserRole
from app.services.user_service import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger("auth")


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(key: str, limit: int, window_seconds: int, detail: str = "Слишком много запросов") -> None:
    if not settings.rate_limit_enabled:
        return
    if not rate_limiter.allow(key, limit, window_seconds):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Нужна авторизация")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        log_event(logger, logging.WARNING, "invalid_access_token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен доступа")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный тип токена")

    try:
        user_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен доступа")

    user = await get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен доступа")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Профиль неактивен")
    return user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    if credentials is None:
        return None
    return await get_current_user(credentials, session)


async def require_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


async def require_moderator(current_user: User = Depends(require_current_user)) -> User:
    if current_user.role not in {UserRole.moderator, UserRole.admin}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нужны права модератора")
    return current_user
