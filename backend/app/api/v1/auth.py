from uuid import UUID

import logging
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import enforce_rate_limit, get_client_ip, get_current_user
from app.core.logging import log_event
from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import ForgotPasswordIn, RefreshTokenIn, ResetPasswordIn, TokenResponse, UserLoginIn, UserOut, UserRegisterIn, VerifyEmailIn
from app.services.email_verification_service import EmailVerificationService, get_email_verification_service
from app.services.password_reset_service import PasswordResetService, get_password_reset_service
from app.services.user_service import build_token_response, get_user_by_id, login_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("auth")


@router.post("/register", response_model=TokenResponse)
async def register(
    payload: UserRegisterIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    email_verification: EmailVerificationService = Depends(get_email_verification_service),
) -> TokenResponse:
    client_ip = get_client_ip(request)
    enforce_rate_limit(f"auth:register:{client_ip}", 8, 60, "Слишком много попыток регистрации")
    auth = await register_user(session, payload)
    user = await get_user_by_id(session, auth.user.id)
    if user is not None:
        await email_verification.create_and_send_token(session, user)
        return build_token_response(user)
    return auth


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginIn, request: Request, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    client_ip = get_client_ip(request)
    enforce_rate_limit(f"auth:login:{client_ip}", 10, 60, "Слишком много попыток входа")
    try:
        return await login_user(session, payload)
    except HTTPException as exc:
        if exc.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
            log_event(logger, logging.WARNING, "failed_auth_attempt", ip=client_ip, email=payload.email.lower())
        raise


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshTokenIn, request: Request, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    client_ip = get_client_ip(request)
    enforce_rate_limit(f"auth:refresh:{client_ip}", 30, 60, "Слишком много попыток обновления сессии")
    try:
        token_payload = decode_token(payload.refresh_token)
    except jwt.PyJWTError:
        log_event(logger, logging.WARNING, "invalid_refresh_token", ip=client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный refresh-токен")

    if token_payload.get("type") != "refresh":
        log_event(logger, logging.WARNING, "invalid_refresh_token_type", ip=client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный тип токена")

    try:
        user_id = UUID(str(token_payload["sub"]))
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный refresh-токен")

    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный refresh-токен")

    return build_token_response(user)


@router.post("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/verify-email", response_model=UserOut)
async def verify_email(
    payload: VerifyEmailIn,
    session: AsyncSession = Depends(get_session),
    email_verification: EmailVerificationService = Depends(get_email_verification_service),
) -> User:
    return await email_verification.verify(session, payload.token)


@router.post("/email-verification", response_model=UserOut)
async def resend_email_verification(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    email_verification: EmailVerificationService = Depends(get_email_verification_service),
) -> User:
    await email_verification.resend(session, current_user)
    return current_user


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    password_reset: PasswordResetService = Depends(get_password_reset_service),
) -> dict[str, str]:
    client_ip = get_client_ip(request)
    enforce_rate_limit(f"auth:forgot-password:{client_ip}", 5, 60, "Слишком много запросов восстановления. Попробуйте позже.")
    await password_reset.request_reset(session, payload.email)
    return {"message": "Если email зарегистрирован, мы отправили ссылку для восстановления пароля."}


@router.post("/reset-password", response_model=TokenResponse)
async def reset_password(
    payload: ResetPasswordIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    password_reset: PasswordResetService = Depends(get_password_reset_service),
) -> TokenResponse:
    client_ip = get_client_ip(request)
    enforce_rate_limit(f"auth:reset-password:{client_ip}", 8, 60, "Слишком много попыток восстановления. Попробуйте позже.")
    user = await password_reset.reset_password(session, payload.token, payload.password)
    return build_token_response(user)
