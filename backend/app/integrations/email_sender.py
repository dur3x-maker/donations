import asyncio
from email.message import EmailMessage
import logging
import smtplib

logger = logging.getLogger("email")


class EmailSender:
    def __init__(
        self,
        host: str | None,
        port: int,
        username: str | None,
        password: str | None,
        from_email: str | None,
        use_tls: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.from_email)

    async def send(self, to_email: str, subject: str, body: str) -> None:
        if not self.is_configured:
            logger.info("email_sender_skipped reason=not_configured to=%s", to_email)
            return

        await asyncio.to_thread(self._send_sync, to_email, subject, body)

    def _send_sync(self, to_email: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self.from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(message)
