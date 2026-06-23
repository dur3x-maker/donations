import asyncio
from decimal import Decimal

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.campaign import Campaign
from app.models.contribution import Contribution, ContributionStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        users_count = await session.scalar(select(func.count(User.id)))
        if users_count:
            return

        demo_password_hash = hash_password("password123")
        alice = User(username="alice", email="alice@example.com", password_hash=demo_password_hash)
        bob = User(username="bob", email="bob@example.com", password_hash=demo_password_hash)
        demo_creator = User(username="marina", email="marina@example.com", password_hash=demo_password_hash)
        session.add_all([alice, bob, demo_creator])
        await session.flush()

        campaigns = [
            Campaign(
                owner_id=alice.id,
                title="Помощь приюту с теплой передержкой",
                description="Собираем на корм, лекарства и утепление комнат для животных, которые ждут новых хозяев.",
                target_amount=Decimal("50000.00"),
                current_amount=Decimal("3100.00"),
                category="pets",
                cover_image_url="https://images.unsplash.com/photo-1548199973-03cce0bbc87b",
            ),
            Campaign(
                owner_id=bob.id,
                title="Школьные материалы для сельского класса",
                description="Нужны тетради, книги, атласы и материалы для проектов, чтобы у детей был спокойный старт учебного года.",
                target_amount=Decimal("30000.00"),
                current_amount=Decimal("2000.00"),
                category="education",
                cover_image_url="https://images.unsplash.com/photo-1481627834876-b7833e8f5570",
            ),
            Campaign(
                owner_id=alice.id,
                title="Поездка на реабилитацию после операции",
                description="Помогаем семье оплатить дорогу и жилье рядом с центром, где проходит важный курс восстановления.",
                target_amount=Decimal("80000.00"),
                current_amount=Decimal("900.00"),
                category="medical",
                cover_image_url="https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d",
            ),
        ]
        session.add_all(campaigns)
        await session.flush()

        contributions = [
            Contribution(
                campaign_id=campaigns[index % len(campaigns)].id,
                user_id=demo_creator.id,
                amount=amount,
                status=ContributionStatus.confirmed,
            )
            for index, amount in enumerate(
                [Decimal("500.00"), Decimal("700.00"), Decimal("900.00"), Decimal("1100.00"), Decimal("1300.00")]
            )
        ]
        contributions.append(
            Contribution(
                campaign_id=campaigns[0].id,
                anonymous_token="demo-anonymous-token",
                amount=Decimal("1500.00"),
                status=ContributionStatus.confirmed,
            )
        )
        session.add_all(contributions)
        await session.flush()

        session.add_all(
            [
                Payment(
                    id=contribution.id,
                    contribution_id=contribution.id,
                    provider="mock",
                    amount=contribution.amount,
                    currency="RUB",
                    status=PaymentStatus.succeeded,
                    confirmed_at=contribution.created_at,
                    metadata_json={"seed": True},
                )
                for contribution in contributions
            ]
        )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
