import unittest
from unittest.mock import MagicMock, patch

import app as app_module


class TenantIsolationTests(unittest.TestCase):

    def setUp(self):
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "tenant-isolation-test-secret"
        self.client = app_module.app.test_client()
        self.original_user_callback = app_module.login_manager._user_callback

    def tearDown(self):
        app_module.login_manager._user_callback = self.original_user_callback

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
    def test_user_cannot_add_interaction_to_another_users_contact(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        # Ownership lookup fails: contact belongs to another tenant
        # or does not exist. Both must be indistinguishable here.
        cur.fetchone.return_value = None
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.post(
            "/add_interaction/202",
            data={
                "kind": "call",
                "happened_at": "2026-09-20",
                "notes": "must never be written",
            },
        )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(cur.execute.call_count, 1)
        sql, params = cur.execute.call_args.args

        self.assertIn("FROM contacts", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(params, (202, 101))

        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_user_can_add_interaction_to_owned_contact(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        # Ownership lookup succeeds.
        cur.fetchone.return_value = {"id": 55}
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.post(
            "/add_interaction/55",
            data={
                "kind": "call",
                "happened_at": "2026-09-20",
                "notes": "owned contact",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(cur.execute.call_count, 2)

        ownership_sql, ownership_params = cur.execute.call_args_list[0].args
        insert_sql, insert_params = cur.execute.call_args_list[1].args

        self.assertIn("FROM contacts", ownership_sql)
        self.assertIn("user_id = %s", ownership_sql)
        self.assertEqual(ownership_params, (55, 101))

        self.assertIn("INSERT INTO interactions", insert_sql)
        self.assertEqual(insert_params[0], 101)
        self.assertEqual(insert_params[1], 55)

        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_user_cannot_delete_another_users_interaction(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        # Tenant-scoped lookup cannot see another user's interaction.
        cur.fetchone.return_value = None
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.get("/delete_interaction/909")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(cur.execute.call_count, 1)

        sql, params = cur.execute.call_args.args
        self.assertIn("FROM interactions", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(params, (909, 101))

        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owned_interaction_delete_is_tenant_scoped(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        cur.fetchone.return_value = {"contact_id": 55}
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.get("/delete_interaction/77")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(cur.execute.call_count, 2)

        lookup_sql, lookup_params = cur.execute.call_args_list[0].args
        delete_sql, delete_params = cur.execute.call_args_list[1].args

        self.assertIn("FROM interactions", lookup_sql)
        self.assertIn("user_id = %s", lookup_sql)
        self.assertEqual(lookup_params, (77, 101))

        self.assertIn("DELETE FROM interactions", delete_sql)
        self.assertIn("user_id = %s", delete_sql)
        self.assertEqual(delete_params, (77, 101))

        conn.commit.assert_called_once()
        conn.close.assert_called_once()


class DashboardTenantIsolationTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "tenant-isolation-test-secret"
        self.client = app_module.app.test_client()
        self.original_user_callback = app_module.login_manager._user_callback

    def tearDown(self):
        app_module.login_manager._user_callback = self.original_user_callback

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

    def test_dashboard_fails_closed_when_contacts_user_id_is_missing(self):
        self.login_as(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        # First has_column() check is contacts.user_id.
        cur.fetchone.return_value = None

        with patch("app.get_db", return_value=conn):
            with self.assertRaisesRegex(
                RuntimeError,
                "Dashboard tenant-isolation schema is incomplete",
            ):
                self.client.get("/")

        executed = cur.execute.call_args_list
        self.assertEqual(len(executed), 2)

        sql, params = executed[0].args
        self.assertIn("information_schema.columns", sql)
        self.assertEqual(params, ("contacts", "user_id"))

        # Most importantly, schema failure must not broaden into tenant data.
        all_sql = "\n".join(
            call.args[0] for call in executed if call.args
        )
        self.assertNotIn("SELECT COUNT(*) AS cnt FROM contacts", all_sql)
        self.assertNotIn("FROM engagements e", all_sql)
        conn.close.assert_called_once()

    def test_dashboard_fails_closed_when_engagements_user_id_is_missing(self):
        self.login_as(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        # contacts.user_id exists; engagements.user_id does not.
        cur.fetchone.side_effect = [
            {"exists": 1},
            None,
        ]

        with patch("app.get_db", return_value=conn):
            with self.assertRaisesRegex(
                RuntimeError,
                "Dashboard tenant-isolation schema is incomplete",
            ):
                self.client.get("/")

        executed = cur.execute.call_args_list
        self.assertEqual(len(executed), 2)

        first_sql, first_params = executed[0].args
        second_sql, second_params = executed[1].args

        self.assertIn("information_schema.columns", first_sql)
        self.assertEqual(first_params, ("contacts", "user_id"))
        self.assertIn("information_schema.columns", second_sql)
        self.assertEqual(second_params, ("engagements", "user_id"))

        all_sql = "\n".join(
            call.args[0] for call in executed if call.args
        )
        self.assertNotIn("SELECT COUNT(*) AS cnt FROM contacts", all_sql)
        self.assertNotIn("FROM engagements e", all_sql)
        conn.close.assert_called_once()

    def test_dashboard_contact_count_is_tenant_scoped(self):
        self.login_as(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        # Stop execution immediately after the contact count query. We only
        # need to prove the first tenant-data query is explicitly scoped.
        cur.fetchone.side_effect = [
            {"exists": 1},  # contacts.user_id
            {"exists": 1},  # engagements.user_id
            None,           # contact_state absent
            {"cnt": 0},     # total contacts
        ]
        cur.fetchall.side_effect = RuntimeError("stop after scoped count")

        with patch("app.get_db", return_value=conn):
            with self.assertRaises(RuntimeError):
                self.client.get("/")

        count_calls = [
            call
            for call in cur.execute.call_args_list
            if call.args
            and "SELECT COUNT(*) AS cnt FROM contacts" in call.args[0]
        ]

        self.assertEqual(len(count_calls), 1)

        sql, params = count_calls[0].args
        self.assertIn("WHERE user_id = %s", sql)
        self.assertEqual(params, (101,))

        all_sql = "\n".join(
            call.args[0] for call in cur.execute.call_args_list if call.args
        )
        self.assertNotIn(
            "SELECT COUNT(*) AS cnt FROM contacts\n",
            all_sql.replace("WHERE user_id = %s", ""),
        )


if __name__ == "__main__":
    unittest.main()
