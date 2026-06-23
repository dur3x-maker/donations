from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def count_rows(session: AsyncSession, model, *conditions) -> int:
    statement = select(func.count()).select_from(model)
    if conditions:
        statement = statement.where(*conditions)
    return int(await session.scalar(statement) or 0)


def campaign_payload(**overrides) -> dict:
    payload = {
        "title": "Urgent medical support",
        "description": "A complete description long enough for campaign validation.",
        "target_amount": str(Decimal("5000")),
        "category": "medical",
    }
    payload.update(overrides)
    return payload
