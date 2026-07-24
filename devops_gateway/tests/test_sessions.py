from gateway.sessions import DevOpsSessionStore


def test_sleep_timer_starts_only_after_final_response() -> None:
    now = 100.0

    def clock() -> float:
        return now

    sessions = DevOpsSessionStore(timeout_seconds=60, clock=clock)
    sessions.begin_operation("-100500", "42")

    now += 20 * 60
    assert sessions.is_active("-100500", "42")
    assert sessions.is_busy("-100500", "42")

    sessions.finish_after_response("-100500", "42")
    now += 59
    assert sessions.is_active("-100500", "42")

    now += 2
    assert not sessions.is_active("-100500", "42")
