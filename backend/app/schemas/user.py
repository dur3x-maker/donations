from datetime import datetime
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.campaign import CampaignListItem
from app.schemas.contribution import RecentDonationOut

USERNAME_BLACKLIST = {
    "admin",
    "root",
    "support",
    "moderator",
    "system",
    "null",
    "undefined",
    "api",
    "test",
}
REALISTIC_EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}$"
)


def validate_realistic_email(value: EmailStr) -> str:
    email = str(value).lower()
    if not REALISTIC_EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Email must include a valid domain zone")
    return email


class UserOut(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    city: str | None = None
    is_active: bool
    is_verified: bool
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdateIn(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=24, pattern=r"^[a-zA-Z0-9_-]{3,24}$")
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    avatar_url: str | None = Field(default=None, max_length=1024)
    bio: str | None = Field(default=None, max_length=250)
    city: str | None = Field(default=None, max_length=80)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            return value
        username = value.lower()
        if username in USERNAME_BLACKLIST:
            raise ValueError("Username is reserved")
        return username

    @field_validator("first_name", "last_name", "avatar_url", "bio", "city")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class UserRegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=24, pattern=r"^[a-zA-Z0-9_-]{3,24}$")
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return validate_realistic_email(value)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        username = value.lower()
        if username in USERNAME_BLACKLIST:
            raise ValueError("Username is reserved")
        return username


class UserLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return validate_realistic_email(value)


class RefreshTokenIn(BaseModel):
    refresh_token: str = Field(min_length=1)


class VerifyEmailIn(BaseModel):
    token: str = Field(min_length=16, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class LinkAnonymousContributions(BaseModel):
    anonymous_token: str = Field(min_length=1, max_length=128)


class ContributionProgressOut(BaseModel):
    confirmed_contributions_count: int
    required_contributions_count: int = 5
    can_create_campaign: bool
    has_unfinished_campaign: bool = False
    can_open_bank_account: bool = False
    has_bank_account: bool = False
    bank_account_application_status: str | None = None


class ProfileContributionOut(BaseModel):
    id: UUID
    campaign_id: UUID
    campaign_title: str
    amount: str
    created_at: datetime


class ProfileTimelineItemOut(BaseModel):
    id: str
    title: str
    created_at: datetime


class ProfileAchievementOut(BaseModel):
    id: str
    title: str
    copy_text: str = Field(alias="copy")
    achieved_at: datetime

    model_config = ConfigDict(populate_by_name=True)


class ProfileSummaryOut(BaseModel):
    confirmed_contributions_count: int
    required_contributions_count: int = 5
    can_create_campaign: bool
    has_unfinished_campaign: bool = False
    supported_campaigns_count: int
    total_donated_amount: str
    last_contribution_at: datetime | None
    recent_contributions: list[ProfileContributionOut]
    supported_campaigns_current_amount: str
    contributions_last_30_days: int
    supported_campaigns_last_30_days: int
    achievements: list[ProfileAchievementOut]
    achievements_last_30_days: int
    user_level: str
    community_top_percent: int | None
    community_rank: int | None
    active_contributors_count: int
    timeline: list[ProfileTimelineItemOut]


class OwnerCampaignStatsOut(BaseModel):
    contributions_count: int
    unique_contributors_count: int
    average_contribution: str
    today_amount: str


class OwnerDashboardOut(BaseModel):
    campaign: CampaignListItem | None
    campaigns_count: int
    stats: OwnerCampaignStatsOut | None
    recent_donations: list[RecentDonationOut]


class UnlockProgressOut(BaseModel):
    confirmed_donations: int
    required_donations: int = 5
    can_create_campaign: bool
    remaining: int


class AuthorReputationOut(BaseModel):
    campaigns_created: int
    campaigns_completed: int
    campaigns_with_reports: int
    campaigns_without_reports: int
    total_raised_amount: str


class ProfileImpactOut(BaseModel):
    current_level: str | None
    next_level: str | None
    confirmed_contributions_count: int
    supported_campaigns_count: int
    completed_supported_campaigns: int
    active_supported_campaigns: int
    fundraising_supported_campaigns: int
    total_supported_amount: str
    progress_percent: int
    is_patron: bool
    patron_since: datetime | None


class UserAchievementOut(BaseModel):
    code: str
    title: str
    description: str
    unlocked_at: datetime


class CommunityPatronCampaignOut(BaseModel):
    id: UUID
    title: str
    cover_image_url: str | None = None
    last_supported_at: datetime


class CommunityPatronOut(BaseModel):
    user_id: UUID
    username: str
    level: str
    confirmed_contributions_count: int
    supported_campaigns_count: int
    total_donated_amount: str
    patron_since: datetime
    recent_supported_campaigns: list[CommunityPatronCampaignOut]


class PublicUserProfileOut(BaseModel):
    id: UUID
    username: str
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    city: str | None = None
    created_at: datetime
    supported_campaigns_count: int
    total_supported_campaigns: int
    total_donated_amount: str
    created_campaigns_count: int
    completed_campaigns_count: int
    achievements_count: int
    achievements: list[str]
    campaigns_created: list[CampaignListItem]
    author_reputation: AuthorReputationOut
    is_verified: bool
