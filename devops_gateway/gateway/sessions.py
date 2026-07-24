from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic


@dataclass
class _Session:
    busy: bool = False
    expires_at: float | None = None


class DevOpsSessionStore:
    def __init__(
        self,
        timeout_seconds: int = 60,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._clock = clock
        self._sessions: dict[tuple[str, str], _Session] = {}

    def is_active(self, chat_id: str, user_id: str) -> bool:
        key = (chat_id, user_id)
        session = self._sessions.get(key)
        if session is None:
            return False
        if session.busy:
            return True
        if session.expires_at is not None and session.expires_at > self._clock():
            return True
        self._sessions.pop(key, None)
        return False

    def is_busy(self, chat_id: str, user_id: str) -> bool:
        session = self._sessions.get((chat_id, user_id))
        return session is not None and session.busy

    def begin_operation(self, chat_id: str, user_id: str) -> None:
        self._sessions[(chat_id, user_id)] = _Session(busy=True)

    def finish_after_response(self, chat_id: str, user_id: str) -> None:
        self._sessions[(chat_id, user_id)] = _Session(
            busy=False,
            expires_at=self._clock() + self._timeout_seconds,
        )

    def close(self, chat_id: str, user_id: str) -> None:
        self._sessions.pop((chat_id, user_id), None)
