from collections import defaultdict
import logging
from fastapi import WebSocket
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import log_event

logger = logging.getLogger("realtime")

CATALOG_TOPIC = "catalog"


def campaign_topic(campaign_id: object) -> str:
    return f"campaign:{campaign_id}"


def dashboard_topic(user_id: object) -> str:
    return f"dashboard:{user_id}"


def notifications_topic(user_id: object) -> str:
    return f"notifications:{user_id}"


class RealtimeManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._connection_ips: dict[WebSocket, str] = {}
        self._ip_counts: dict[str, int] = defaultdict(int)

    async def connect(self, topic: str, websocket: WebSocket, client_ip: str, subprotocol: str | None = None) -> bool:
        if self._ip_counts[client_ip] >= settings.ws_max_connections_per_ip:
            await websocket.close(code=1008)
            log_event(logger, logging.WARNING, "websocket_connection_limit", ip=client_ip)
            return False

        await websocket.accept(subprotocol=subprotocol)
        self._connections[topic].add(websocket)
        self._connection_ips[websocket] = client_ip
        self._ip_counts[client_ip] += 1
        log_event(
            logger,
            logging.INFO,
            "websocket_connected",
            topic=topic,
            ip=client_ip,
            connection_count=self.connection_count,
        )
        return True

    def disconnect(self, topic: str, websocket: WebSocket) -> None:
        self._connections[topic].discard(websocket)
        if not self._connections[topic]:
            self._connections.pop(topic, None)

        client_ip = self._connection_ips.pop(websocket, None)
        if client_ip:
            self._ip_counts[client_ip] = max(0, self._ip_counts[client_ip] - 1)
            if self._ip_counts[client_ip] == 0:
                self._ip_counts.pop(client_ip, None)

        log_event(
            logger,
            logging.INFO,
            "websocket_disconnected",
            topic=topic,
            ip=client_ip,
            connection_count=self.connection_count,
        )

    async def broadcast(self, topic: str, payload: BaseModel | dict) -> None:
        data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
        stale_connections: list[WebSocket] = []

        for websocket in list(self._connections.get(topic, set())):
            try:
                await websocket.send_json(data)
            except Exception:
                stale_connections.append(websocket)

        for websocket in stale_connections:
            self.disconnect(topic, websocket)

    @property
    def connection_count(self) -> int:
        return sum(len(connections) for connections in self._connections.values())

    def health(self) -> dict[str, int]:
        return {
            "rooms": len(self._connections),
            "connections": self.connection_count,
        }


realtime_manager = RealtimeManager()
