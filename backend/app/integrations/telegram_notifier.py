import asyncio
import json
import logging
from urllib import request
from urllib.error import HTTPError, URLError

from app.core.logging import log_event

logger = logging.getLogger("telegram")


class TelegramNotifier:
    def __init__(self, bot_token: str | None, chat_id: str | None) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send_message(self, text: str, reply_markup: dict | None = None, chat_id: str | int | None = None) -> None:
        target_chat_id = chat_id or self.chat_id
        if not self.bot_token or not target_chat_id:
            log_event(
                logger,
                logging.INFO,
                "telegram_api_trace",
                step="send_message_skipped",
                reason="not_configured",
                bot_token_configured=bool(self.bot_token),
                chat_id=str(target_chat_id or ""),
            )
            return

        await asyncio.to_thread(self._send_message_sync, text, reply_markup, target_chat_id)

    async def edit_message_text(
        self,
        chat_id: str | int,
        message_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> None:
        if not self.bot_token:
            logger.info("telegram_edit_skipped reason=not_configured")
            return

        await asyncio.to_thread(
            self._request_sync,
            "editMessageText",
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "disable_web_page_preview": True,
                **({"reply_markup": reply_markup} if reply_markup is not None else {}),
            },
        )

    async def answer_callback_query(self, callback_query_id: str, text: str | None = None) -> None:
        if not self.bot_token:
            logger.info("telegram_callback_answer_skipped reason=not_configured")
            return

        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        await asyncio.to_thread(self._request_sync, "answerCallbackQuery", payload)

    def _send_message_sync(self, text: str, reply_markup: dict | None = None, chat_id: str | int | None = None) -> None:
        self._request_sync(
            "sendMessage",
            {
                "chat_id": chat_id or self.chat_id,
                "text": text,
                "disable_web_page_preview": True,
                **({"reply_markup": reply_markup} if reply_markup is not None else {}),
            },
        )

    def _request_sync(self, method: str, payload: dict) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/{method}"
        data = json.dumps(payload).encode("utf-8")
        log_event(
            logger,
            logging.INFO,
            "telegram_api_trace",
            step="request_start",
            method=method,
            chat_id=str(payload.get("chat_id") or ""),
            message_id=payload.get("message_id"),
            callback_query_id=str(payload.get("callback_query_id") or ""),
            text_length=len(str(payload.get("text") or "")),
            has_reply_markup="reply_markup" in payload,
        )
        http_request = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=10) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
                log_event(
                    logger,
                    logging.INFO,
                    "telegram_api_trace",
                    step="request_completed",
                    method=method,
                    chat_id=str(payload.get("chat_id") or ""),
                    status=response.status,
                    telegram_ok=response_payload.get("ok"),
                )
                if response.status >= 400:
                    logger.warning("telegram_request_failed method=%s status=%s", method, response.status)
        except HTTPError as exc:
            try:
                error_payload = json.loads(exc.read().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                error_payload = {}
            logger.exception(
                "telegram_request_failed method=%s chat_id=%s status=%s error_code=%s description=%s",
                method,
                str(payload.get("chat_id") or ""),
                exc.code,
                error_payload.get("error_code"),
                error_payload.get("description"),
            )
        except URLError as exc:
            logger.exception(
                "telegram_request_failed method=%s chat_id=%s reason=%s",
                method,
                str(payload.get("chat_id") or ""),
                exc.reason,
            )
