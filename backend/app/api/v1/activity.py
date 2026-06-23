from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.activity import ActivityOut
from app.services.activity_service import get_activity_feed

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/feed", response_model=list[ActivityOut])
async def activity_feed(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[ActivityOut]:
    return await get_activity_feed(session, page=page, page_size=page_size)
