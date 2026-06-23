from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.user import CommunityPatronOut
from app.services.community_service import get_community_patrons

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/patrons", response_model=list[CommunityPatronOut])
async def community_patrons(session: AsyncSession = Depends(get_session)) -> list[CommunityPatronOut]:
    return await get_community_patrons(session)
