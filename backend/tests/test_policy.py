from datetime import date

import pytest

from app.policies.service import age_band_for_dob, age_on, validate_timezone


@pytest.mark.parametrize(
    ("birth", "today", "expected"),
    [
        (date(2017, 8, 15), date(2026, 8, 14), "YOUNG_CHILD"),
        (date(2017, 8, 15), date(2026, 8, 15), "PRETEEN"),
        (date(2013, 8, 15), date(2026, 8, 14), "PRETEEN"),
        (date(2013, 8, 15), date(2026, 8, 15), "TEEN"),
        (date(2010, 8, 15), date(2026, 8, 14), "TEEN"),
        (date(2010, 8, 15), date(2026, 8, 15), "OLDER_TEEN"),
    ],
)
def test_age_band_boundaries(birth: date, today: date, expected: str) -> None:
    assert age_band_for_dob(birth, today) == expected


def test_age_calculation_before_birthday() -> None:
    assert age_on(date(2017, 12, 31), date(2026, 12, 30)) == 8


def test_invalid_timezone_rejected() -> None:
    with pytest.raises(ValueError):
        validate_timezone("Not/An-IANA-Zone")
