import pytest

from app.services.level_service import current_level_for


@pytest.mark.parametrize(
    ("count", "expected_threshold"),
    [
        (0, None),
        (1, 1),
        (4, 1),
        (5, 5),
        (19, 5),
        (20, 20),
        (49, 20),
        (50, 50),
        (51, 50),
        (99, 50),
        (100, 100),
        (101, 100),
    ],
)
def test_level_boundaries(count, expected_threshold):
    level = current_level_for(count)
    assert (level.threshold if level else None) == expected_threshold

