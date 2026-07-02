from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_account_application import BankAccountApplication, BankAccountApplicationStatus
from app.models.user import User
from app.schemas.bank_account import BankAccountApplicationStateOut
from app.services.user_service import REQUIRED_CONFIRMED_DONATIONS, get_confirmed_donation_count


async def get_bank_account_application(session: AsyncSession, user_id: UUID) -> BankAccountApplication | None:
    return await session.scalar(
        select(BankAccountApplication).where(BankAccountApplication.user_id == user_id)
    )


async def get_bank_account_state(session: AsyncSession, user_id: UUID) -> BankAccountApplicationStateOut:
    application = await get_bank_account_application(session, user_id)
    has_bank_account = application is not None and application.status == BankAccountApplicationStatus.approved
    can_open = (
        await get_confirmed_donation_count(session, user_id) >= REQUIRED_CONFIRMED_DONATIONS
        and application is None
    )
    return BankAccountApplicationStateOut(
        can_open_bank_account=can_open,
        has_bank_account=has_bank_account,
        application_status=application.status.value if application else None,
        application=application,
    )


async def create_bank_account_application(session: AsyncSession, user: User) -> BankAccountApplication:
    state = await get_bank_account_state(session, user.id)
    if state.has_bank_account:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Банковский счёт уже открыт.")
    if state.application is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Заявка на открытие счёта уже отправлена.")
    if not state.can_open_bank_account:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Для открытия счёта нужно минимум 5 подтверждённых донатов.",
        )

    application = BankAccountApplication(
        user_id=user.id,
        status=BankAccountApplicationStatus.pending,
    )
    session.add(application)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Заявка на открытие счёта уже отправлена.")
    await session.refresh(application)
    return application
