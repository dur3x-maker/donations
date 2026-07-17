import re
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


class ContactSubject(str, Enum):
    general = "Общий вопрос"
    bug = "Сообщить об ошибке"
    suggestion = "Предложение"
    campaign_problem = "Проблема со сбором"
    other = "Другое"


class ContactRequestIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    telegram: str | None = Field(default=None, max_length=64)
    subject: ContactSubject
    message: str = Field(min_length=20, max_length=3000)

    @field_validator("name", "message")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("telegram", mode="before")
    @classmethod
    def normalize_telegram(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Telegram must be a string")
        normalized = value.strip()
        if not normalized:
            return None
        match = re.fullmatch(
            r"(?:@|(?:https?://)?t\.me/)([A-Za-z0-9_]{5,32})/?",
            normalized,
            flags=re.IGNORECASE,
        )
        if not match:
            raise ValueError("Telegram must use @username or t.me/username format")
        return f"@{match.group(1)}"


class ContactRequestOut(BaseModel):
    ok: bool = True
    message: str
