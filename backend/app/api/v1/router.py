from fastapi import APIRouter

from app.api.v1 import activity, auth, bank_account, campaigns, community, contact, contributions, me, moderation, notifications, platform, telegram, uploads, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(campaigns.router)
api_router.include_router(contributions.router)
api_router.include_router(bank_account.router)
api_router.include_router(contact.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(users.router)
api_router.include_router(activity.router)
api_router.include_router(community.router)
api_router.include_router(notifications.router)
api_router.include_router(moderation.router)
api_router.include_router(platform.router)
api_router.include_router(telegram.router)
api_router.include_router(uploads.router)
