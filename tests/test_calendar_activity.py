import unittest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from calendar_activity import (
    calendar_item,
    calendar_uid,
    list_calendar_items,
)


NY = ZoneInfo("America/New_York")
PACIFIC = ZoneInfo("America/Los_Angeles")


class CalendarActivityAdapterTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 20, 14, 0, tzinfo=NY)

    def test_uid_uses_stable_activity_identity(self):
        activity = {"activity_key": "followup:42"}

        self.assertEqual(
            calendar_uid(activity),
            "ulysses-followup-42@ulyssescrm",
        )

    def test_uid_does_not_change_when_activity_content_changes(self):
        first = {
            "activity_key": "followup:42",
            "title": "Call Tyler",
        }
        changed = {
            "activity_key": "followup:42",
            "title": "Call Tyler and Gabby",
        }

        self.assertEqual(calendar_uid(first), calendar_uid(changed))

    def test_timed_activity_converts_instant_to_account_timezone(self):
        activity = {
            "activity_key": "followup:42",
            "title": "Call Tyler",
            "description": "Discuss inspection.",
            "target_url": "/engagements/42/edit",
            "calendar_eligible": True,
            "due_at": datetime(
                2026,
                9,
                20,
                18,
                0,
                tzinfo=timezone.utc,
            ),
            "due_date": None,
        }

        item = calendar_item(activity, now=self.now)

        self.assertEqual(item["event_kind"], "timed")
        self.assertEqual(item["start_at"].hour, 14)
        self.assertEqual(item["start_at"].tzinfo, NY)
        self.assertIsNone(item["start_date"])

        self.assertEqual(
            item["start_at"].astimezone(timezone.utc),
            activity["due_at"],
        )

    def test_timed_activity_uses_pacific_account_timezone(self):
        now = datetime(2026, 9, 20, 11, 0, tzinfo=PACIFIC)

        activity = {
            "activity_key": "followup:42",
            "title": "Call Tyler",
            "description": "",
            "target_url": None,
            "calendar_eligible": True,
            "due_at": datetime(
                2026,
                9,
                20,
                18,
                0,
                tzinfo=timezone.utc,
            ),
            "due_date": None,
        }

        item = calendar_item(activity, now=now)

        self.assertEqual(item["start_at"].hour, 11)
        self.assertEqual(item["start_at"].tzinfo, PACIFIC)
        self.assertEqual(
            item["start_at"].astimezone(timezone.utc),
            activity["due_at"],
        )

    def test_date_only_activity_remains_true_all_day_date(self):
        activity = {
            "activity_key": "transaction_deadline:9",
            "title": "Mortgage commitment",
            "description": "",
            "target_url": "/transactions/3",
            "calendar_eligible": True,
            "due_at": None,
            "due_date": date(2026, 9, 21),
        }

        item = calendar_item(activity, now=self.now)

        self.assertEqual(item["event_kind"], "all_day")
        self.assertEqual(item["start_date"], date(2026, 9, 21))
        self.assertIsNone(item["start_at"])

    def test_ineligible_activity_is_rejected(self):
        activity = {
            "activity_key": "task:7",
            "calendar_eligible": False,
            "due_at": None,
            "due_date": date(2026, 9, 21),
        }

        with self.assertRaises(ValueError):
            calendar_item(activity, now=self.now)

    def test_calendar_activity_requires_due_value(self):
        activity = {
            "activity_key": "followup:42",
            "calendar_eligible": True,
            "due_at": None,
            "due_date": None,
        }

        with self.assertRaises(ValueError):
            calendar_item(activity, now=self.now)

    @patch("calendar_activity.list_activities")
    def test_list_calendar_items_filters_ineligible_activity(
        self,
        list_activities,
    ):
        list_activities.return_value = [
            {
                "activity_key": "followup:42",
                "title": "Call Tyler",
                "description": "",
                "target_url": None,
                "calendar_eligible": True,
                "due_at": datetime(
                    2026,
                    9,
                    20,
                    16,
                    0,
                    tzinfo=NY,
                ),
                "due_date": None,
            },
            {
                "activity_key": "task:7",
                "title": "Prepare CMA",
                "description": "",
                "target_url": None,
                "calendar_eligible": False,
                "due_at": None,
                "due_date": date(2026, 9, 21),
            },
        ]

        conn = MagicMock()

        items = list_calendar_items(
            conn,
            101,
            now=self.now,
        )

        list_activities.assert_called_once_with(
            conn,
            101,
            now=self.now,
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["activity_key"], "followup:42")

    @patch("calendar_activity.list_activities")
    def test_list_calendar_items_passes_exact_user_to_activity_engine(
        self,
        list_activities,
    ):
        list_activities.return_value = []

        conn = MagicMock()

        list_calendar_items(
            conn,
            202,
            now=self.now,
        )

        list_activities.assert_called_once_with(
            conn,
            202,
            now=self.now,
        )


if __name__ == "__main__":
    unittest.main()
