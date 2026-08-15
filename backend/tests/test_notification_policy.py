from datetime import UTC, datetime

from app.events.models import SafetyEvent
from app.events.notifications import age_band_allows, in_quiet_hours, safety_severity


def test_notification_policy_is_age_sensitive_and_severity_aware():
    assert safety_severity(SafetyEvent(event_type="SAFETY_RISK")) == "HIGH"
    assert age_band_allows("YOUNG_CHILD", "MEDIUM")
    assert age_band_allows("TEEN", "HIGH")
    assert not age_band_allows("TEEN", "MEDIUM")
    assert not age_band_allows("OLDER_TEEN", "HIGH")
    assert age_band_allows("OLDER_TEEN", "CRITICAL")


def test_notification_policy_applies_child_timezone_quiet_hours():
    quiet = datetime(2024, 1, 2, 22, tzinfo=UTC)
    daytime = datetime(2024, 1, 2, 12, tzinfo=UTC)
    assert in_quiet_hours(quiet, "UTC")
    assert not in_quiet_hours(daytime, "UTC")
