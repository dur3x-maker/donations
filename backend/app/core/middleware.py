import logging
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import log_event
from app.core.request_context import request_id_context

logger = logging.getLogger("request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = _request_id(request)
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        started = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started) * 1000, 2)
            log_event(
                logger,
                logging.ERROR,
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )
            request_id_context.reset(token)
            raise

        duration_ms = round((perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        _set_security_headers(response)
        log_event(
            logger,
            logging.INFO,
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        request_id_context.reset(token)
        return response


def _request_id(request: Request) -> str:
    value = request.headers.get("X-Request-ID", "").strip()
    if value and len(value) <= 64:
        return value
    return str(uuid4())


def _set_security_headers(response: Response) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
