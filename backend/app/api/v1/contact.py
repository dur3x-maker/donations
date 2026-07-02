from fastapi import APIRouter, Depends

from app.api.deps import get_optional_current_user
from app.models.user import User
from app.schemas.contact import ContactRequestIn, ContactRequestOut
from app.services.admin_event_service import AdminEventService, admin_actor_from_user, build_contact_event, get_admin_event_service

router = APIRouter(tags=["contact"])


@router.post("/contact", response_model=ContactRequestOut)
async def contact(
    payload: ContactRequestIn,
    current_user: User | None = Depends(get_optional_current_user),
    admin_events: AdminEventService = Depends(get_admin_event_service),
) -> ContactRequestOut:
    actor = admin_actor_from_user(current_user.id, current_user.username) if current_user else None
    await admin_events.publish(build_contact_event(payload, actor=actor))
    return ContactRequestOut(message="Мы получили ваше сообщение.")
