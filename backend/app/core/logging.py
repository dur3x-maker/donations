import json
import logging
from typing import Any

from app.core.request_context import get_request_id


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = {"event": event, "request_id": get_request_id(), **fields}
    logger.log(level, json.dumps(payload, default=str, ensure_ascii=False))
