import unittest
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from calendar_ics import (
    ics_escape,
    serialize_calendar,
)


NY = ZoneInfo("America/New_York")
PACIFIC = ZoneInfo("America/Los_Angeles")


class CalendarICSTests(unittest.TestCase):
    def setUp(self):
        self.dtstamp = datetime(
            2026,
            9,
            20,
            4,
            30,
            tzinfo=timezone.utc,
        )

    def test_escape_text(self):
        self.assertEqual(
            ics_escape("Call, discuss; next\nstep\\later"),
            "Call\\, discuss\\; next\\nstep\\\\later",
        )

    def test_timed_event_uses_named_timezone_and_thirty_minute_end(self):
        item = {
            "uid": "ulysses-followup-42@ulyssescrm",
            "title": "Call Tyler",
            "description": "Discuss inspection.",
            "event_kind": "timed",
            "start_at": datetime(
                2026,
                9,
                20,
                14,
                0,
                tzinfo=NY,
            ),
            "start_date": None,
        }

        result = serialize_calendar(
            [item],
            dtstamp=self.dtstamp,
        )

        self.assertIn(
            "DTSTART;TZID=America/New_York:20260920T140000\r\n",
            result,
        )
        self.assertIn(
            "DTEND;TZID=America/New_York:20260920T143000\r\n",
            result,
        )
        self.assertIn(
            "UID:ulysses-followup-42@ulyssescrm\r\n",
            result,
        )
        self.assertIn(
            "DTSTAMP:20260920T043000Z\r\n",
            result,
        )

    def test_pacific_timed_event_preserves_pacific_timezone(self):
        item = {
            "uid": "ulysses-followup-42@ulyssescrm",
            "title": "Call Tyler",
            "description": "",
            "event_kind": "timed",
            "start_at": datetime(
                2026,
                9,
                20,
                11,
                0,
                tzinfo=PACIFIC,
            ),
            "start_date": None,
        }

        result = serialize_calendar(
            [item],
            dtstamp=self.dtstamp,
        )

        self.assertIn(
            "DTSTART;TZID=America/Los_Angeles:20260920T110000\r\n",
            result,
        )
        self.assertIn(
            "DTEND;TZID=America/Los_Angeles:20260920T113000\r\n",
            result,
        )

    def test_all_day_event_uses_exclusive_following_day_dtend(self):
        item = {
            "uid": "ulysses-transaction_deadline-9@ulyssescrm",
            "title": "Mortgage commitment",
            "description": "",
            "event_kind": "all_day",
            "start_at": None,
            "start_date": date(2026, 9, 21),
        }

        result = serialize_calendar(
            [item],
            dtstamp=self.dtstamp,
        )

        self.assertIn(
            "DTSTART;VALUE=DATE:20260921\r\n",
            result,
        )
        self.assertIn(
            "DTEND;VALUE=DATE:20260922\r\n",
            result,
        )
        self.assertNotIn("TZID=", result)

    def test_description_is_escaped(self):
        item = {
            "uid": "ulysses-followup-42@ulyssescrm",
            "title": "Call Tyler",
            "description": "Inspection, financing;\ncall back",
            "event_kind": "timed",
            "start_at": datetime(
                2026,
                9,
                20,
                14,
                0,
                tzinfo=NY,
            ),
            "start_date": None,
        }

        result = serialize_calendar(
            [item],
            dtstamp=self.dtstamp,
        )

        self.assertIn(
            "DESCRIPTION:Inspection\\, financing\\;\\ncall back\r\n",
            result,
        )

    def test_naive_timed_event_is_rejected(self):
        item = {
            "uid": "ulysses-followup-42@ulyssescrm",
            "title": "Call Tyler",
            "description": "",
            "event_kind": "timed",
            "start_at": datetime(2026, 9, 20, 14, 0),
            "start_date": None,
        }

        with self.assertRaises(ValueError):
            serialize_calendar(
                [item],
                dtstamp=self.dtstamp,
            )

    def test_calendar_has_single_wrapper_for_multiple_events(self):
        items = [
            {
                "uid": "ulysses-followup-42@ulyssescrm",
                "title": "Call Tyler",
                "description": "",
                "event_kind": "timed",
                "start_at": datetime(
                    2026,
                    9,
                    20,
                    14,
                    0,
                    tzinfo=NY,
                ),
                "start_date": None,
            },
            {
                "uid": "ulysses-transaction_deadline-9@ulyssescrm",
                "title": "Mortgage commitment",
                "description": "",
                "event_kind": "all_day",
                "start_at": None,
                "start_date": date(2026, 9, 21),
            },
        ]

        result = serialize_calendar(
            items,
            dtstamp=self.dtstamp,
        )

        self.assertEqual(result.count("BEGIN:VCALENDAR"), 1)
        self.assertEqual(result.count("END:VCALENDAR"), 1)
        self.assertEqual(result.count("BEGIN:VEVENT"), 2)
        self.assertEqual(result.count("END:VEVENT"), 2)


if __name__ == "__main__":
    unittest.main()
