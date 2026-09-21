import unittest
from unittest.mock import MagicMock, patch

import app as app_module
from push_subscriptions import (
    deactivate_push_subscription,
    save_push_subscription,
)


class TenantBoundaryAdversarialTests(unittest.TestCase):
    """
    Final architectural tenant-boundary tests.

    User 101 is the authenticated tenant. User 202 represents another tenant.
    The authenticated user is deliberately given the owner role to prove that
    owner/admin privilege does not imply cross-tenant CRM access.
    """

    def setUp(self):
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "tenant-boundary-test-secret"
        self.client = app_module.app.test_client()
        self.original_user_callback = app_module.login_manager._user_callback

    def tearDown(self):
        app_module.login_manager._user_callback = self.original_user_callback

    def login_as_owner(self, user_id=101):
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
                user if str(requested_user_id) == str(user_id) else None
            )
        )
        with self.client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True

    @patch("app.get_db")
    def test_owner_cannot_export_foreign_activepipe_contact(self, mock_get_db):
        self.login_as_owner(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None
        mock_get_db.return_value = conn

        response = self.client.get(
            "/integrations/activepipe/contact/202/export.csv"
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(cur.execute.call_count, 1)

        sql, params = cur.execute.call_args.args
        normalized = " ".join(sql.split())
        self.assertIn("FROM contacts", normalized)
        self.assertIn("WHERE id = %s AND user_id = %s", normalized)
        self.assertEqual(params, (202, 101))

        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owner_bulk_activepipe_export_is_tenant_scoped(self, mock_get_db):
        self.login_as_owner(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchall.return_value = []
        mock_get_db.return_value = conn

        response = self.client.get("/integrations/activepipe/export.csv")

        self.assertEqual(response.status_code, 200)

        sql, params = cur.execute.call_args_list[0].args
        normalized = " ".join(sql.split())

        self.assertIn("FROM contacts c", normalized)
        self.assertIn("ci.user_id = c.user_id", normalized)
        self.assertIn("ci.contact_id = c.id", normalized)
        self.assertIn("WHERE c.user_id = %s", normalized)
        self.assertEqual(params, (101,))

        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owner_cannot_export_foreign_open_house(self, mock_get_db):
        self.login_as_owner(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None
        mock_get_db.return_value = conn

        response = self.client.get("/openhouses/202/export.csv")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(cur.execute.call_count, 1)

        sql, params = cur.execute.call_args.args
        normalized = " ".join(sql.split())

        self.assertIn("FROM open_houses", normalized)
        self.assertIn("id = %s", normalized)
        self.assertIn("created_by_user_id = %s", normalized)
        self.assertEqual(params, (202, 101))

        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_public_open_house_token_derives_owner_for_contact_lookup(
        self,
        mock_get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        mock_get_db.return_value = conn

        cur.fetchone.side_effect = [
            {
                "id": 77,
                "created_by_user_id": 202,
                "address_line1": "1 Main Street",
                "city": "Keyport",
                "state": "NJ",
                "zip": "07735",
                "start_datetime": None,
                "end_datetime": None,
                "house_photo_url": None,
                "archived_at": None,
            },
            {"id": 303},
        ]

        response = self.client.post(
            "/openhouse/public-token-for-user-202",
            data={
                "first_name": "Other",
                "last_name": "Tenant",
                "email": "other@example.com",
                "phone": "",
            },
        )

        self.assertEqual(response.status_code, 302)

        contact_lookup = cur.execute.call_args_list[1]
        sql, params = contact_lookup.args
        normalized = " ".join(sql.split())

        self.assertIn("FROM contacts", normalized)
        self.assertIn("WHERE user_id = %s", normalized)
        self.assertEqual(params[0], 202)

        signin_calls = [
            call
            for call in cur.execute.call_args_list
            if call.args
            and "INSERT INTO open_house_signins" in call.args[0]
        ]
        self.assertEqual(len(signin_calls), 1)
        signin_params = signin_calls[0].args[1]
        self.assertEqual(signin_params[0], 77)
        self.assertEqual(signin_params[1], 202)

        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_newsletter_token_derives_owner_for_contact_lookup(
        self,
        mock_get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        mock_get_db.return_value = conn

        cur.fetchone.side_effect = [
            {
                "id": 88,
                "created_by_user_id": 202,
                "title": "Newsletter",
                "redirect_url": None,
                "is_active": True,
            },
            {"id": 404},
        ]

        response = self.client.post(
            "/newsletter/signup/public-token-for-user-202",
            data={
                "first_name": "Other",
                "last_name": "Tenant",
                "email": "other@example.com",
            },
        )

        self.assertEqual(response.status_code, 302)

        contact_lookup = cur.execute.call_args_list[1]
        sql, params = contact_lookup.args
        normalized = " ".join(sql.split())

        self.assertIn("FROM contacts", normalized)
        self.assertIn("WHERE user_id = %s", normalized)
        self.assertEqual(params, (202, "other@example.com"))

        engagement_calls = [
            call
            for call in cur.execute.call_args_list
            if call.args
            and "INSERT INTO engagements" in call.args[0]
        ]
        self.assertEqual(len(engagement_calls), 1)
        engagement_params = engagement_calls[0].args[1]
        self.assertEqual(engagement_params[0], 202)
        self.assertEqual(engagement_params[1], 404)

        conn.commit.assert_called_once()
        conn.close.assert_called_once()


class PushSubscriptionTenantBoundaryTests(unittest.TestCase):

    def test_user_cannot_claim_endpoint_owned_by_another_tenant(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cur

        # Endpoint already belongs to user 202.
        cur.fetchone.return_value = {
            "id": 77,
            "user_id": 202,
        }

        endpoint = "https://push.example/foreign-endpoint"

        with self.assertRaises(ValueError):
            save_push_subscription(
                conn,
                user_id=101,
                endpoint=endpoint,
                p256dh="p256dh",
                auth="auth",
            )

        sql, params = cur.execute.call_args_list[0].args
        normalized = " ".join(sql.split())

        self.assertIn("FROM push_subscriptions", normalized)
        self.assertIn("WHERE endpoint = %s", normalized)
        self.assertEqual(params, (endpoint,))

        # The ownership check must stop the INSERT/UPSERT entirely.
        self.assertEqual(cur.execute.call_count, 1)

    def test_user_cannot_deactivate_another_tenants_endpoint(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cur
        cur.fetchone.return_value = None

        endpoint = "https://push.example/foreign-endpoint"

        result = deactivate_push_subscription(
            conn,
            user_id=101,
            endpoint=endpoint,
        )

        self.assertIsNone(result)

        sql, params = cur.execute.call_args.args
        normalized = " ".join(sql.split())

        self.assertIn("UPDATE push_subscriptions", normalized)
        self.assertIn("user_id = %s", normalized)
        self.assertIn("endpoint = %s", normalized)
        self.assertEqual(params, (101, endpoint))


if __name__ == "__main__":
    unittest.main()
