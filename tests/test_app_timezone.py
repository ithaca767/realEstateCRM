import unittest
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app import (
    NY,
    app,
    fmt_dt,
    get_user_tz,
    normalize_followup_due,
    normalize_utc_instant,
)


class AppTimezoneRegressionTests(unittest.TestCase):
    """
    Locks down Ulysses' existing New York timezone behavior before
    account-specific runtime timezone support is introduced.

    These tests intentionally describe current behavior. They are not
    permission to change timestamp storage or date-only semantics.
    """

    def test_get_user_tz_is_new_york(self):
        tz = get_user_tz()

        self.assertEqual(tz.key, "America/New_York")
        self.assertEqual(tz, NY)

    def test_utc_instant_converts_to_edt(self):
        value = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)

        result = normalize_utc_instant(value)

        self.assertEqual(result, datetime(2026, 9, 20, 14, 0, tzinfo=NY))
        self.assertEqual(result.utcoffset().total_seconds(), -4 * 3600)

    def test_utc_instant_converts_to_est(self):
        value = datetime(2026, 12, 20, 18, 0, tzinfo=timezone.utc)

        result = normalize_utc_instant(value)

        self.assertEqual(result, datetime(2026, 12, 20, 13, 0, tzinfo=NY))
        self.assertEqual(result.utcoffset().total_seconds(), -5 * 3600)

    def test_aware_instant_is_converted_not_reinterpreted(self):
        pacific = ZoneInfo("America/Los_Angeles")
        value = datetime(2026, 9, 20, 11, 0, tzinfo=pacific)

        result = normalize_utc_instant(value)

        self.assertEqual(result, datetime(2026, 9, 20, 14, 0, tzinfo=NY))
        self.assertEqual(result.astimezone(timezone.utc), value.astimezone(timezone.utc))

    def test_naive_utc_instant_preserves_existing_legacy_behavior(self):
        value = datetime(2026, 9, 20, 18, 0)

        result = normalize_utc_instant(value)

        self.assertEqual(result, datetime(2026, 9, 20, 14, 0, tzinfo=NY))

    def test_naive_followup_due_is_new_york_wall_time(self):
        value = datetime(2026, 9, 20, 14, 30)

        result = normalize_followup_due(value)

        self.assertEqual(result, datetime(2026, 9, 20, 14, 30, tzinfo=NY))

    def test_aware_followup_due_converts_to_new_york(self):
        value = datetime(2026, 9, 20, 18, 30, tzinfo=timezone.utc)

        result = normalize_followup_due(value)

        self.assertEqual(result, datetime(2026, 9, 20, 14, 30, tzinfo=NY))

    def test_fmt_dt_converts_aware_utc_to_new_york(self):
        value = datetime(2026, 9, 20, 18, 30, tzinfo=timezone.utc)

        with app.app_context():
            result = fmt_dt(value)

        self.assertEqual(result, "Sep 20, 2026 2:30 PM")

    def test_fmt_dt_preserves_naive_new_york_wall_time(self):
        value = datetime(2026, 9, 20, 14, 30)

        with app.app_context():
            result = fmt_dt(value)

        self.assertEqual(result, "Sep 20, 2026 2:30 PM")

    def test_date_only_value_is_not_a_timezone_instant(self):
        value = date(2026, 9, 20)

        self.assertNotIsInstance(value, datetime)
        self.assertEqual(value.isoformat(), "2026-09-20")


if __name__ == "__main__":
    unittest.main()
