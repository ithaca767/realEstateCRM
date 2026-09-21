import unittest
from unittest.mock import MagicMock, patch

import app as app_module
from datetime import datetime


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


class BuyerPropertyTenantIsolationTests(unittest.TestCase):
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

    def test_user_cannot_get_another_users_buyer_property(self):
        self.login_as(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None

        with patch("app.get_db", return_value=conn):
            response = self.client.get("/buyer/property/77/edit")

        self.assertEqual(response.status_code, 404)

        self.assertEqual(len(cur.execute.call_args_list), 1)
        sql, params = cur.execute.call_args_list[0].args
        self.assertIn("WHERE bp.id = %s", sql)
        self.assertIn("AND c.user_id = %s", sql)
        self.assertEqual(params, (77, 101))

        all_sql = "\n".join(
            call.args[0] for call in cur.execute.call_args_list if call.args
        )
        self.assertNotIn("UPDATE buyer_properties", all_sql)
        conn.close.assert_called_once()

    def test_user_cannot_post_another_users_buyer_property(self):
        self.login_as(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None

        with patch("app.get_db", return_value=conn):
            response = self.client.post(
                "/buyer/property/77/edit",
                data={
                    "address_line": "Other Tenant Property",
                    "city": "Keyport",
                    "state": "NJ",
                    "postal_code": "07735",
                    "offer_status": "considering",
                },
            )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(len(cur.execute.call_args_list), 1)
        sql, params = cur.execute.call_args_list[0].args
        self.assertIn("WHERE bp.id = %s", sql)
        self.assertIn("AND c.user_id = %s", sql)
        self.assertEqual(params, (77, 101))

        all_sql = "\n".join(
            call.args[0] for call in cur.execute.call_args_list if call.args
        )
        self.assertNotIn("UPDATE buyer_properties", all_sql)
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    def test_owned_buyer_property_update_is_tenant_scoped(self):
        self.login_as(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = {
            "id": 77,
            "buyer_profile_id": 55,
            "address_line": "1 Main Street",
            "city": "Keyport",
            "state": "NJ",
            "postal_code": "07735",
            "offer_status": "considering",
            "contact_id": 44,
            "first_name": "Test",
            "last_name": "Buyer",
        }

        with patch("app.get_db", return_value=conn):
            response = self.client.post(
                "/buyer/property/77/edit",
                data={
                    "address_line": "2 Main Street",
                    "city": "Keyport",
                    "state": "NJ",
                    "postal_code": "07735",
                    "offer_status": "accepted",
                },
            )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(len(cur.execute.call_args_list), 2)

        lookup_sql, lookup_params = cur.execute.call_args_list[0].args
        self.assertIn("WHERE bp.id = %s", lookup_sql)
        self.assertIn("AND c.user_id = %s", lookup_sql)
        self.assertEqual(lookup_params, (77, 101))

        update_sql, update_params = cur.execute.call_args_list[1].args
        self.assertIn("UPDATE buyer_properties", update_sql)
        self.assertIn("WHERE id = %s", update_sql)
        self.assertIn("AND EXISTS", update_sql)
        self.assertIn("AND c.user_id = %s", update_sql)
        self.assertEqual(
            update_params,
            (
                "2 Main Street",
                "Keyport",
                "NJ",
                "07735",
                "accepted",
                77,
                101,
            ),
        )

        conn.commit.assert_called_once()
        conn.close.assert_called_once()




class SpecialDateTenantIsolationTests(unittest.TestCase):
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
                user if str(requested_user_id) == str(user_id) else None
            )
        )
        with self.client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True

    @patch("app.get_db")
    def test_user_cannot_add_special_date_to_another_users_contact(self, mock_get_db):
        self.login_as(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None
        mock_get_db.return_value = conn

        response = self.client.post(
            "/contact/202/special-dates/add",
            data={
                "label": "Birthday",
                "special_date": "1990-01-02",
                "is_recurring": "on",
                "notes": "Must remain tenant isolated",
            },
        )

        self.assertEqual(response.status_code, 404)

        first_sql, first_params = cur.execute.call_args_list[0].args
        self.assertIn(
            "SELECT id FROM contacts WHERE id = %s AND user_id = %s",
            " ".join(first_sql.split()),
        )
        self.assertEqual(first_params, (202, 101))

        executed_sql = [
            " ".join(call.args[0].split())
            for call in cur.execute.call_args_list
        ]
        self.assertFalse(
            any("INSERT INTO contact_special_dates" in sql for sql in executed_sql)
        )
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_user_can_add_special_date_to_owned_contact(self, mock_get_db):
        self.login_as(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = {"id": 202}
        mock_get_db.return_value = conn

        response = self.client.post(
            "/contact/202/special-dates/add",
            data={
                "label": "Birthday",
                "special_date": "1990-01-02",
                "is_recurring": "on",
                "notes": "Owned contact",
            },
        )

        self.assertEqual(response.status_code, 302)

        first_sql, first_params = cur.execute.call_args_list[0].args
        self.assertIn(
            "SELECT id FROM contacts WHERE id = %s AND user_id = %s",
            " ".join(first_sql.split()),
        )
        self.assertEqual(first_params, (202, 101))

        insert_sql, insert_params = cur.execute.call_args_list[1].args
        self.assertIn(
            "INSERT INTO contact_special_dates",
            " ".join(insert_sql.split()),
        )
        self.assertEqual(
            insert_params,
            (202, "Birthday", "1990-01-02", True, "Owned contact"),
        )
        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_user_cannot_delete_another_users_special_date(self, mock_get_db):
        self.login_as(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None
        mock_get_db.return_value = conn

        response = self.client.post("/special-dates/303/delete")

        self.assertEqual(response.status_code, 404)

        lookup_sql, lookup_params = cur.execute.call_args_list[0].args
        normalized = " ".join(lookup_sql.split())
        self.assertIn("FROM contact_special_dates csd", normalized)
        self.assertIn("JOIN contacts c ON c.id = csd.contact_id", normalized)
        self.assertIn("WHERE csd.id = %s", normalized)
        self.assertIn("AND c.user_id = %s", normalized)
        self.assertEqual(lookup_params, (303, 101))

        executed_sql = [
            " ".join(call.args[0].split())
            for call in cur.execute.call_args_list
        ]
        self.assertFalse(
            any("DELETE FROM contact_special_dates" in sql for sql in executed_sql)
        )
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owned_special_date_delete_is_tenant_scoped(self, mock_get_db):
        self.login_as(101)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = {"contact_id": 202}
        mock_get_db.return_value = conn

        response = self.client.post("/special-dates/303/delete")

        self.assertEqual(response.status_code, 302)

        lookup_sql, lookup_params = cur.execute.call_args_list[0].args
        lookup_normalized = " ".join(lookup_sql.split())
        self.assertIn("JOIN contacts c ON c.id = csd.contact_id", lookup_normalized)
        self.assertIn("AND c.user_id = %s", lookup_normalized)
        self.assertEqual(lookup_params, (303, 101))

        delete_sql, delete_params = cur.execute.call_args_list[1].args
        delete_normalized = " ".join(delete_sql.split())
        self.assertIn("DELETE FROM contact_special_dates csd", delete_normalized)
        self.assertIn("USING contacts c", delete_normalized)
        self.assertIn("c.id = csd.contact_id", delete_normalized)
        self.assertIn("c.user_id = %s", delete_normalized)
        self.assertEqual(delete_params, (303, 101))

        conn.commit.assert_called_once()
        conn.close.assert_called_once()

class ChecklistTenantIsolationTests(unittest.TestCase):
    @patch("app.get_db")
    def test_buyer_checklist_read_is_tenant_scoped(self, mock_get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchall.return_value = []
        mock_get_db.return_value = conn

        rows, complete, total = app_module.get_buyer_checklist(101, 202)

        self.assertEqual(rows, [])
        self.assertEqual(complete, 0)
        self.assertEqual(total, 0)

        sql, params = cur.execute.call_args.args
        normalized = " ".join(sql.split())
        self.assertIn("FROM buyer_checklist_items AS bci", normalized)
        self.assertIn(
            "JOIN contacts AS c ON c.id = bci.contact_id",
            normalized,
        )
        self.assertIn("WHERE bci.contact_id = %s", normalized)
        self.assertIn("AND c.user_id = %s", normalized)
        self.assertEqual(params, (202, 101))
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_listing_checklist_read_is_tenant_scoped(self, mock_get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchall.return_value = []
        mock_get_db.return_value = conn

        rows, complete, total = app_module.get_listing_checklist(101, 202)

        self.assertEqual(rows, [])
        self.assertEqual(complete, 0)
        self.assertEqual(total, 0)

        sql, params = cur.execute.call_args.args
        normalized = " ".join(sql.split())
        self.assertIn(
            "FROM listing_checklist_items AS lci",
            normalized,
        )
        self.assertIn(
            "JOIN contacts AS c ON c.id = lci.contact_id",
            normalized,
        )
        self.assertIn("WHERE lci.contact_id = %s", normalized)
        self.assertIn("AND c.user_id = %s", normalized)
        self.assertEqual(params, (202, 101))
        conn.close.assert_called_once()



class EngagementInsertTenantIsolationTests(unittest.TestCase):
    def _connection(self, fetches):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.side_effect = fetches
        return conn, cur

    def test_insert_engagement_rejects_foreign_contact(self):
        from engagements import insert_engagement

        conn, cur = self._connection([None])

        with self.assertRaises(ValueError):
            insert_engagement(
                conn=conn,
                user_id=101,
                contact_id=202,
                engagement_type="call",
                occurred_at=datetime(2026, 9, 21, 10, 0),
            )

        sql = " ".join(cur.execute.call_args_list[0].args[0].split())
        self.assertIn("FROM contacts", sql)
        self.assertIn("id = %s", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(cur.execute.call_args_list[0].args[1], (202, 101))
        self.assertEqual(cur.execute.call_count, 1)
        conn.commit.assert_not_called()
        cur.close.assert_called_once()

    def test_insert_engagement_rejects_foreign_or_mismatched_parent(self):
        from engagements import insert_engagement

        conn, cur = self._connection([{"id": 202}, None])

        with self.assertRaises(ValueError):
            insert_engagement(
                conn=conn,
                user_id=101,
                contact_id=202,
                parent_engagement_id=303,
                engagement_type="call",
                occurred_at=datetime(2026, 9, 21, 10, 0),
            )

        parent_sql = " ".join(cur.execute.call_args_list[1].args[0].split())
        self.assertIn("FROM engagements", parent_sql)
        self.assertIn("user_id = %s", parent_sql)
        self.assertIn("contact_id = %s", parent_sql)
        self.assertEqual(
            cur.execute.call_args_list[1].args[1],
            (303, 101, 202),
        )
        self.assertEqual(cur.execute.call_count, 2)
        conn.commit.assert_not_called()
        cur.close.assert_called_once()

    def test_insert_engagement_allows_owned_contact_and_parent(self):
        from engagements import insert_engagement

        conn, cur = self._connection([
            {"id": 202},
            {"id": 303},
            {"id": 404},
        ])

        engagement_id = insert_engagement(
            conn=conn,
            user_id=101,
            contact_id=202,
            parent_engagement_id=303,
            engagement_type="call",
            occurred_at=datetime(2026, 9, 21, 10, 0),
        )

        self.assertEqual(engagement_id, 404)
        self.assertEqual(cur.execute.call_count, 3)
        insert_sql = " ".join(cur.execute.call_args_list[2].args[0].split())
        self.assertIn("INSERT INTO engagements", insert_sql)
        conn.commit.assert_called_once()
        cur.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
