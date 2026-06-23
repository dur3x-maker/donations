import asyncio
from contextlib import asynccontextmanager
from time import perf_counter
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1.router import api_router
from app.api.ws import router as ws_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware
from app.core.request_context import get_request_id
from app.db.session import AsyncSessionLocal, engine
from app.realtime.manager import realtime_manager
from app.services.report_reminder_service import process_report_reminders

configure_logging()
logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_report_reminder_loop())
    try:
        yield
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


app = FastAPI(title="Collective Donations MVP", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(api_router)
app.include_router(ws_router)
Path("uploads").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return _error_response(request, exc.status_code, exc.detail)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(request, status.HTTP_422_UNPROCESSABLE_ENTITY, "Некорректные данные запроса")


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception path=%s request_id=%s", request.url.path, getattr(request.state, "request_id", None))
    return _error_response(request, status.HTTP_500_INTERNAL_SERVER_ERROR, "Внутренняя ошибка сервера")


@app.get("/health")
async def health() -> dict:
    started = perf_counter()
    return {"status": "ok", "duration_ms": _duration_ms(started)}


@app.get("/ready")
async def ready() -> dict:
    started = perf_counter()
    db_ok = False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1"))
        db_ok = True
    except Exception:
        db_ok = False

    realtime = realtime_manager.health()
    status_value = "ready" if db_ok else "not_ready"
    payload = {
        "status": status_value,
        "db": "ok" if db_ok else "error",
        "realtime": realtime,
        "duration_ms": _duration_ms(started),
    }
    if not db_ok:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)
    return payload


def _error_response(request: Request, status_code: int, detail) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or get_request_id()
    response = JSONResponse(
        status_code=status_code,
        content={"detail": str(detail), "request_id": request_id},
    )
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


def _duration_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 2)


async def _report_reminder_loop() -> None:
    while True:
        try:
            async with AsyncSessionLocal() as session:
                await process_report_reminders(session)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("report_reminder_check_failed")
        await asyncio.sleep(6 * 60 * 60)
