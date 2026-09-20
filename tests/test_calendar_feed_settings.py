import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import app as app_module


class CalendarFeedSettingsTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "calendar-feed-test-secret"
        self.client = app_module.app.test_client()

        self.original_user_callback = (
            app_module.login_manager._user_callback
        )

    def tearDown(self):
        app_module.login_manager._user_callback = (
            self.original_user_callback
        )

    def login_as(self, user_id):
        user = app_module.User(
            {
                "id": user_id,
                "email": f"user{user_id}@example.com",
                "role": "owner",
                "is_active": True,
                "timezone_name": "America/New_York",
            }
        )

        app_module.login_manager._user_callback = (
            lambda requested_user_id: (
                user
                if str(requested_user_id) == str(user_id)
                else None
            )
        )

        with self.client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True

    @patch("app.get_db")
    def test_calendar_feed_settings_requires_login(self, get_db):
        response = self.client.get("/calendar-feed")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
        get_db.assert_not_called()

    @patch("app.render_template", return_value="calendar settings")
    @patch("app.get_db")
    def test_get_queries_only_authenticated_users_credential(
        self,
        get_db,
        render_template,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = {
            "id": 55,
            "created_at": datetime(
                2026,
                9,
                20,
                tzinfo=timezone.utc,
            ),
        }
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.get("/calendar-feed")

        self.assertEqual(response.status_code, 200)

        sql, params = cur.execute.call_args.args
        self.assertIn("FROM calendar_feed_tokens", sql)
        self.assertIn("WHERE user_id = %s", sql)
        self.assertEqual(params, (101,))

        render_template.assert_called_once()
        self.assertEqual(
            render_template.call_args.args[0],
            "account/calendar_feed.html",
        )

        conn.close.assert_called_once()

    @patch("app.build_link")
    @patch("app.create_calendar_feed_token")
    @patch("app.render_template", return_value="calendar settings")
    @patch("app.get_db")
    def test_post_creates_credential_only_for_authenticated_user(
        self,
        get_db,
        render_template,
        create_calendar_feed_token,
        build_link,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = {
            "id": 55,
            "created_at": datetime(
                2026,
                9,
                19,
                tzinfo=timezone.utc,
            ),
        }
        get_db.return_value = conn

        created_at = datetime(
            2026,
            9,
            20,
            tzinfo=timezone.utc,
        )

        create_calendar_feed_token.return_value = {
            "id": 56,
            "user_id": 101,
            "created_at": created_at,
            "raw_token": "new-user-101-token",
        }

        build_link.return_value = (
            "https://ulyssescrmpro.com/followups.ics"
            "?key=new-user-101-token"
        )

        old_base_url = app_module.app.config.get(
            "PUBLIC_BASE_URL"
        )
        app_module.app.config[
            "PUBLIC_BASE_URL"
        ] = "https://ulyssescrmpro.com"

        try:
            self.login_as(101)
            response = self.client.post("/calendar-feed")
        finally:
            app_module.app.config[
                "PUBLIC_BASE_URL"
            ] = old_base_url

        self.assertEqual(response.status_code, 200)

        create_calendar_feed_token.assert_called_once_with(
            conn,
            101,
        )

        build_link.assert_called_once_with(
            "https://ulyssescrmpro.com",
            "/followups.ics",
            "new-user-101-token",
            param_name="key",
        )

        template_kwargs = render_template.call_args.kwargs

        self.assertEqual(
            template_kwargs[
                "calendar_feed_subscription_url"
            ],
            "https://ulyssescrmpro.com/followups.ics"
            "?key=new-user-101-token",
        )

        self.assertEqual(
            template_kwargs["active_credential"]["id"],
            56,
        )

        conn.close.assert_called_once()

    @patch("app.create_calendar_feed_token")
    @patch("app.render_template", return_value="calendar settings")
    @patch("app.get_db")
    def test_missing_public_base_url_does_not_create_credential(
        self,
        get_db,
        render_template,
        create_calendar_feed_token,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None
        get_db.return_value = conn

        old_base_url = app_module.app.config.get(
            "PUBLIC_BASE_URL"
        )
        app_module.app.config["PUBLIC_BASE_URL"] = ""

        try:
            self.login_as(101)
            response = self.client.post("/calendar-feed")
        finally:
            app_module.app.config[
                "PUBLIC_BASE_URL"
            ] = old_base_url

        self.assertEqual(response.status_code, 200)
        create_calendar_feed_token.assert_not_called()
        conn.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
