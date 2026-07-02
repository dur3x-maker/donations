import asyncio
import json
import logging
from urllib import request
from urllib.error import URLError

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
            logger.info("telegram_notifier_skipped reason=not_configured")
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
        http_request = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=10) as response:
                if response.status >= 400:
                    logger.warning("telegram_request_failed method=%s status=%s", method, response.status)
        except URLError:
            logger.exception("telegram_request_failed method=%s", method)
