from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user
from app.db.session import get_session
from app.models.contact_request import ContactRequest
from app.models.user import User
from app.schemas.contact import ContactRequestIn, ContactRequestOut
from app.services.admin_event_service import AdminEventService, admin_actor_from_user, build_contact_event, get_admin_event_service

router = APIRouter(tags=["contact"])


@router.post("/contact", response_model=ContactRequestOut)
async def contact(
    payload: ContactRequestIn,
    current_user: User | None = Depends(get_optional_current_user),
    admin_events: AdminEventService = Depends(get_admin_event_service),
    session: AsyncSession = Depends(get_session),
) -> ContactRequestOut:
    contact_request = ContactRequest(
        user_id=current_user.id if current_user else None,
        name=payload.name,
        email=str(payload.email),
        telegram=payload.telegram,
        subject=payload.subject.value,
        message=payload.message,
    )
    session.add(contact_request)
    await session.commit()

    actor = admin_actor_from_user(current_user.id, current_user.username) if current_user else None
    await admin_events.publish(build_contact_event(payload, actor=actor))
    return ContactRequestOut(message="Мы получили ваше сообщение.")
