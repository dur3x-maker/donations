from functools import cached_property, lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    devops_telegram_bot_token: str = Field(min_length=1)
    devops_telegram_allowed_user_ids: str = Field(min_length=1)
    devops_telegram_chat_ids: str = Field(min_length=1)
    devops_session_timeout_seconds: int = Field(default=60, ge=1, le=3600)
    sophie_devops_api_url: str = Field(min_length=1)
    sophie_devops_api_token: str | None = None
    sophie_devops_api_token_file: Path | None = None
    sophie_devops_api_timeout_seconds: float = Field(default=1250.0, ge=1.0, le=1800.0)

    @model_validator(mode="after")
    def normalize_api_url(self) -> "GatewaySettings":
        self.sophie_devops_api_url = self.sophie_devops_api_url.strip().rstrip("/")
        if not self.sophie_devops_api_url.startswith(("http://", "https://")):
            raise ValueError("SOPHIE_DEVOPS_API_URL must be an absolute HTTP(S) URL")
        if not self.sophie_devops_api_token and self.sophie_devops_api_token_file is None:
            raise ValueError(
                "SOPHIE_DEVOPS_API_TOKEN or SOPHIE_DEVOPS_API_TOKEN_FILE is required"
            )
        if (
            self.sophie_devops_api_token_file is not None
            and not self.sophie_devops_api_token_file.is_file()
        ):
            raise ValueError("SOPHIE_DEVOPS_API_TOKEN_FILE must point to a readable file")
        _ = self.api_token
        return self

    @cached_property
    def api_token(self) -> str:
        token = self.sophie_devops_api_token
        if token is None and self.sophie_devops_api_token_file is not None:
            token = self.sophie_devops_api_token_file.read_text(encoding="utf-8").strip()
        if token is None or len(token) < 32:
            raise ValueError("Sophie DevOps API token must contain at least 32 characters")
        return token

    @property
    def allowed_user_ids(self) -> frozenset[str]:
        return _identifier_set(self.devops_telegram_allowed_user_ids)

    @property
    def allowed_chat_ids(self) -> frozenset[str]:
        return _identifier_set(self.devops_telegram_chat_ids)


def _identifier_set(raw_value: str) -> frozenset[str]:
    return frozenset(value.strip() for value in raw_value.split(",") if value.strip())


@lru_cache
def get_settings() -> GatewaySettings:
    return GatewaySettings()  # type: ignore[call-arg]
