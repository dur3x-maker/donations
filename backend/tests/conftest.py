from collections.abc import AsyncIterator, Callable
from decimal import Decimal
import os

os.environ.setdefault("PUBLIC_WEB_URL", "http://test")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models.campaign import Campaign, CampaignStatus
from app.models.contribution import Contribution, ContributionStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://donations:donations@localhost:5432/donations_test",
)


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    if not TEST_DATABASE_URL.startswith("postgresql+asyncpg://"):
        raise RuntimeError("Tests require a real PostgreSQL database")
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_database(session_factory: async_sessionmaker[AsyncSession]) -> None:
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with session_factory() as session:
        await session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
        await session.commit()


@pytest.fixture
async def db_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> Callable[[User], dict[str, str]]:
    return lambda user: {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def user_factory(db_session: AsyncSession):
    counter = 0

    async def create_user(
        *,
        username: str | None = None,
        email: str | None = None,
        password: str = "password123",
        is_active: bool = True,
    ) -> User:
        nonlocal counter
        counter += 1
        user = User(
            username=username or f"user{counter}",
            email=email or f"user{counter}@example.com",
            password_hash=hash_password(password),
            is_active=is_active,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return create_user


@pytest.fixture
def campaign_factory(db_session: AsyncSession):
    counter = 0

    async def create_campaign(
        owner: User,
        *,
        title: str | None = None,
        target_amount: Decimal = Decimal("10000"),
        current_amount: Decimal = Decimal("0"),
        status: CampaignStatus = CampaignStatus.active,
        has_completion_report: bool = False,
        is_active: bool = True,
    ) -> Campaign:
        nonlocal counter
        counter += 1
        campaign = Campaign(
            owner_id=owner.id,
            title=title or f"Campaign {counter}",
            description="A sufficiently detailed campaign description.",
            target_amount=target_amount,
            current_amount=current_amount,
            category="medical",
            is_active=is_active,
            status=status,
            has_completion_report=has_completion_report,
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)
        return campaign

    return create_campaign


@pytest.fixture
def contribution_factory(db_session: AsyncSession):
    async def create_contributions(
        campaign: Campaign,
        *,
        user: User | None = None,
        count: int = 1,
        amount: Decimal = Decimal("100"),
        anonymous_token: str | None = None,
        update_campaign_amount: bool = True,
    ) -> list[Contribution]:
        contributions = []
        for _ in range(count):
            contribution = Contribution(
                campaign_id=campaign.id,
                user_id=user.id if user else None,
                anonymous_token=anonymous_token,
                amount=amount,
                status=ContributionStatus.confirmed,
            )
            db_session.add(contribution)
            await db_session.flush()
            db_session.add(
                Payment(
                    contribution_id=contribution.id,
                    provider="test",
                    amount=amount,
                    currency="RUB",
                    status=PaymentStatus.succeeded,
                )
            )
            contributions.append(contribution)
        if update_campaign_amount:
            campaign.current_amount = Decimal(campaign.current_amount) + amount * count
        await db_session.commit()
        return contributions

    return create_contributions
