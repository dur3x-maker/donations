import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _production_settings(**overrides) -> Settings:
    values = {
        "app_env": "production",
        "database_url": "postgresql+asyncpg://donations:secret@postgres:5432/donations",
        "backend_cors_origins": "https://test.digitalgardens.online",
        "trusted_ws_origins": "https://test.digitalgardens.online",
        "jwt_secret_key": "a-production-secret-with-more-than-32-characters",
        "public_web_url": "https://test.digitalgardens.online/",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_public_web_url_is_normalized_in_production():
    configured = _production_settings()

    assert configured.public_web_url == "https://test.digitalgardens.online"


def test_public_web_url_rejects_localhost_in_production():
    with pytest.raises(ValidationError, match="PUBLIC_WEB_URL must not use localhost"):
        _production_settings(public_web_url="http://localhost:3000")
