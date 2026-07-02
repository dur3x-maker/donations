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
    subject: ContactSubject
    message: str = Field(min_length=20, max_length=3000)

    @field_validator("name", "message")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class ContactRequestOut(BaseModel):
    ok: bool = True
    message: str
