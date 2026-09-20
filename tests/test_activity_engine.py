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
