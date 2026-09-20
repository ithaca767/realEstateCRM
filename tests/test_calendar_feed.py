import unittest
from unittest.mock import MagicMock, patch

from calendar_feed import (
    create_calendar_feed_token,
    resolve_calendar_feed_token,
    revoke_calendar_feed_token,
)


class CalendarFeedTokenTests(unittest.TestCase):
    @patch("calendar_feed.hash_token", return_value="hashed-token")
    @patch("calendar_feed.generate_raw_token", return_value="raw-token")
    def test_create_token_belongs_to_supplied_user(
        self,
        generate_raw_token,
        hash_token,
    ):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = {
            "id": 17,
            "user_id": 101,
            "created_at": "created",
        }

        result = create_calendar_feed_token(conn, 101)

        self.assertEqual(result["user_id"], 101)
        self.assertEqual(result["raw_token"], "raw-token")
        self.assertNotIn("token_hash", result)
        conn.commit.assert_called_once()

        insert_call = cur.execute.call_args_list[1]
        self.assertEqual(insert_call.args[1], (101, "hashed-token"))

    @patch("calendar_feed.hash_token", return_value="hashed-token")
    def test_resolve_token_returns_only_credential_owner(self, hash_token):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = [
            {
                "calendar_feed_token_id": 22,
                "user_id": 101,
                "timezone_name": "America/New_York",
            }
        ]

        result = resolve_calendar_feed_token(conn, "raw-token")

        self.assertEqual(result["user_id"], 101)
        self.assertEqual(result["timezone_name"], "America/New_York")

        sql = cur.execute.call_args.args[0]
        params = cur.execute.call_args.args[1]

        self.assertIn("cft.token_hash = %s", sql)
        self.assertIn("cft.revoked_at IS NULL", sql)
        self.assertIn("u.is_active = TRUE", sql)
        self.assertNotIn("user_id = %s", sql)
        self.assertEqual(params, ("hashed-token",))

    @patch("calendar_feed.hash_token", return_value="hashed-token")
    def test_resolve_rejects_no_matching_owner(self, hash_token):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = []

        self.assertIsNone(resolve_calendar_feed_token(conn, "raw-token"))

    @patch("calendar_feed.hash_token", return_value="hashed-token")
    def test_resolve_rejects_ambiguous_owner(self, hash_token):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = [
            {
                "calendar_feed_token_id": 22,
                "user_id": 101,
                "timezone_name": "America/New_York",
            },
            {
                "calendar_feed_token_id": 23,
                "user_id": 202,
                "timezone_name": "America/Los_Angeles",
            },
        ]

        self.assertIsNone(resolve_calendar_feed_token(conn, "raw-token"))

    def test_resolve_blank_token_does_not_query_database(self):
        conn = MagicMock()

        self.assertIsNone(resolve_calendar_feed_token(conn, "   "))
        conn.cursor.assert_not_called()

    def test_revoke_scopes_to_exact_user(self):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.rowcount = 1

        self.assertTrue(revoke_calendar_feed_token(conn, 101))

        sql = cur.execute.call_args.args[0]
        params = cur.execute.call_args.args[1]

        self.assertIn("user_id = %s", sql)
        self.assertIn("revoked_at IS NULL", sql)
        self.assertEqual(params[1], 101)
        conn.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
