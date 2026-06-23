from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.campaign import CampaignStatus
from app.models.campaign_update import CampaignUpdate, CampaignUpdatePhoto
from app.models.notification import NotificationType
from app.models.user import User
from app.schemas.campaign import CampaignUpdateCreate, CampaignUpdateOut
from app.services.campaign_service import get_campaign_or_404
from app.services.follow_up_service import notify_campaign_subscribers


async def create_campaign_update(
    session: AsyncSession,
    campaign_id: UUID,
    author: User,
    payload: CampaignUpdateCreate,
) -> CampaignUpdateOut:
    campaign = await get_campaign_or_404(session, campaign_id)
    if campaign.owner_id != author.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только автор может публиковать обновления")
    if campaign.status != CampaignStatus.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Публиковать обычные обновления можно только для активного сбора.")

    update = CampaignUpdate(
        campaign_id=campaign.id,
        author_id=author.id,
        title=payload.title,
        content=payload.content,
    )
    session.add(update)
    await session.flush()

    photos = [CampaignUpdatePhoto(update_id=update.id, image_url=image_url) for image_url in payload.photos]
    if photos:
        session.add_all(photos)
        await session.flush()

    action_url = f"/campaigns/{campaign.id}"
    await notify_campaign_subscribers(
        session,
        campaign.id,
        NotificationType.campaign_author_update_created,
        "Автор поделился новостями",
        "Появилось новое обновление истории, которую вы поддержали.",
        action_url=action_url,
        exclude_user_id=author.id,
    )
    if photos:
        await notify_campaign_subscribers(
            session,
            campaign.id,
            NotificationType.campaign_photos_added,
            "Добавлены новые фотографии",
            "Автор опубликовал новые фотографии истории.",
            action_url=action_url,
            exclude_user_id=author.id,
        )

    await session.commit()
    return await get_campaign_update(session, campaign.id, update.id)


async def get_campaign_updates(session: AsyncSession, campaign_id: UUID) -> list[CampaignUpdateOut]:
    await get_campaign_or_404(session, campaign_id)
    updates = await session.scalars(
        select(CampaignUpdate)
        .options(selectinload(CampaignUpdate.photos))
        .where(CampaignUpdate.campaign_id == campaign_id)
        .order_by(desc(CampaignUpdate.created_at))
    )
    return [CampaignUpdateOut.model_validate(update) for update in updates]


async def get_campaign_update(session: AsyncSession, campaign_id: UUID, update_id: UUID) -> CampaignUpdateOut:
    await get_campaign_or_404(session, campaign_id)
    update = await session.scalar(
        select(CampaignUpdate)
        .options(selectinload(CampaignUpdate.photos))
        .where(CampaignUpdate.id == update_id, CampaignUpdate.campaign_id == campaign_id)
    )
    if update is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Обновление не найдено")
    return CampaignUpdateOut.model_validate(update)
