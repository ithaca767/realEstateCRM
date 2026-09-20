import unittest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import app as app_module


class CalendarRouteTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    @patch("app.serialize_calendar")
    @patch("app.list_calendar_items")
    @patch("app.resolve_calendar_feed_token")
    @patch("app.get_db")
    def test_feed_uses_only_credential_owner_user_id(
        self,
        get_db,
        resolve_calendar_feed_token,
        list_calendar_items,
        serialize_calendar,
    ):
        conn = MagicMock()
        get_db.return_value = conn

        resolve_calendar_feed_token.return_value = {
            "calendar_feed_token_id": 22,
            "user_id": 101,
            "timezone_name": "America/New_York",
        }

        list_calendar_items.return_value = []
        serialize_calendar.return_value = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "END:VCALENDAR\r\n"
        )

        response = self.client.get("/followups.ics?key=user-101-token")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/calendar")

        resolve_calendar_feed_token.assert_called_once_with(
            conn,
            "user-101-token",
        )

        list_calendar_items.assert_called_once()
        args = list_calendar_items.call_args.args
        kwargs = list_calendar_items.call_args.kwargs

        self.assertIs(args[0], conn)
        self.assertEqual(args[1], 101)

        calendar_now = kwargs["now"]
        self.assertIsNotNone(calendar_now.tzinfo)
        self.assertEqual(
            getattr(calendar_now.tzinfo, "key", None),
            "America/New_York",
        )

        conn.close.assert_called_once()

    @patch("app.list_calendar_items")
    @patch("app.resolve_calendar_feed_token")
    @patch("app.get_db")
    def test_invalid_token_never_reaches_calendar_data(
        self,
        get_db,
        resolve_calendar_feed_token,
        list_calendar_items,
    ):
        conn = MagicMock()
        get_db.return_value = conn
        resolve_calendar_feed_token.return_value = None

        response = self.client.get("/followups.ics?key=invalid-token")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.mimetype, "text/plain")
        body = response.get_data(as_text=True)
        self.assertIn("Ulysses Calendar Feed Unavailable", body)
        self.assertIn("invalid or no longer active", body)
        self.assertIn("More > Calendar Feed", body)
        list_calendar_items.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_missing_token_never_opens_database(self, get_db):
        response = self.client.get("/followups.ics")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.mimetype, "text/plain")
        body = response.get_data(as_text=True)
        self.assertIn("Ulysses Calendar Feed Unavailable", body)
        self.assertIn("invalid or no longer active", body)
        self.assertIn("More > Calendar Feed", body)
        get_db.assert_not_called()

    @patch("app.serialize_calendar")
    @patch("app.list_calendar_items")
    @patch("app.resolve_calendar_feed_token")
    @patch("app.get_db")
    def test_feed_serializes_only_items_returned_for_credential_owner(
        self,
        get_db,
        resolve_calendar_feed_token,
        list_calendar_items,
        serialize_calendar,
    ):
        conn = MagicMock()
        get_db.return_value = conn

        resolve_calendar_feed_token.return_value = {
            "calendar_feed_token_id": 22,
            "user_id": 101,
            "timezone_name": "America/New_York",
        }

        owner_items = [
            {
                "activity_key": "engagement_followup:501",
                "uid": "ulysses-engagement_followup-501@ulyssescrm",
                "title": "Follow up with Owner Contact",
                "description": "",
                "target_url": "/engagement/501",
                "event_kind": "all_day",
                "start_at": None,
                "start_date": date(2026, 9, 21),
            }
        ]

        list_calendar_items.return_value = owner_items
        serialize_calendar.return_value = (
            "BEGIN:VCALENDAR\r\n"
            "SUMMARY:Follow up with Owner Contact\r\n"
            "END:VCALENDAR\r\n"
        )

        response = self.client.get("/followups.ics?key=user-101-token")

        self.assertEqual(response.status_code, 200)

        list_calendar_items.assert_called_once()
        self.assertEqual(list_calendar_items.call_args.args[1], 101)

        serialize_calendar.assert_called_once()
        serialized_items = serialize_calendar.call_args.args[0]
        self.assertIs(serialized_items, owner_items)

        body = response.get_data(as_text=True)
        self.assertIn("Owner Contact", body)
        self.assertNotIn("Other User", body)

        conn.close.assert_called_once()

    @patch("app.serialize_calendar")
    @patch("app.list_calendar_items")
    @patch("app.resolve_calendar_feed_token")
    @patch("app.get_db")
    def test_feed_uses_credential_owner_timezone_not_session_timezone(
        self,
        get_db,
        resolve_calendar_feed_token,
        list_calendar_items,
        serialize_calendar,
    ):
        conn = MagicMock()
        get_db.return_value = conn

        resolve_calendar_feed_token.return_value = {
            "calendar_feed_token_id": 44,
            "user_id": 202,
            "timezone_name": "America/Los_Angeles",
        }

        list_calendar_items.return_value = []
        serialize_calendar.return_value = (
            "BEGIN:VCALENDAR\r\n"
            "END:VCALENDAR\r\n"
        )

        response = self.client.get("/followups.ics?key=user-202-token")

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            list_calendar_items.call_args.args[1],
            202,
        )

        calendar_now = list_calendar_items.call_args.kwargs["now"]
        self.assertEqual(
            getattr(calendar_now.tzinfo, "key", None),
            "America/Los_Angeles",
        )

        conn.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
