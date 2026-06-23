from dataclasses import dataclass


@dataclass(frozen=True)
class LevelDefinition:
    title: str
    threshold: int


LEVELS = (
    LevelDefinition("Помощник", 1),
    LevelDefinition("Участник", 5),
    LevelDefinition("Наставник", 20),
    LevelDefinition("Меценат", 50),
    LevelDefinition("Хранитель сообщества", 100),
)


def current_level_for(confirmed_contributions_count: int) -> LevelDefinition | None:
    current = None
    for level in LEVELS:
        if confirmed_contributions_count >= level.threshold:
            current = level
    return current


def next_level_for(confirmed_contributions_count: int) -> LevelDefinition | None:
    return next((level for level in LEVELS if confirmed_contributions_count < level.threshold), None)


def progress_percent_for(confirmed_contributions_count: int) -> int:
    next_level = next_level_for(confirmed_contributions_count)
    if next_level is None:
        return 100
    return min(100, int((confirmed_contributions_count / next_level.threshold) * 100))
