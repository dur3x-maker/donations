from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password, password_hash)
    except Exception:
        return False


def create_access_token(user_id: UUID) -> str:
    return _create_token(user_id=user_id, token_type="access", expires_delta=timedelta(minutes=15))


def create_refresh_token(user_id: UUID) -> str:
    return _create_token(user_id=user_id, token_type="refresh", expires_delta=timedelta(days=30))


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "type", "exp"]},
    )


def generate_anonymous_token() -> str:
    return str(uuid4())


def _create_token(user_id: UUID, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
