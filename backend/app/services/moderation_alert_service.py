import logging

from app.core.logging import log_event

logger = logging.getLogger("moderation")


async def send_moderation_alert(event_type: str, payload: dict) -> None:
    log_event(logger, logging.WARNING, "moderation_alert", type=event_type, payload=payload)
