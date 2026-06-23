import asyncio
import json
import logging
from uuid import UUID

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.logging import log_event
from app.core.rate_limit import rate_limiter
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.realtime.manager import CATALOG_TOPIC, campaign_topic, dashboard_topic, notifications_topic, realtime_manager
from app.services.user_service import get_user_by_id

router = APIRouter(prefix="/ws", tags=["websocket"])
logger = logging.getLogger("realtime")


@router.websocket("/campaigns/{campaign_id}")
async def campaign_updates(websocket: WebSocket, campaign_id: UUID) -> None:
    await _serve_topic(websocket, campaign_topic(campaign_id))


@router.websocket("/catalog")
async def catalog_updates(websocket: WebSocket) -> None:
    await _serve_topic(websocket, CATALOG_TOPIC)


@router.websocket("/me/dashboard")
async def dashboard_updates(websocket: WebSocket) -> None:
    user_id = await _authenticated_user_id(websocket)
    if user_id is None:
        return
    await _serve_topic(websocket, dashboard_topic(user_id), subprotocol="bearer")


@router.websocket("/me/notifications")
async def notification_updates(websocket: WebSocket) -> None:
    user_id = await _authenticated_user_id(websocket)
    if user_id is None:
        return
    await _serve_topic(websocket, notifications_topic(user_id), subprotocol="bearer")


async def _authenticated_user_id(websocket: WebSocket) -> UUID | None:
    protocols = [protocol.strip() for protocol in websocket.headers.get("sec-websocket-protocol", "").split(",")]
    if len(protocols) != 2 or protocols[0] != "bearer":
        await websocket.close(code=1008)
        return None
    token = protocols[1]

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("access token required")
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        await websocket.close(code=1008)
        return None

    async with AsyncSessionLocal() as session:
        user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        await websocket.close(code=1008)
        return None
    return user.id


async def _serve_topic(websocket: WebSocket, topic: str, subprotocol: str | None = None) -> None:
    client_ip = websocket.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    if not client_ip:
        client_ip = websocket.client.host if websocket.client else "unknown"

    origin = websocket.headers.get("origin")
    if origin and origin not in settings.ws_origins:
        log_event(logger, logging.WARNING, "websocket_rejected_origin", ip=client_ip, origin=origin)
        await websocket.close(code=1008)
        return

    if settings.rate_limit_enabled and not rate_limiter.allow(f"ws:{client_ip}", 20, 60):
        log_event(logger, logging.WARNING, "websocket_rate_limited", ip=client_ip)
        await websocket.close(code=1008)
        return

    connected = await realtime_manager.connect(topic, websocket, client_ip, subprotocol=subprotocol)
    if not connected:
        return

    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue

            if len(message) > 1024:
                log_event(logger, logging.WARNING, "websocket_payload_too_large", ip=client_ip)
                await websocket.close(code=1003)
                break

            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                log_event(logger, logging.WARNING, "websocket_invalid_payload", ip=client_ip)
                continue

            if not isinstance(payload, dict) or payload.get("type") not in {"pong", "ping"}:
                log_event(logger, logging.WARNING, "websocket_ignored_payload", ip=client_ip)
    except WebSocketDisconnect:
        pass
    finally:
        realtime_manager.disconnect(topic, websocket)
