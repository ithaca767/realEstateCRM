import unittest
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from activity_engine import (
    activity_key,
    classify_due,
    make_activity,
    to_new_york,
)


NY = ZoneInfo("America/New_York")


class ActivityEngineTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 20, 14, 0, tzinfo=NY)

    def test_activity_key_preserves_source_identity(self):
        self.assertEqual(activity_key("followup", 42), "followup:42")
        self.assertEqual(activity_key("task", 7), "task:7")
        self.assertEqual(
            activity_key("transaction_deadline", 3),
            "transaction_deadline:3",
        )

    def test_activity_key_rejects_invalid_source(self):
        with self.assertRaises(ValueError):
            activity_key("mystery", 1)

    def test_activity_key_rejects_invalid_id(self):
        with self.assertRaises(ValueError):
            activity_key("task", 0)

    def test_to_new_york_requires_aware_datetime(self):
        with self.assertRaises(ValueError):
            to_new_york(datetime(2026, 9, 20, 14, 0))

    def test_to_new_york_converts_utc_instant(self):
        value = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)
        converted = to_new_york(value)

        self.assertEqual(converted.hour, 14)
        self.assertEqual(converted.tzinfo, NY)

    def test_timestamp_before_now_is_overdue(self):
        result = classify_due(
            due_at=datetime(2026, 9, 20, 13, 59, tzinfo=NY),
            now=self.now,
        )

        self.assertTrue(result["is_overdue"])
        self.assertFalse(result["is_today"])
        self.assertFalse(result["is_upcoming"])

    def test_timestamp_later_today_is_today(self):
        result = classify_due(
            due_at=datetime(2026, 9, 20, 16, 0, tzinfo=NY),
            now=self.now,
        )

        self.assertFalse(result["is_overdue"])
        self.assertTrue(result["is_today"])
        self.assertFalse(result["is_upcoming"])

    def test_future_timestamp_is_upcoming(self):
        result = classify_due(
            due_at=datetime(2026, 9, 21, 9, 0, tzinfo=NY),
            now=self.now,
        )

        self.assertFalse(result["is_overdue"])
        self.assertFalse(result["is_today"])
        self.assertTrue(result["is_upcoming"])

    def test_date_before_today_is_overdue(self):
        result = classify_due(
            due_date=date(2026, 9, 19),
            now=self.now,
        )

        self.assertTrue(result["is_overdue"])

    def test_date_today_is_today_not_overdue(self):
        result = classify_due(
            due_date=date(2026, 9, 20),
            now=self.now,
        )

        self.assertFalse(result["is_overdue"])
        self.assertTrue(result["is_today"])

    def test_future_date_is_upcoming(self):
        result = classify_due(
            due_date=date(2026, 9, 21),
            now=self.now,
        )

        self.assertTrue(result["is_upcoming"])

    def test_timestamp_classification_uses_now_timezone_calendar_day(self):
        pacific = ZoneInfo("America/Los_Angeles")
        now = datetime(2026, 9, 19, 22, 30, tzinfo=pacific)

        result = classify_due(
            due_at=datetime(2026, 9, 20, 6, 0, tzinfo=timezone.utc),
            now=now,
        )

        self.assertFalse(result["is_overdue"])
        self.assertTrue(result["is_today"])
        self.assertFalse(result["is_upcoming"])

    def test_date_only_classification_uses_now_timezone_calendar_day(self):
        pacific = ZoneInfo("America/Los_Angeles")
        now = datetime(2026, 9, 19, 22, 30, tzinfo=pacific)

        result = classify_due(
            due_date=date(2026, 9, 19),
            now=now,
        )

        self.assertFalse(result["is_overdue"])
        self.assertTrue(result["is_today"])
        self.assertFalse(result["is_upcoming"])

    def test_undated_activity_has_no_due_bucket(self):
        result = classify_due(now=self.now)

        self.assertFalse(result["is_overdue"])
        self.assertFalse(result["is_today"])
        self.assertFalse(result["is_upcoming"])

    def test_cannot_supply_date_and_timestamp(self):
        with self.assertRaises(ValueError):
            classify_due(
                due_at=datetime(2026, 9, 20, 16, 0, tzinfo=NY),
                due_date=date(2026, 9, 20),
                now=self.now,
            )

    def test_make_activity_normalizes_contract(self):
        activity = make_activity(
            activity_type="followup",
            source_id=42,
            title="Call Tyler",
            description="Discuss inspection.",
            contact_id=100,
            contact_name="Tyler Ely",
            due_at=datetime(2026, 9, 20, 16, 0, tzinfo=NY),
            now=self.now,
            calendar_eligible=True,
            target_url="/engagements/42/edit",
        )

        self.assertEqual(activity["activity_key"], "followup:42")
        self.assertEqual(activity["source_id"], 42)
        self.assertEqual(activity["contact_id"], 100)
        self.assertEqual(activity["contact_name"], "Tyler Ely")
        self.assertTrue(activity["is_today"])
        self.assertFalse(activity["is_overdue"])
        self.assertTrue(activity["calendar_eligible"])


if __name__ == "__main__":
    unittest.main()


class FollowupActivityDatabaseTests(unittest.TestCase):
    class FakeCursor:
        def __init__(self, rows):
            self.rows = rows
            self.sql = None
            self.params = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params):
            self.sql = sql
            self.params = params

        def fetchall(self):
            return self.rows

    class FakeConnection:
        def __init__(self, rows):
            self.cursor_instance = FollowupActivityDatabaseTests.FakeCursor(rows)

        def cursor(self, **kwargs):
            return self.cursor_instance

    def setUp(self):
        self.now = datetime(2026, 9, 20, 14, 0, tzinfo=NY)

    def test_followup_reader_normalizes_source_record(self):
        from activity_engine import list_followup_activities

        conn = self.FakeConnection(
            [
                {
                    "source_id": 42,
                    "contact_id": 100,
                    "contact_name": "Tyler Ely",
                    "due_at": datetime(
                        2026, 9, 20, 16, 0, tzinfo=timezone.utc
                    ),
                    "outcome": "",
                    "summary_clean": "",
                    "notes": "",
                    "engagement_type": "follow_up",
                    "parent_outcome": "Discuss inspection results",
                    "parent_summary_clean": "",
                    "parent_notes": "",
                    "parent_engagement_type": "call",
                }
            ]
        )

        activities = list_followup_activities(
            conn,
            7,
            now=self.now,
        )

        self.assertEqual(len(activities), 1)

        activity = activities[0]

        self.assertEqual(activity["activity_key"], "followup:42")
        self.assertEqual(activity["source_id"], 42)
        self.assertEqual(activity["contact_id"], 100)
        self.assertEqual(activity["contact_name"], "Tyler Ely")
        self.assertEqual(activity["title"], "Follow up with Tyler Ely")
        self.assertEqual(
            activity["description"],
            "follow_up",
        )
        self.assertTrue(activity["calendar_eligible"])
        self.assertEqual(
            conn.cursor_instance.params,
            (7,),
        )

    def test_followup_reader_prefers_child_content(self):
        from activity_engine import list_followup_activities

        conn = self.FakeConnection(
            [
                {
                    "source_id": 55,
                    "contact_id": 101,
                    "contact_name": "Gabby Shields",
                    "due_at": datetime(
                        2026, 9, 21, 15, 0, tzinfo=timezone.utc
                    ),
                    "outcome": "Call about lender update",
                    "summary_clean": "Other child summary",
                    "notes": "",
                    "engagement_type": "follow_up",
                    "parent_outcome": "Older parent context",
                    "parent_summary_clean": "",
                    "parent_notes": "",
                    "parent_engagement_type": "call",
                }
            ]
        )

        activities = list_followup_activities(
            conn,
            7,
            now=self.now,
        )

        self.assertEqual(
            activities[0]["description"],
            "Call about lender update",
        )

    def test_followup_reader_rejects_missing_user(self):
        from activity_engine import list_followup_activities

        conn = self.FakeConnection([])

        with self.assertRaises(ValueError):
            list_followup_activities(
                conn,
                0,
                now=self.now,
            )


class TaskActivityDatabaseTests(unittest.TestCase):
    class FakeCursor:
        def __init__(self, rows):
            self.rows = rows
            self.sql = None
            self.params = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params):
            self.sql = sql
            self.params = params

        def fetchall(self):
            return self.rows

    class FakeConnection:
        def __init__(self, rows):
            self.cursor_instance = TaskActivityDatabaseTests.FakeCursor(rows)

        def cursor(self, **kwargs):
            return self.cursor_instance

    def setUp(self):
        self.now = datetime(2026, 9, 20, 14, 0, tzinfo=NY)

    def test_timestamp_task_normalizes_as_activity(self):
        from activity_engine import list_task_activities

        conn = self.FakeConnection(
            [
                {
                    "source_id": 10,
                    "contact_id": 100,
                    "transaction_id": 200,
                    "engagement_id": None,
                    "title": "Call lender",
                    "description": "Get commitment update",
                    "task_type": "call",
                    "status": "open",
                    "priority": "high",
                    "due_date": None,
                    "due_at": datetime(
                        2026, 9, 20, 19, 0, tzinfo=timezone.utc
                    ),
                    "snoozed_until": None,
                    "contact_name": "Tyler Ely",
                }
            ]
        )

        activities = list_task_activities(
            conn,
            7,
            now=self.now,
        )

        self.assertEqual(len(activities), 1)
        activity = activities[0]

        self.assertEqual(activity["activity_key"], "task:10")
        self.assertEqual(activity["title"], "Call lender")
        self.assertEqual(activity["contact_id"], 100)
        self.assertEqual(activity["transaction_id"], 200)
        self.assertEqual(activity["priority"], "high")
        self.assertTrue(activity["is_today"])
        self.assertIsNone(activity["due_date"])
        self.assertIsNotNone(activity["due_at"])
        self.assertFalse(activity["calendar_eligible"])

    def test_date_only_task_preserves_date_semantics(self):
        from activity_engine import list_task_activities

        conn = self.FakeConnection(
            [
                {
                    "source_id": 11,
                    "contact_id": None,
                    "transaction_id": None,
                    "engagement_id": None,
                    "title": "Review file",
                    "description": "",
                    "task_type": None,
                    "status": "open",
                    "priority": None,
                    "due_date": date(2026, 9, 20),
                    "due_at": None,
                    "snoozed_until": None,
                    "contact_name": "(Unnamed contact)",
                }
            ]
        )

        activities = list_task_activities(
            conn,
            7,
            now=self.now,
        )

        activity = activities[0]

        self.assertEqual(activity["due_date"], date(2026, 9, 20))
        self.assertIsNone(activity["due_at"])
        self.assertTrue(activity["is_today"])
        self.assertFalse(activity["is_overdue"])

    def test_task_reader_passes_user_and_now_to_query(self):
        from activity_engine import list_task_activities

        conn = self.FakeConnection([])

        list_task_activities(
            conn,
            7,
            now=self.now,
        )

        self.assertEqual(
            conn.cursor_instance.params,
            (7, self.now),
        )

    def test_task_reader_sql_has_no_account_timezone_assumption(self):
        from activity_engine import list_task_activities

        conn = self.FakeConnection([])

        list_task_activities(
            conn,
            7,
            now=self.now,
        )

        self.assertNotIn(
            "America/New_York",
            conn.cursor_instance.sql,
        )

    def test_task_reader_rejects_missing_user(self):
        from activity_engine import list_task_activities

        conn = self.FakeConnection([])

        with self.assertRaises(ValueError):
            list_task_activities(
                conn,
                0,
                now=self.now,
            )


class TransactionDeadlineActivityDatabaseTests(unittest.TestCase):
    class FakeCursor:
        def __init__(self, rows):
            self.rows = rows
            self.params = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params):
            self.params = params

        def fetchall(self):
            return self.rows

    class FakeConnection:
        def __init__(self, rows):
            self.cursor_instance = (
                TransactionDeadlineActivityDatabaseTests.FakeCursor(rows)
            )

        def cursor(self, **kwargs):
            return self.cursor_instance

    def setUp(self):
        self.now = datetime(2026, 9, 20, 14, 0, tzinfo=NY)

    def test_deadline_normalizes_as_date_only_activity(self):
        from activity_engine import list_transaction_deadline_activities

        conn = self.FakeConnection(
            [
                {
                    "source_id": 3,
                    "transaction_id": 200,
                    "name": "Mortgage commitment",
                    "due_date": date(2026, 9, 20),
                    "notes": "Confirm with lender.",
                    "contact_id": 100,
                    "contact_name": "Tyler Ely",
                }
            ]
        )

        activities = list_transaction_deadline_activities(
            conn,
            7,
            now=self.now,
        )

        self.assertEqual(len(activities), 1)

        activity = activities[0]

        self.assertEqual(
            activity["activity_key"],
            "transaction_deadline:3",
        )
        self.assertEqual(
            activity["title"],
            "Mortgage commitment",
        )
        self.assertEqual(
            activity["description"],
            "Confirm with lender.",
        )
        self.assertEqual(activity["transaction_id"], 200)
        self.assertEqual(activity["contact_id"], 100)
        self.assertEqual(activity["due_date"], date(2026, 9, 20))
        self.assertIsNone(activity["due_at"])
        self.assertTrue(activity["is_today"])
        self.assertFalse(activity["is_overdue"])
        self.assertTrue(activity["calendar_eligible"])

    def test_deadline_reader_passes_user_to_query(self):
        from activity_engine import list_transaction_deadline_activities

        conn = self.FakeConnection([])

        list_transaction_deadline_activities(
            conn,
            7,
            now=self.now,
        )

        self.assertEqual(
            conn.cursor_instance.params,
            (7,),
        )

    def test_deadline_reader_rejects_missing_user(self):
        from activity_engine import list_transaction_deadline_activities

        conn = self.FakeConnection([])

        with self.assertRaises(ValueError):
            list_transaction_deadline_activities(
                conn,
                0,
                now=self.now,
            )


class UnifiedActivityListTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 20, 14, 0, tzinfo=NY)

    def test_sort_key_does_not_change_date_only_activity(self):
        from activity_engine import _activity_sort_key

        activity = {
            "activity_type": "task",
            "source_id": 1,
            "due_date": date(2026, 9, 20),
            "due_at": None,
        }

        original_due_date = activity["due_date"]

        key = _activity_sort_key(activity)

        self.assertEqual(
            activity["due_date"],
            original_due_date,
        )
        self.assertIsNone(activity["due_at"])
        self.assertEqual(
            key[0],
            datetime(2026, 9, 20, 0, 0, tzinfo=NY),
        )

    def test_sort_key_uses_now_timezone_for_date_only_surrogate(self):
        from activity_engine import _activity_sort_key

        pacific = ZoneInfo("America/Los_Angeles")
        now = datetime(2026, 9, 19, 22, 30, tzinfo=pacific)

        activity = {
            "activity_type": "task",
            "source_id": 9,
            "due_date": date(2026, 9, 20),
            "due_at": None,
        }

        key = _activity_sort_key(activity, now=now)

        self.assertEqual(
            key[0],
            datetime(2026, 9, 20, 0, 0, tzinfo=pacific),
        )
        self.assertEqual(activity["due_date"], date(2026, 9, 20))
        self.assertIsNone(activity["due_at"])

    def test_timestamp_sorting_uses_new_york_instant(self):
        from activity_engine import _activity_sort_key

        activity = {
            "activity_type": "followup",
            "source_id": 2,
            "due_date": None,
            "due_at": datetime(
                2026, 9, 20, 18, 30, tzinfo=timezone.utc
            ),
        }

        key = _activity_sort_key(activity)

        self.assertEqual(
            key[0],
            datetime(2026, 9, 20, 14, 30, tzinfo=NY),
        )

    def test_unified_list_combines_deduplicates_and_sorts(self):
        from unittest.mock import patch

        from activity_engine import list_activities

        followups = [
            {
                "activity_key": "followup:5",
                "activity_type": "followup",
                "source_id": 5,
                "due_date": None,
                "due_at": datetime(
                    2026, 9, 21, 13, 0, tzinfo=timezone.utc
                ),
            }
        ]

        tasks = [
            {
                "activity_key": "task:2",
                "activity_type": "task",
                "source_id": 2,
                "due_date": date(2026, 9, 20),
                "due_at": None,
            },
            {
                "activity_key": "task:2",
                "activity_type": "task",
                "source_id": 2,
                "due_date": date(2026, 9, 20),
                "due_at": None,
            },
        ]

        deadlines = [
            {
                "activity_key": "transaction_deadline:3",
                "activity_type": "transaction_deadline",
                "source_id": 3,
                "due_date": date(2026, 9, 22),
                "due_at": None,
            }
        ]

        with (
            patch(
                "activity_engine.list_followup_activities",
                return_value=followups,
            ),
            patch(
                "activity_engine.list_task_activities",
                return_value=tasks,
            ),
            patch(
                "activity_engine.list_transaction_deadline_activities",
                return_value=deadlines,
            ),
        ):
            activities = list_activities(
                object(),
                7,
                now=self.now,
            )

        self.assertEqual(
            [a["activity_key"] for a in activities],
            [
                "task:2",
                "followup:5",
                "transaction_deadline:3",
            ],
        )

        self.assertEqual(len(activities), 3)

    def test_unified_list_rejects_missing_user(self):
        from activity_engine import list_activities

        with self.assertRaises(ValueError):
            list_activities(
                object(),
                0,
                now=self.now,
            )

    def test_unified_list_rejects_naive_now(self):
        from activity_engine import list_activities

        with self.assertRaises(ValueError):
            list_activities(
                object(),
                7,
                now=datetime(2026, 9, 20, 14, 0),
            )


class DashboardActivityAdapterTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 20, 14, 0, tzinfo=NY)

    def test_dashboard_list_includes_only_overdue_and_today(self):
        from unittest.mock import patch

        from activity_engine import list_dashboard_activities

        activities = [
            {
                "activity_key": "task:1",
                "is_overdue": True,
                "is_today": False,
            },
            {
                "activity_key": "task:2",
                "is_overdue": False,
                "is_today": True,
            },
            {
                "activity_key": "task:3",
                "is_overdue": False,
                "is_today": False,
                "is_upcoming": True,
            },
        ]

        with patch(
            "activity_engine.list_activities",
            return_value=activities,
        ):
            result = list_dashboard_activities(
                object(),
                7,
                now=self.now,
            )

        self.assertEqual(
            [item["activity_key"] for item in result],
            ["task:1", "task:2"],
        )

    def test_followup_adapts_to_existing_dashboard_contract(self):
        from activity_engine import dashboard_snapshot_item

        due = datetime(
            2026, 9, 19, 18, 30, tzinfo=timezone.utc
        )

        activity = {
            "activity_key": "followup:88",
            "activity_type": "followup",
            "source_type": "followup",
            "source_id": 88,
            "title": "Follow up with Olivia Quinn",
            "description": "Call Olivia",
            "contact_id": 10,
            "contact_name": "Olivia Quinn",
            "transaction_id": None,
            "due_date": None,
            "due_at": due,
            "status": "open",
            "priority": None,
            "is_overdue": True,
            "is_today": False,
            "is_upcoming": False,
            "calendar_eligible": True,
            "target_url": "/engagements/88/edit",
        }

        item = dashboard_snapshot_item(
            activity,
            now=self.now,
        )

        self.assertEqual(item["item_type"], "followup")
        self.assertEqual(item["engagement_id"], 88)
        self.assertEqual(item["follow_up_due_at"], due)
        self.assertEqual(item["snap_status"], "overdue")
        self.assertEqual(item["overdue_days"], 1)
        self.assertEqual(item["snippet"], "Call Olivia")

    def test_dashboard_overdue_days_uses_now_timezone_calendar_day(self):
        from activity_engine import dashboard_snapshot_item

        pacific = ZoneInfo("America/Los_Angeles")
        now = datetime(2026, 9, 20, 0, 30, tzinfo=pacific)
        due = datetime(2026, 9, 20, 6, 30, tzinfo=timezone.utc)

        activity = {
            "activity_key": "followup:99",
            "activity_type": "followup",
            "source_type": "followup",
            "source_id": 99,
            "title": "Follow up",
            "description": "",
            "contact_id": 10,
            "contact_name": "Test Contact",
            "transaction_id": None,
            "due_date": None,
            "due_at": due,
            "status": "open",
            "priority": None,
            "is_overdue": True,
            "is_today": False,
            "is_upcoming": False,
            "calendar_eligible": True,
            "target_url": "/engagements/99/edit",
        }

        item = dashboard_snapshot_item(activity, now=now)

        self.assertEqual(
            due.astimezone(pacific),
            datetime(2026, 9, 19, 23, 30, tzinfo=pacific),
        )
        self.assertEqual(item["snap_status"], "overdue")
        self.assertEqual(item["overdue_days"], 1)
        self.assertEqual(item["follow_up_due_at"], due)

    def test_date_only_task_stays_date_only_in_dashboard_adapter(self):
        from activity_engine import dashboard_snapshot_item

        activity = {
            "activity_key": "task:21",
            "activity_type": "task",
            "source_type": "task",
            "source_id": 21,
            "title": "Another SNOOZE test",
            "description": "",
            "contact_id": None,
            "contact_name": None,
            "transaction_id": None,
            "due_date": date(2026, 9, 19),
            "due_at": None,
            "status": "snoozed",
            "priority": None,
            "is_overdue": True,
            "is_today": False,
            "is_upcoming": False,
            "calendar_eligible": False,
            "target_url": "/tasks/21",
        }

        item = dashboard_snapshot_item(
            activity,
            now=self.now,
        )

        self.assertEqual(item["item_type"], "task")
        self.assertEqual(item["task_id"], 21)
        self.assertEqual(item["due_date"], date(2026, 9, 19))
        self.assertIsNone(item["due_at"])
        self.assertIsNone(item["due_ts"])
        self.assertEqual(item["overdue_days"], 1)

    def test_transaction_deadline_adapts_for_dashboard(self):
        from activity_engine import dashboard_snapshot_item

        activity = {
            "activity_key": "transaction_deadline:3",
            "activity_type": "transaction_deadline",
            "source_type": "transaction_deadline",
            "source_id": 3,
            "title": "Mortgage commitment",
            "description": "Confirm with lender",
            "contact_id": 100,
            "contact_name": "Tyler Ely",
            "transaction_id": 200,
            "due_date": date(2026, 9, 20),
            "due_at": None,
            "status": "open",
            "priority": None,
            "is_overdue": False,
            "is_today": True,
            "is_upcoming": False,
            "calendar_eligible": True,
            "target_url": "/transactions/200/edit",
        }

        item = dashboard_snapshot_item(
            activity,
            now=self.now,
        )

        self.assertEqual(
            item["item_type"],
            "transaction_deadline",
        )
        self.assertEqual(item["deadline_id"], 3)
        self.assertEqual(item["transaction_id"], 200)
        self.assertEqual(item["due_date"], date(2026, 9, 20))
        self.assertEqual(item["snap_status"], "today")
        self.assertEqual(item["overdue_days"], 0)
        self.assertEqual(item["snippet"], "Confirm with lender")

    def test_dashboard_snapshot_items_uses_adapter(self):
        from unittest.mock import patch

        from activity_engine import list_dashboard_snapshot_items

        activity = {
            "activity_key": "task:5",
            "activity_type": "task",
            "source_type": "task",
            "source_id": 5,
            "title": "Call attorney",
            "description": "",
            "contact_id": None,
            "contact_name": None,
            "transaction_id": None,
            "due_date": date(2026, 9, 20),
            "due_at": None,
            "status": "open",
            "priority": None,
            "is_overdue": False,
            "is_today": True,
            "is_upcoming": False,
            "calendar_eligible": False,
            "target_url": "/tasks/5",
        }

        with patch(
            "activity_engine.list_dashboard_activities",
            return_value=[activity],
        ):
            result = list_dashboard_snapshot_items(
                object(),
                7,
                now=self.now,
            )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["item_type"], "task")
        self.assertEqual(result[0]["task_id"], 5)
        self.assertEqual(result[0]["snap_status"], "today")
