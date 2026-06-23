from decimal import Decimal
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import OwnerOut

CAMPAIGN_CATEGORIES = {"medical", "education", "emergency", "pets", "community", "personal", "other"}
ImageUrl = Annotated[str, Field(max_length=1024)]


class CampaignBaseOut(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    description: str
    target_amount: Decimal
    current_amount: Decimal
    category: str
    cover_image_url: str | None
    is_verified: bool
    is_active: bool
    status: str
    has_completion_report: bool
    report_requested_at: datetime | None
    report_completed_at: datetime | None
    report_overdue: bool = False
    created_at: datetime
    progress_percentage: int
    owner: OwnerOut | None

    model_config = ConfigDict(from_attributes=True)


class CampaignListItem(CampaignBaseOut):
    description_preview: str
    contributors_count: int


class CampaignDetail(CampaignBaseOut):
    contributors_count: int


class CampaignCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    target_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: str
    cover_image_url: str | None = Field(default=None, max_length=1024)

    @field_validator("title", "description", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        category = value.lower()
        if category not in CAMPAIGN_CATEGORIES:
            raise ValueError("Invalid campaign category")
        return category


class CampaignUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    target_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    category: str | None = None
    cover_image_url: str | None = Field(default=None, max_length=1024)
    is_active: bool | None = None

    @field_validator("title", "description", mode="before")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        if value is None:
            return value
        category = value.lower()
        if category not in CAMPAIGN_CATEGORIES:
            raise ValueError("Invalid campaign category")
        return category


class CampaignUpdatePhotoOut(BaseModel):
    id: UUID
    image_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignUpdateCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    content: str = Field(min_length=10, max_length=5000)
    photos: list[ImageUrl] = Field(default_factory=list, max_length=12)

    @field_validator("title", "content", mode="before")
    @classmethod
    def strip_update_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("photos")
    @classmethod
    def validate_photos(cls, value: list[str]) -> list[str]:
        return [url.strip() for url in value if url.strip()]


class CampaignUpdateOut(BaseModel):
    id: UUID
    campaign_id: UUID
    author_id: UUID
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    photos: list[CampaignUpdatePhotoOut]

    model_config = ConfigDict(from_attributes=True)


class CampaignCompletionPhotoOut(BaseModel):
    id: UUID
    image_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompletedCampaignListItem(CampaignListItem):
    completion_report_preview: str | None
    completion_photos: list[CampaignCompletionPhotoOut]


class CampaignCompletionSupporterOut(BaseModel):
    name: str
    is_anonymous: bool


class CampaignCompletionReportCreate(BaseModel):
    gratitude_text: str = Field(min_length=10, max_length=5000)
    photos: list[ImageUrl] = Field(min_length=1, max_length=12)

    @field_validator("gratitude_text", mode="before")
    @classmethod
    def strip_gratitude_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("photos")
    @classmethod
    def validate_photos(cls, value: list[str]) -> list[str]:
        photos = [url.strip() for url in value if url.strip()]
        if not photos:
            raise ValueError("At least one photo is required")
        return photos


class CampaignCompletionReportOut(BaseModel):
    id: UUID
    campaign_id: UUID
    author_id: UUID
    gratitude_text: str
    created_at: datetime
    raised_amount: Decimal
    supporters_count: int
    photos: list[CampaignCompletionPhotoOut]
    supporters: list[CampaignCompletionSupporterOut]

    model_config = ConfigDict(from_attributes=True)
