from functools import lru_cache
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PLACEHOLDER_SECRETS = {"change-me-in-production", "replace-with-a-long-random-secret"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://donations:donations@localhost:5432/donations"
    backend_cors_origins: str = "http://localhost:3000"
    trusted_ws_origins: str = "http://localhost:3000"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    rate_limit_enabled: bool = True
    ws_max_connections_per_ip: int = 20

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env.lower() != "production":
            return self

        errors: list[str] = []
        if self.jwt_secret_key in PLACEHOLDER_SECRETS or len(self.jwt_secret_key) < 32:
            errors.append("JWT_SECRET_KEY must be a non-placeholder value with at least 32 characters")
        if not self.database_url.startswith("postgresql+asyncpg://"):
            errors.append("DATABASE_URL must use the postgresql+asyncpg:// driver")
        if _uses_localhost(self.database_url):
            errors.append("DATABASE_URL must not point to localhost in production")
        if not self.cors_origins:
            errors.append("BACKEND_CORS_ORIGINS must contain at least one production origin")
        if not self.ws_origins:
            errors.append("TRUSTED_WS_ORIGINS must contain at least one production origin")
        for origin in self.cors_origins:
            errors.extend(_validate_public_origin(origin, "BACKEND_CORS_ORIGINS"))
        for origin in self.ws_origins:
            errors.extend(_validate_public_origin(origin, "TRUSTED_WS_ORIGINS"))
        if self.ws_max_connections_per_ip < 1:
            errors.append("WS_MAX_CONNECTIONS_PER_IP must be greater than 0")

        if errors:
            raise ValueError("Invalid production settings: " + "; ".join(errors))
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [_normalize_origin(origin) for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def ws_origins(self) -> list[str]:
        return [_normalize_origin(origin) for origin in self.trusted_ws_origins.split(",") if origin.strip()]


def _normalize_origin(origin: str) -> str:
    return origin.strip().rstrip("/")


def _validate_public_origin(origin: str, field_name: str) -> list[str]:
    parsed = urlparse(origin)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"}:
        return [f"{field_name} origin must be an https origin without path: {origin}"]
    if parsed.hostname in LOCAL_HOSTS:
        return [f"{field_name} must not use localhost in production: {origin}"]
    return []


def _uses_localhost(url: str) -> bool:
    return urlparse(url).hostname in LOCAL_HOSTS


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
