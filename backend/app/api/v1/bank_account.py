from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.bank_account import BankAccountApplicationOut, BankAccountApplicationStateOut
from app.services.bank_account_service import create_bank_account_application, get_bank_account_state

router = APIRouter(prefix="/bank-account", tags=["bank-account"])


@router.get("/application", response_model=BankAccountApplicationStateOut)
async def bank_account_application_state(
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> BankAccountApplicationStateOut:
    return await get_bank_account_state(session, current_user.id)


@router.post("/applications", response_model=BankAccountApplicationOut, status_code=status.HTTP_201_CREATED)
async def open_bank_account_application(
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> BankAccountApplicationOut:
    return await create_bank_account_application(session, current_user)
