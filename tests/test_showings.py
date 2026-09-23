import unittest
from unittest.mock import MagicMock, patch

import app as app_module


class ShowingRouteTests(unittest.TestCase):

    def setUp(self):
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "showing-test-secret"
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

    @staticmethod
    def base_data(**overrides):
        data = {
            "showing_type": "buyer",
            "scheduled_at": "2026-09-23T14:30",
            "status": "scheduled",
            "address_line": "75 Franklin Ave",
            "city": "Hazlet",
            "state": "NJ",
            "postal_code": "07730",
        }
        data.update(overrides)
        return data

    @patch("app.get_db")
    def test_buyer_showing_requires_contact(self, get_db):
        self.login_as(101)

        response = self.client.post(
            "/showings",
            data=self.base_data(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Buyer showing requires at least one contact",
            response.get_data(as_text=True),
        )
        get_db.assert_not_called()

    @patch("app.get_db")
    def test_listing_showing_can_have_no_crm_contact(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        cur.fetchone.return_value = {"id": 501}

        self.login_as(101)

        response = self.client.post(
            "/showings",
            data=self.base_data(
                showing_type="listing",
                showing_agent_name="Outside Agent",
            ),
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(cur.execute.call_count, 1)
        insert_sql, insert_params = cur.execute.call_args.args

        self.assertIn("INSERT INTO showings", insert_sql)
        self.assertEqual(insert_params[0], 101)
        self.assertEqual(insert_params[1], "listing")
        self.assertEqual(insert_params[10], "Outside Agent")

        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_buyer_showing_creates_explicit_memberships_for_owned_contacts(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        cur.fetchall.return_value = [
            {"id": 55},
            {"id": 56},
        ]
        cur.fetchone.return_value = {"id": 501}

        self.login_as(101)

        response = self.client.post(
            "/showings",
            data={
                **self.base_data(),
                "contact_ids": ["55", "56"],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(cur.execute.call_count, 4)

        contact_sql, contact_params = cur.execute.call_args_list[0].args
        showing_sql, showing_params = cur.execute.call_args_list[1].args
        membership_1_sql, membership_1_params = (
            cur.execute.call_args_list[2].args
        )
        membership_2_sql, membership_2_params = (
            cur.execute.call_args_list[3].args
        )

        self.assertIn("FROM contacts", contact_sql)
        self.assertIn("user_id = %s", contact_sql)
        self.assertEqual(contact_params, (101, [55, 56]))

        self.assertIn("INSERT INTO showings", showing_sql)
        self.assertEqual(showing_params[0], 101)
        self.assertEqual(showing_params[1], "buyer")

        self.assertIn("INSERT INTO showing_contacts", membership_1_sql)
        self.assertEqual(membership_1_params, (101, 501, 55))

        self.assertIn("INSERT INTO showing_contacts", membership_2_sql)
        self.assertEqual(membership_2_params, (101, 501, 56))

        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_duplicate_contact_ids_create_one_membership_each(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        cur.fetchall.return_value = [
            {"id": 55},
            {"id": 56},
        ]
        cur.fetchone.return_value = {"id": 501}

        self.login_as(101)

        response = self.client.post(
            "/showings",
            data={
                **self.base_data(),
                "contact_ids": ["55", "55", "56", "56"],
            },
        )

        self.assertEqual(response.status_code, 302)

        membership_calls = [
            call
            for call in cur.execute.call_args_list
            if "INSERT INTO showing_contacts" in call.args[0]
        ]

        self.assertEqual(len(membership_calls), 2)
        self.assertEqual(
            {call.args[1][2] for call in membership_calls},
            {55, 56},
        )

    @patch("app.get_db")
    def test_owner_cannot_use_foreign_contact_in_showing(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # Only contact 55 belongs to user 101. Contact 909 is foreign.
        cur.fetchall.return_value = [{"id": 55}]

        self.login_as(101)

        response = self.client.post(
            "/showings",
            data={
                **self.base_data(),
                "contact_ids": ["55", "909"],
            },
        )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(cur.execute.call_count, 1)
        sql, params = cur.execute.call_args.args

        self.assertIn("FROM contacts", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(params, (101, [55, 909]))

        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owner_cannot_use_foreign_transaction_in_showing(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        cur.fetchone.return_value = None

        self.login_as(101)

        response = self.client.post(
            "/showings",
            data={
                **self.base_data(),
                "transaction_id": "909",
                "contact_ids": ["55"],
            },
        )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(cur.execute.call_count, 1)
        sql, params = cur.execute.call_args.args

        self.assertIn("FROM transactions", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(params, (909, 101))

        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owner_cannot_use_foreign_professional_in_showing(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        cur.fetchone.return_value = None

        self.login_as(101)

        response = self.client.post(
            "/showings",
            data={
                **self.base_data(showing_type="listing"),
                "showing_agent_professional_id": "909",
            },
        )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(cur.execute.call_count, 1)
        sql, params = cur.execute.call_args.args

        self.assertIn("FROM professionals", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(params, (909, 101))

        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owned_professional_is_stored_on_showing(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        cur.fetchone.side_effect = [
            {"id": 77},
            {"id": 501},
        ]

        self.login_as(101)

        response = self.client.post(
            "/showings",
            data=self.base_data(
                showing_type="listing",
                showing_agent_professional_id="77",
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(cur.execute.call_count, 2)

        professional_sql, professional_params = (
            cur.execute.call_args_list[0].args
        )
        showing_sql, showing_params = cur.execute.call_args_list[1].args

        self.assertIn("FROM professionals", professional_sql)
        self.assertIn("user_id = %s", professional_sql)
        self.assertEqual(professional_params, (77, 101))

        self.assertIn("INSERT INTO showings", showing_sql)
        self.assertEqual(showing_params[0], 101)
        self.assertEqual(showing_params[3], 77)

        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_professional_details_populate_blank_showing_snapshot_fields(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        cur.fetchone.side_effect = [
            {
                "id": 77,
                "name": "Donna Bruno",
                "company": "Example Realty",
                "email": "donna@example.com",
                "phone": "732-555-0101",
            },
            {"id": 501},
        ]

        self.login_as(101)

        response = self.client.post(
            "/showings",
            data=self.base_data(
                showing_type="listing",
                showing_agent_professional_id="77",
            ),
        )

        self.assertEqual(response.status_code, 302)

        showing_sql, showing_params = cur.execute.call_args_list[1].args

        self.assertIn("INSERT INTO showings", showing_sql)
        self.assertEqual(showing_params[3], 77)
        self.assertEqual(showing_params[10], "Donna Bruno")
        self.assertEqual(showing_params[11], "Example Realty")
        self.assertEqual(showing_params[12], "donna@example.com")
        self.assertEqual(showing_params[13], "732-555-0101")

        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_manual_showing_agent_values_override_professional_snapshot(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        cur.fetchone.side_effect = [
            {
                "id": 77,
                "name": "Donna Bruno",
                "company": "Example Realty",
                "email": "donna@example.com",
                "phone": "732-555-0101",
            },
            {"id": 501},
        ]

        self.login_as(101)

        response = self.client.post(
            "/showings",
            data=self.base_data(
                showing_type="listing",
                showing_agent_professional_id="77",
                showing_agent_name="Donna B.",
                showing_agent_brokerage="Showing Day Realty",
                showing_agent_email="showing@example.com",
                showing_agent_phone="732-555-9999",
            ),
        )

        self.assertEqual(response.status_code, 302)

        showing_sql, showing_params = cur.execute.call_args_list[1].args

        self.assertIn("INSERT INTO showings", showing_sql)
        self.assertEqual(showing_params[3], 77)
        self.assertEqual(showing_params[10], "Donna B.")
        self.assertEqual(showing_params[11], "Showing Day Realty")
        self.assertEqual(showing_params[12], "showing@example.com")
        self.assertEqual(showing_params[13], "732-555-9999")

        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    def test_invalid_showing_type_is_rejected_before_database_access(self):
        self.login_as(101)

        with patch("app.get_db") as get_db:
            response = self.client.post(
                "/showings",
                data=self.base_data(
                    showing_type="mystery",
                    contact_ids=["55"],
                ),
            )

        self.assertEqual(response.status_code, 400)
        get_db.assert_not_called()

    def test_invalid_status_is_rejected_before_database_access(self):
        self.login_as(101)

        with patch("app.get_db") as get_db:
            response = self.client.post(
                "/showings",
                data=self.base_data(
                    status="mystery",
                    contact_ids=["55"],
                ),
            )

        self.assertEqual(response.status_code, 400)
        get_db.assert_not_called()

    def test_invalid_interest_level_is_rejected_before_database_access(self):
        self.login_as(101)

        with patch("app.get_db") as get_db:
            response = self.client.post(
                "/showings",
                data=self.base_data(
                    interest_level="mystery",
                    contact_ids=["55"],
                ),
            )

        self.assertEqual(response.status_code, 400)
        get_db.assert_not_called()

    def test_missing_datetime_is_rejected_before_database_access(self):
        self.login_as(101)

        with patch("app.get_db") as get_db:
            response = self.client.post(
                "/showings",
                data=self.base_data(
                    scheduled_at="",
                    contact_ids=["55"],
                ),
            )

        self.assertEqual(response.status_code, 400)
        get_db.assert_not_called()

    def test_invalid_transaction_id_is_rejected_before_database_access(self):
        self.login_as(101)

        with patch("app.get_db") as get_db:
            response = self.client.post(
                "/showings",
                data=self.base_data(
                    transaction_id="not-an-id",
                    contact_ids=["55"],
                ),
            )

        self.assertEqual(response.status_code, 400)
        get_db.assert_not_called()

    def test_invalid_professional_id_is_rejected_before_database_access(self):
        self.login_as(101)

        with patch("app.get_db") as get_db:
            response = self.client.post(
                "/showings",
                data=self.base_data(
                    showing_type="listing",
                    showing_agent_professional_id="not-an-id",
                ),
            )

        self.assertEqual(response.status_code, 400)
        get_db.assert_not_called()

    def test_invalid_contact_id_is_rejected_before_database_access(self):
        self.login_as(101)

        with patch("app.get_db") as get_db:
            response = self.client.post(
                "/showings",
                data={
                    **self.base_data(),
                    "contact_ids": ["55", "not-an-id"],
                },
            )

        self.assertEqual(response.status_code, 400)
        get_db.assert_not_called()


    @patch("app.get_db")
    def test_buyer_profile_context_returns_to_owned_buyer_showings(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # 1. buyer_contact_id ownership check
        # 2. Showing insert RETURNING id
        cur.fetchone.side_effect = [
            {"id": 55},
            {"id": 501},
        ]
        cur.fetchall.return_value = [{"id": 55}]

        self.login_as(101)

        response = self.client.post(
            "/showings",
            data={
                **self.base_data(),
                "buyer_contact_id": "55",
                "contact_ids": ["55"],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.headers["Location"].endswith(
                "/buyer/55#bp-showings"
            ),
            response.headers["Location"],
        )

        buyer_sql, buyer_params = cur.execute.call_args_list[0].args
        self.assertIn("FROM contacts", buyer_sql)
        self.assertIn("user_id = %s", buyer_sql)
        self.assertEqual(buyer_params, (55, 101))

        contact_sql, contact_params = cur.execute.call_args_list[1].args
        self.assertIn("FROM contacts", contact_sql)
        self.assertEqual(contact_params, (101, [55]))

        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owner_cannot_use_foreign_buyer_contact_for_return(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # buyer_contact_id 909 does not belong to user 101.
        cur.fetchone.return_value = None

        self.login_as(101)

        response = self.client.post(
            "/showings",
            data={
                **self.base_data(),
                "buyer_contact_id": "909",
                "contact_ids": ["55"],
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn(
            "Buyer contact not found",
            response.get_data(as_text=True),
        )

        self.assertEqual(cur.execute.call_count, 1)
        sql, params = cur.execute.call_args.args
        self.assertIn("FROM contacts", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(params, (909, 101))

        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_buyer_return_contact_must_be_showing_attendee(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # Contact 55 is an owned Buyer Profile, but only 56 was submitted
        # as a Showing attendee.
        cur.fetchone.return_value = {"id": 55}

        self.login_as(101)

        response = self.client.post(
            "/showings",
            data={
                **self.base_data(),
                "buyer_contact_id": "55",
                "contact_ids": ["56"],
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Buyer contact must attend buyer showing",
            response.get_data(as_text=True),
        )

        # Failure occurs immediately after validating buyer_contact_id,
        # before attendee ownership lookup or any insert.
        self.assertEqual(cur.execute.call_count, 1)
        sql, params = cur.execute.call_args.args
        self.assertIn("FROM contacts", sql)
        self.assertEqual(params, (55, 101))

        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()



    @patch("app.get_db")
    def test_owner_can_delete_showing(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # 1. Showing ownership
        # 2. DELETE ... RETURNING id
        cur.fetchone.side_effect = [
            {"id": 44},
            {"id": 44},
        ]

        self.login_as(101)

        response = self.client.post("/showings/44/delete")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/transactions"))

        self.assertEqual(cur.execute.call_count, 2)

        ownership_sql, ownership_params = cur.execute.call_args_list[0].args
        self.assertIn("FROM showings", ownership_sql)
        self.assertIn("user_id = %s", ownership_sql)
        self.assertEqual(ownership_params, (44, 101))

        delete_sql, delete_params = cur.execute.call_args_list[1].args
        self.assertIn("DELETE FROM showings", delete_sql)
        self.assertIn("user_id = %s", delete_sql)
        self.assertEqual(delete_params, (44, 101))

        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owner_cannot_delete_foreign_showing(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # Showing 44 is not owned by user 101.
        cur.fetchone.return_value = None

        self.login_as(101)

        response = self.client.post("/showings/44/delete")

        self.assertEqual(response.status_code, 404)
        self.assertIn(
            "Showing not found",
            response.get_data(as_text=True),
        )

        self.assertEqual(cur.execute.call_count, 1)

        sql, params = cur.execute.call_args.args
        self.assertIn("FROM showings", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(params, (44, 101))

        executed_sql = "\n".join(
            call.args[0]
            for call in cur.execute.call_args_list
        )
        self.assertNotIn("DELETE FROM showings", executed_sql)

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owner_can_delete_showing_with_valid_buyer_return_context(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # 1. Showing ownership
        # 2. Buyer belongs to tenant and participates in Showing
        # 3. DELETE ... RETURNING id
        cur.fetchone.side_effect = [
            {"id": 44},
            {"id": 55},
            {"id": 44},
        ]

        self.login_as(101)

        response = self.client.post(
            "/showings/44/delete",
            data={"buyer_contact_id": "55"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.location.endswith("/buyer/55#bp-showings")
        )

        self.assertEqual(cur.execute.call_count, 3)

        context_sql, context_params = cur.execute.call_args_list[1].args
        self.assertIn("FROM contacts AS c", context_sql)
        self.assertIn("JOIN showing_contacts AS sc", context_sql)
        self.assertIn("c.user_id = %s", context_sql)
        self.assertEqual(
            context_params,
            (101, 44, 55, 101),
        )

        delete_sql, delete_params = cur.execute.call_args_list[2].args
        self.assertIn("DELETE FROM showings", delete_sql)
        self.assertEqual(delete_params, (44, 101))

        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_delete_rejects_invalid_buyer_return_context_before_delete(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # Showing belongs to user 101, but Buyer return context is either
        # foreign, nonexistent, or not a member of this Showing.
        cur.fetchone.side_effect = [
            {"id": 44},
            None,
        ]

        self.login_as(101)

        response = self.client.post(
            "/showings/44/delete",
            data={"buyer_contact_id": "909"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn(
            "Buyer Showing context not found",
            response.get_data(as_text=True),
        )

        self.assertEqual(cur.execute.call_count, 2)

        context_sql, context_params = cur.execute.call_args_list[1].args
        self.assertIn("FROM contacts AS c", context_sql)
        self.assertIn("JOIN showing_contacts AS sc", context_sql)
        self.assertIn("c.user_id = %s", context_sql)
        self.assertEqual(
            context_params,
            (101, 44, 909, 101),
        )

        executed_sql = "\n".join(
            call.args[0]
            for call in cur.execute.call_args_list
        )
        self.assertNotIn("DELETE FROM showings", executed_sql)

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    def test_delete_showing_route_is_post_only(self):
        self.login_as(101)

        response = self.client.get("/showings/44/delete")

        self.assertEqual(response.status_code, 405)


    @patch("app.get_db")
    def test_owner_can_update_showing_and_replace_memberships(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # 1. Showing ownership
        # 2. Buyer return-contact ownership
        # 3. UPDATE ... RETURNING id
        cur.fetchone.side_effect = [
            {"id": 44, "showing_type": "buyer"},
            {"id": 55},
            {"id": 44},
        ]

        # Attendee ownership query
        cur.fetchall.return_value = [
            {"id": 55},
            {"id": 56},
        ]

        self.login_as(101)
        response = self.client.post(
            "/showings/44/update",
            data={
                **self.base_data(
                    status="completed",
                    interest_level="interested",
                    feedback="Liked the layout",
                    notes="Follow up tomorrow",
                ),
                "buyer_contact_id": "55",
                "contact_ids": ["55", "56"],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.location.endswith("/buyer/55#bp-showings")
        )

        calls = cur.execute.call_args_list

        # Showing ownership gate
        self.assertIn("FROM showings", calls[0].args[0])
        self.assertEqual(calls[0].args[1], (44, 101))

        # Buyer return-contact ownership gate
        self.assertIn("FROM contacts", calls[1].args[0])
        self.assertEqual(calls[1].args[1], (55, 101))

        # Attendee ownership validation occurs before UPDATE.
        self.assertIn("id = ANY(%s)", calls[2].args[0])
        self.assertEqual(calls[2].args[1], (101, [55, 56]))

        # Showing update remains tenant-scoped.
        self.assertIn("UPDATE showings", calls[3].args[0])
        self.assertIn("user_id = %s", calls[3].args[0])
        self.assertEqual(calls[3].args[1][-2:], (44, 101))

        # Existing memberships are removed only for this tenant/showing.
        self.assertIn("DELETE FROM showing_contacts", calls[4].args[0])
        self.assertEqual(calls[4].args[1], (44, 101))

        # Explicit replacement memberships.
        self.assertIn("INSERT INTO showing_contacts", calls[5].args[0])
        self.assertEqual(calls[5].args[1], (101, 44, 55))
        self.assertIn("INSERT INTO showing_contacts", calls[6].args[0])
        self.assertEqual(calls[6].args[1], (101, 44, 56))

        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owner_cannot_update_foreign_showing(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        cur.fetchone.return_value = None

        self.login_as(101)
        response = self.client.post(
            "/showings/909/update",
            data={
                **self.base_data(),
                "buyer_contact_id": "55",
                "contact_ids": ["55"],
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn(
            "Showing not found",
            response.get_data(as_text=True),
        )

        self.assertEqual(cur.execute.call_count, 1)
        sql, params = cur.execute.call_args.args
        self.assertIn("FROM showings", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(params, (909, 101))

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owner_cannot_add_foreign_contact_when_updating_showing(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # Showing 44 and Buyer 55 belong to user 101.
        cur.fetchone.side_effect = [
            {"id": 44, "showing_type": "buyer"},
            {"id": 55},
        ]

        # Only 55 belongs to this user. Submitted 909 is foreign/missing.
        cur.fetchall.return_value = [
            {"id": 55},
        ]

        self.login_as(101)
        response = self.client.post(
            "/showings/44/update",
            data={
                **self.base_data(),
                "buyer_contact_id": "55",
                "contact_ids": ["55", "909"],
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn(
            "Contact not found",
            response.get_data(as_text=True),
        )

        # Ownership gate, Buyer context check, attendee ownership query.
        self.assertEqual(cur.execute.call_count, 3)
        self.assertIn(
            "id = ANY(%s)",
            cur.execute.call_args_list[2].args[0],
        )
        self.assertEqual(
            cur.execute.call_args_list[2].args[1],
            (101, [55, 909]),
        )

        # No UPDATE or membership replacement may occur.
        executed_sql = "\n".join(
            call.args[0]
            for call in cur.execute.call_args_list
        )
        self.assertNotIn("UPDATE showings", executed_sql)
        self.assertNotIn("DELETE FROM showing_contacts", executed_sql)
        self.assertNotIn("INSERT INTO showing_contacts", executed_sql)

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()



    @patch("app.get_db")
    def test_owner_cannot_use_foreign_transaction_when_updating_showing(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # Showing and Buyer belong to user 101; transaction does not.
        cur.fetchone.side_effect = [
            {"id": 44, "showing_type": "buyer"},
            {"id": 55},
            None,
        ]

        self.login_as(101)
        response = self.client.post(
            "/showings/44/update",
            data={
                **self.base_data(transaction_id="909"),
                "buyer_contact_id": "55",
                "contact_ids": ["55"],
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn(
            "Transaction not found",
            response.get_data(as_text=True),
        )

        self.assertEqual(cur.execute.call_count, 3)
        sql, params = cur.execute.call_args_list[2].args
        self.assertIn("FROM transactions", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(params, (909, 101))

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owner_cannot_use_foreign_professional_when_updating_showing(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # Showing and Buyer belong to user 101; Professional does not.
        cur.fetchone.side_effect = [
            {"id": 44, "showing_type": "buyer"},
            {"id": 55},
            None,
        ]

        self.login_as(101)
        response = self.client.post(
            "/showings/44/update",
            data={
                **self.base_data(
                    showing_agent_professional_id="909"
                ),
                "buyer_contact_id": "55",
                "contact_ids": ["55"],
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn(
            "Showing agent not found",
            response.get_data(as_text=True),
        )

        self.assertEqual(cur.execute.call_count, 3)
        sql, params = cur.execute.call_args_list[2].args
        self.assertIn("FROM professionals", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(params, (909, 101))

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_owner_cannot_use_foreign_buyer_return_when_updating_showing(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # Showing belongs to user 101, Buyer return contact does not.
        cur.fetchone.side_effect = [
            {"id": 44, "showing_type": "buyer"},
            None,
        ]

        self.login_as(101)
        response = self.client.post(
            "/showings/44/update",
            data={
                **self.base_data(),
                "buyer_contact_id": "909",
                "contact_ids": ["909"],
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn(
            "Buyer contact not found",
            response.get_data(as_text=True),
        )

        self.assertEqual(cur.execute.call_count, 2)
        sql, params = cur.execute.call_args_list[1].args
        self.assertIn("FROM contacts", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(params, (909, 101))

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_buyer_return_contact_must_remain_attendee_on_update(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        cur.fetchone.side_effect = [
            {"id": 44, "showing_type": "buyer"},
            {"id": 55},
        ]

        self.login_as(101)
        response = self.client.post(
            "/showings/44/update",
            data={
                **self.base_data(),
                "buyer_contact_id": "55",
                "contact_ids": ["56"],
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Buyer contact must attend buyer showing",
            response.get_data(as_text=True),
        )

        # Stop immediately after Showing and Buyer ownership checks.
        self.assertEqual(cur.execute.call_count, 2)

        executed_sql = "\n".join(
            call.args[0]
            for call in cur.execute.call_args_list
        )
        self.assertNotIn("UPDATE showings", executed_sql)
        self.assertNotIn("DELETE FROM showing_contacts", executed_sql)

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_update_cannot_change_showing_type(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        get_db.return_value = conn

        # Existing Showing is a Buyer Showing owned by user 101.
        cur.fetchone.return_value = {
            "id": 44,
            "showing_type": "buyer",
        }

        self.login_as(101)
        response = self.client.post(
            "/showings/44/update",
            data={
                **self.base_data(showing_type="listing"),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Showing type cannot be changed",
            response.get_data(as_text=True),
        )

        # Stop immediately after the tenant-scoped ownership/type check.
        self.assertEqual(cur.execute.call_count, 1)
        sql, params = cur.execute.call_args.args
        self.assertIn("SELECT id, showing_type", sql)
        self.assertIn("FROM showings", sql)
        self.assertIn("user_id = %s", sql)
        self.assertEqual(params, (44, 101))

        executed_sql = "\n".join(
            call.args[0]
            for call in cur.execute.call_args_list
        )
        self.assertNotIn("UPDATE showings", executed_sql)
        self.assertNotIn("DELETE FROM showing_contacts", executed_sql)
        self.assertNotIn("INSERT INTO showing_contacts", executed_sql)

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    def test_update_showing_route_is_post_only(self):
        self.login_as(101)

        response = self.client.get("/showings/44/update")

        self.assertEqual(response.status_code, 405)



if __name__ == "__main__":
    unittest.main()
