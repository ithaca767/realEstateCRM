import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import app as app_module


class CurrentClientsTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "current-clients-test-secret"
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

    @patch("app.render_template", return_value="contacts")
    @patch("app.get_db")
    def test_current_clients_queries_are_tenant_scoped(
        self,
        get_db,
        render_template,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        cur.fetchone.return_value = {"total": 0}
        cur.fetchall.return_value = []
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.get("/contacts?tab=clients&client_status=current")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(cur.execute.call_count, 2)

        count_sql, count_params = cur.execute.call_args_list[0].args
        data_sql, data_params = cur.execute.call_args_list[1].args

        count_normalized = " ".join(count_sql.split())
        data_normalized = " ".join(data_sql.split())

        for sql in (count_normalized, data_normalized):
            self.assertIn("FROM contacts", sql)
            self.assertIn("user_id = %s", sql)
            self.assertIn("EXISTS (", sql)
            self.assertIn("FROM client_relationships cr", sql)
            self.assertIn(
                "JOIN client_relationship_contacts crc", sql
            )
            self.assertIn("cr.user_id = %s", sql)
            self.assertIn("crc.user_id = cr.user_id", sql)
            self.assertIn("crc.relationship_id = cr.id", sql)
            self.assertIn("crc.contact_id = contacts.id", sql)
            self.assertIn("cr.status = 'current'", sql)

        self.assertEqual(count_params, (101, 101))
        self.assertEqual(data_params, (101, 101, 101, 10, 0))

        render_template.assert_called_once()
        render_kwargs = render_template.call_args.kwargs
        self.assertEqual(render_kwargs["active_tab"], "clients")
        self.assertEqual(render_kwargs["client_status"], "current")

        conn.close.assert_called_once()

    @patch("app.render_template", return_value="contacts")
    @patch("app.get_db")
    def test_current_clients_uses_exists_not_relationship_join(
        self,
        get_db,
        render_template,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        cur.fetchone.return_value = {"total": 1}
        cur.fetchall.return_value = [
            {
                "id": 55,
                "name": "Current Client",
                "first_name": "Current",
                "last_name": "Client",
                "email": None,
                "phone": None,
                "lead_type": "Buyer",
                "pipeline_stage": None,
                "notes": None,
                "archived_at": None,
                "contact_state": "active",
            }
        ]
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.get("/contacts?tab=clients&client_status=current")

        self.assertEqual(response.status_code, 200)

        data_sql, data_params = cur.execute.call_args_list[1].args
        normalized = " ".join(data_sql.split())

        self.assertIn("EXISTS (", normalized)
        self.assertNotIn(
            "FROM contacts JOIN client_relationships",
            normalized,
        )
        self.assertIn(
            "JOIN client_relationship_contacts crc",
            normalized,
        )
        self.assertIn("crc.user_id = cr.user_id", normalized)
        self.assertIn("crc.relationship_id = cr.id", normalized)
        self.assertIn("crc.contact_id = contacts.id", normalized)
        self.assertIn("cr.status = 'current'", normalized)
        self.assertEqual(data_params, (101, 101, 101, 10, 0))

        template_kwargs = render_template.call_args.kwargs
        self.assertEqual(len(template_kwargs["contacts"]), 1)
        self.assertEqual(template_kwargs["contacts"][0]["id"], 55)

        conn.close.assert_called_once()


    @patch("app.get_db")
    def test_add_client_relationship_rejects_foreign_contact(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        # Ownership lookup cannot see a contact owned by another tenant.
        cur.fetchone.return_value = None
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.post(
            "/contacts/202/client-relationships/add",
            data={
                "relationship_type": "Buyer",
                "agreement_type": "Buyer Agency Agreement",
                "signed_date": "2026-09-21",
                "notes": "must never be written",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(cur.execute.call_count, 1)

        ownership_sql, ownership_params = cur.execute.call_args.args
        normalized = " ".join(ownership_sql.split())

        self.assertIn("FROM contacts", normalized)
        self.assertIn("id = %s", normalized)
        self.assertIn("user_id = %s", normalized)
        self.assertEqual(ownership_params, (202, 101))

        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_add_client_relationship_creates_origin_membership(self, get_db):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        # First fetchone: originating Contact ownership.
        # Second fetchone: INSERT ... RETURNING relationship id.
        cur.fetchone.side_effect = [
            {"id": 55},
            {"id": 700},
        ]
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.post(
            "/contacts/55/client-relationships/add",
            data={
                "relationship_type": "Buyer",
                "agreement_type": "Buyer Agency Agreement",
                "signed_date": "2026-09-21",
                "notes": "Signed representation agreement",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(cur.execute.call_count, 3)

        ownership_sql, ownership_params = cur.execute.call_args_list[0].args
        relationship_sql, relationship_params = cur.execute.call_args_list[1].args
        membership_sql, membership_params = cur.execute.call_args_list[2].args

        ownership_normalized = " ".join(ownership_sql.split())
        relationship_normalized = " ".join(relationship_sql.split())
        membership_normalized = " ".join(membership_sql.split())

        self.assertIn("FROM contacts", ownership_normalized)
        self.assertIn("user_id = %s", ownership_normalized)
        self.assertEqual(ownership_params, (55, 101))

        self.assertIn(
            "INSERT INTO client_relationships",
            relationship_normalized,
        )
        self.assertIn("RETURNING id", relationship_normalized)
        self.assertEqual(relationship_params[0], 101)
        self.assertEqual(relationship_params[1], 55)
        self.assertEqual(relationship_params[2], "Buyer")
        self.assertEqual(
            relationship_params[3],
            "Buyer Agency Agreement",
        )
        self.assertEqual(str(relationship_params[4]), "2026-09-21")
        self.assertEqual(
            relationship_params[5],
            "Signed representation agreement",
        )

        self.assertIn(
            "INSERT INTO client_relationship_contacts",
            membership_normalized,
        )
        self.assertEqual(membership_params, (101, 700, 55))

        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_add_client_relationship_adds_selected_associated_contact(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        cur.fetchone.side_effect = [
            {"id": 55},
            {"id": 701},
        ]
        cur.fetchall.return_value = [
            {"other_contact_id": 56},
        ]
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.post(
            "/contacts/55/client-relationships/add",
            data={
                "relationship_type": "Buyer",
                "agreement_type": "Buyer Agency Agreement",
                "signed_date": "2026-09-21",
                "notes": "Joint buyers",
                "member_contact_ids": ["56"],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(cur.execute.call_count, 5)

        association_sql, association_params = (
            cur.execute.call_args_list[1].args
        )
        relationship_sql, relationship_params = (
            cur.execute.call_args_list[2].args
        )
        first_membership_sql, first_membership_params = (
            cur.execute.call_args_list[3].args
        )
        second_membership_sql, second_membership_params = (
            cur.execute.call_args_list[4].args
        )

        association_normalized = " ".join(association_sql.split())
        self.assertIn(
            "FROM contact_associations ca",
            association_normalized,
        )
        self.assertIn("ca.user_id = %s", association_normalized)
        self.assertIn(
            "c.user_id = ca.user_id",
            association_normalized,
        )
        self.assertEqual(
            association_params,
            (55, 55, 101, 55, 55),
        )

        self.assertIn(
            "INSERT INTO client_relationships",
            " ".join(relationship_sql.split()),
        )
        self.assertEqual(relationship_params[0], 101)
        self.assertEqual(relationship_params[1], 55)

        for sql in (first_membership_sql, second_membership_sql):
            self.assertIn(
                "INSERT INTO client_relationship_contacts",
                " ".join(sql.split()),
            )

        self.assertEqual(first_membership_params, (101, 701, 55))
        self.assertEqual(second_membership_params, (101, 701, 56))

        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_add_client_relationship_rejects_unassociated_member(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        cur.fetchone.return_value = {"id": 55}
        # Contact 999 was submitted but is not in the authenticated
        # user's direct associations for Contact 55.
        cur.fetchall.return_value = [
            {"other_contact_id": 56},
        ]
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.post(
            "/contacts/55/client-relationships/add",
            data={
                "relationship_type": "Buyer",
                "agreement_type": "Buyer Agency Agreement",
                "signed_date": "2026-09-21",
                "member_contact_ids": ["999"],
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(cur.execute.call_count, 2)

        association_sql, association_params = (
            cur.execute.call_args_list[1].args
        )
        association_normalized = " ".join(association_sql.split())

        self.assertIn(
            "FROM contact_associations ca",
            association_normalized,
        )
        self.assertIn("ca.user_id = %s", association_normalized)
        self.assertEqual(
            association_params,
            (55, 55, 101, 55, 55),
        )

        executed_sql = " ".join(
            " ".join(call.args[0].split())
            for call in cur.execute.call_args_list
        )
        self.assertNotIn(
            "INSERT INTO client_relationships",
            executed_sql,
        )
        self.assertNotIn(
            "INSERT INTO client_relationship_contacts",
            executed_sql,
        )

        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_add_client_relationship_rejects_invalid_type_before_database(
        self,
        get_db,
    ):
        self.login_as(101)

        response = self.client.post(
            "/contacts/55/client-relationships/add",
            data={
                "relationship_type": "Invalid Type",
                "agreement_type": "Agreement",
                "signed_date": "2026-09-21",
            },
        )

        self.assertEqual(response.status_code, 302)
        get_db.assert_not_called()



    def test_edit_contact_client_relationship_read_is_tenant_scoped(self):
        source = Path("app.py").read_text()

        start = source.index("def edit_contact(contact_id):")
        end = source.index(
            '@app.route("/contacts/<int:contact_id>/associations/add"',
            start,
        )
        edit_contact_source = source[start:end]

        self.assertIn(
            "FROM client_relationships cr",
            edit_contact_source,
        )
        self.assertIn(
            "JOIN client_relationship_contacts crc",
            edit_contact_source,
        )
        self.assertIn(
            "crc.user_id = cr.user_id",
            edit_contact_source,
        )
        self.assertIn(
            "crc.relationship_id = cr.id",
            edit_contact_source,
        )
        self.assertIn(
            "WHERE cr.user_id = %s",
            edit_contact_source,
        )
        self.assertIn(
            "AND crc.contact_id = %s",
            edit_contact_source,
        )
        self.assertIn(
            "(current_user.id, contact_id)",
            edit_contact_source,
        )
        self.assertIn(
            "client_relationships=client_relationships",
            edit_contact_source,
        )

        # Every displayed relationship also loads its complete member list.
        # Both the membership rows and joined Contacts remain tenant-scoped.
        self.assertIn(
            "FROM client_relationship_contacts crc",
            edit_contact_source,
        )
        self.assertIn(
            "JOIN contacts c",
            edit_contact_source,
        )
        self.assertIn(
            "c.user_id = crc.user_id",
            edit_contact_source,
        )
        self.assertIn(
            "c.id = crc.contact_id",
            edit_contact_source,
        )
        self.assertIn(
            "WHERE crc.user_id = %s",
            edit_contact_source,
        )
        self.assertIn(
            "crc.relationship_id = ANY(%s)",
            edit_contact_source,
        )
        self.assertIn(
            "(current_user.id, relationship_ids)",
            edit_contact_source,
        )
        self.assertIn(
            'relationship["members"] = members',
            edit_contact_source,
        )
        self.assertIn(
            'relationship["member_contact_ids"] = [',
            edit_contact_source,
        )



    @patch("app.get_db")
    def test_edit_client_relationship_updates_details_and_membership(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        # Origin ownership, then relationship membership lookup.
        cur.fetchone.side_effect = [
            {"id": 55},
            {
                "id": 700,
                "status": "current",
                "signed_date": "2026-09-21",
                "end_date": None,
            },
        ]

        # Existing members, then allowed associated Contacts.
        cur.fetchall.side_effect = [
            [
                {"contact_id": 55},
                {"contact_id": 56},
            ],
            [
                {"other_contact_id": 57},
            ],
        ]

        # Relationship UPDATE succeeds.
        cur.rowcount = 1
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.post(
            "/contacts/55/client-relationships/700/edit",
            data={
                "relationship_type": "Buyer",
                "agreement_type": "Updated Buyer Agency Agreement",
                "signed_date": "2026-09-20",
                "notes": "Updated shared relationship",
                "member_contact_ids": ["55", "57"],
            },
        )

        self.assertEqual(response.status_code, 302)

        normalized_calls = [
            (" ".join(call.args[0].split()), call.args[1])
            for call in cur.execute.call_args_list
        ]

        relationship_lookup_sql, relationship_lookup_params = (
            normalized_calls[1]
        )
        self.assertIn(
            "JOIN client_relationship_contacts crc",
            relationship_lookup_sql,
        )
        self.assertIn(
            "crc.user_id = cr.user_id",
            relationship_lookup_sql,
        )
        self.assertIn(
            "crc.relationship_id = cr.id",
            relationship_lookup_sql,
        )
        self.assertIn(
            "AND cr.user_id = %s",
            relationship_lookup_sql,
        )
        self.assertIn(
            "AND crc.contact_id = %s",
            relationship_lookup_sql,
        )
        self.assertEqual(
            relationship_lookup_params,
            (700, 101, 55),
        )

        association_sql, association_params = normalized_calls[3]
        self.assertIn(
            "FROM contact_associations ca",
            association_sql,
        )
        self.assertIn("ca.user_id = %s", association_sql)
        self.assertIn(
            "c.user_id = ca.user_id",
            association_sql,
        )
        self.assertEqual(
            association_params,
            (55, 55, 101, 55, 55),
        )

        update_sql, update_params = normalized_calls[4]
        self.assertIn(
            "UPDATE client_relationships",
            update_sql,
        )
        self.assertIn("AND user_id = %s", update_sql)
        self.assertNotIn("SET status =", update_sql)
        self.assertEqual(update_params[0], "Buyer")
        self.assertEqual(
            update_params[1],
            "Updated Buyer Agency Agreement",
        )
        self.assertEqual(str(update_params[2]), "2026-09-20")
        self.assertIsNone(update_params[3])
        self.assertEqual(
            update_params[4],
            "Updated shared relationship",
        )
        self.assertEqual(update_params[5], 700)
        self.assertEqual(update_params[6], 101)

        delete_sql, delete_params = normalized_calls[5]
        self.assertIn(
            "DELETE FROM client_relationship_contacts",
            delete_sql,
        )
        self.assertEqual(delete_params, (101, 700, 56))

        insert_sql, insert_params = normalized_calls[6]
        self.assertIn(
            "INSERT INTO client_relationship_contacts",
            insert_sql,
        )
        self.assertEqual(insert_params, (101, 700, 57))

        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_edit_client_relationship_can_remove_page_contact(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        cur.fetchone.side_effect = [
            {"id": 55},
            {
                "id": 700,
                "status": "current",
                "signed_date": "2026-09-21",
                "end_date": None,
            },
        ]
        cur.fetchall.return_value = [
            {"contact_id": 55},
            {"contact_id": 56},
        ]
        cur.rowcount = 1
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.post(
            "/contacts/55/client-relationships/700/edit",
            data={
                "relationship_type": "Buyer",
                "agreement_type": "Buyer Agency Agreement",
                "signed_date": "2026-09-21",
                "member_contact_ids": ["56"],
            },
        )

        self.assertEqual(response.status_code, 302)

        normalized_calls = [
            (" ".join(call.args[0].split()), call.args[1])
            for call in cur.execute.call_args_list
        ]

        delete_calls = [
            (sql, params)
            for sql, params in normalized_calls
            if "DELETE FROM client_relationship_contacts" in sql
        ]
        self.assertEqual(len(delete_calls), 1)
        self.assertEqual(delete_calls[0][1], (101, 700, 55))

        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_edit_client_relationship_rejects_unassociated_new_member(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        cur.fetchone.side_effect = [
            {"id": 55},
            {
                "id": 700,
                "status": "current",
                "signed_date": "2026-09-21",
                "end_date": None,
            },
        ]
        cur.fetchall.side_effect = [
            [{"contact_id": 55}],
            [{"other_contact_id": 56}],
        ]
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.post(
            "/contacts/55/client-relationships/700/edit",
            data={
                "relationship_type": "Buyer",
                "agreement_type": "Buyer Agency Agreement",
                "signed_date": "2026-09-21",
                "member_contact_ids": ["55", "999"],
            },
        )

        self.assertEqual(response.status_code, 404)

        executed_sql = " ".join(
            " ".join(call.args[0].split())
            for call in cur.execute.call_args_list
        )
        self.assertNotIn(
            "UPDATE client_relationships SET",
            executed_sql,
        )
        self.assertNotIn(
            "DELETE FROM client_relationship_contacts",
            executed_sql,
        )
        self.assertNotIn(
            "INSERT INTO client_relationship_contacts",
            executed_sql,
        )

        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_edit_client_relationship_rejects_foreign_or_nonmember_relationship(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        # Page Contact belongs to the user, but relationship 999 is either
        # foreign or Contact 55 is not one of its members.
        cur.fetchone.side_effect = [
            {"id": 55},
            None,
        ]
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.post(
            "/contacts/55/client-relationships/999/edit",
            data={
                "relationship_type": "Buyer",
                "agreement_type": "Buyer Agency Agreement",
                "signed_date": "2026-09-21",
                "member_contact_ids": ["55"],
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(cur.execute.call_count, 2)

        lookup_sql, lookup_params = cur.execute.call_args_list[1].args
        normalized = " ".join(lookup_sql.split())

        self.assertIn(
            "JOIN client_relationship_contacts crc",
            normalized,
        )
        self.assertIn("AND cr.user_id = %s", normalized)
        self.assertIn("AND crc.contact_id = %s", normalized)
        self.assertEqual(lookup_params, (999, 101, 55))

        conn.commit.assert_not_called()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()


    @patch("app.get_db")
    def test_end_client_relationship_is_tenant_and_membership_scoped(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.rowcount = 1
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.post(
            "/contacts/55/client-relationships/700/end",
            data={"end_date": "2026-09-21"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(cur.execute.call_count, 1)

        update_sql, update_params = cur.execute.call_args.args
        normalized = " ".join(update_sql.split())

        self.assertIn(
            "UPDATE client_relationships AS cr",
            normalized,
        )
        self.assertIn("SET status = 'ended'", normalized)
        self.assertIn("end_date = %s", normalized)
        self.assertIn("WHERE cr.id = %s", normalized)
        self.assertIn("AND cr.user_id = %s", normalized)
        self.assertIn("AND cr.status = 'current'", normalized)
        self.assertIn("AND cr.signed_date <= %s", normalized)
        self.assertIn(
            "FROM client_relationship_contacts crc",
            normalized,
        )
        self.assertIn(
            "crc.user_id = cr.user_id",
            normalized,
        )
        self.assertIn(
            "crc.relationship_id = cr.id",
            normalized,
        )
        self.assertIn(
            "crc.contact_id = %s",
            normalized,
        )
        self.assertNotIn("cr.contact_id = %s", normalized)

        self.assertEqual(str(update_params[0]), "2026-09-21")
        self.assertEqual(update_params[1], 700)
        self.assertEqual(update_params[2], 101)
        self.assertEqual(str(update_params[3]), "2026-09-21")
        self.assertEqual(update_params[4], 55)

        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    @patch("app.get_db")
    def test_end_client_relationship_rejects_foreign_or_nonmember_row(
        self,
        get_db,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        # A foreign relationship, non-member Contact, or already-ended
        # relationship cannot satisfy the tenant- and membership-scoped UPDATE.
        cur.rowcount = 0
        get_db.return_value = conn

        self.login_as(101)

        response = self.client.post(
            "/contacts/55/client-relationships/999/end",
            data={"end_date": "2026-09-21"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(cur.execute.call_count, 1)

        update_sql, update_params = cur.execute.call_args.args
        normalized = " ".join(update_sql.split())

        self.assertIn(
            "UPDATE client_relationships AS cr",
            normalized,
        )
        self.assertIn("AND cr.user_id = %s", normalized)
        self.assertIn(
            "FROM client_relationship_contacts crc",
            normalized,
        )
        self.assertIn(
            "crc.user_id = cr.user_id",
            normalized,
        )
        self.assertIn(
            "crc.relationship_id = cr.id",
            normalized,
        )
        self.assertIn(
            "crc.contact_id = %s",
            normalized,
        )
        self.assertNotIn("cr.contact_id = %s", normalized)

        self.assertEqual(update_params[1], 999)
        self.assertEqual(update_params[2], 101)
        self.assertEqual(update_params[4], 55)

        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()


    @patch("app.render_template")
    @patch("app.get_db")
    def test_past_clients_requires_ended_and_excludes_current_relationships(
        self,
        get_db,
        render_template,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur

        cur.fetchone.return_value = {"total": 1}
        cur.fetchall.return_value = []
        get_db.return_value = conn
        render_template.return_value = "rendered"

        self.login_as(101)

        response = self.client.get("/contacts?tab=clients&client_status=past")

        self.assertEqual(response.status_code, 200)

        execute_calls = cur.execute.call_args_list
        self.assertGreaterEqual(len(execute_calls), 2)

        count_sql, count_params = execute_calls[0].args
        data_sql, data_params = execute_calls[1].args

        count_normalized = " ".join(count_sql.split())
        data_normalized = " ".join(data_sql.split())

        for sql in (count_normalized, data_normalized):
            self.assertIn("FROM contacts", sql)
            self.assertIn("user_id = %s", sql)
            self.assertIn("EXISTS (", sql)
            self.assertIn("FROM client_relationships cr_ended", sql)
            self.assertIn(
                "JOIN client_relationship_contacts crc_ended", sql
            )
            self.assertIn("cr_ended.user_id = %s", sql)
            self.assertIn(
                "crc_ended.user_id = cr_ended.user_id", sql
            )
            self.assertIn(
                "crc_ended.relationship_id = cr_ended.id", sql
            )
            self.assertIn(
                "crc_ended.contact_id = contacts.id", sql
            )
            self.assertIn("cr_ended.status = 'ended'", sql)
            self.assertIn("AND NOT EXISTS (", sql)
            self.assertIn("FROM client_relationships cr_current", sql)
            self.assertIn(
                "JOIN client_relationship_contacts crc_current", sql
            )
            self.assertIn("cr_current.user_id = %s", sql)
            self.assertIn(
                "crc_current.user_id = cr_current.user_id", sql
            )
            self.assertIn(
                "crc_current.relationship_id = cr_current.id", sql
            )
            self.assertIn(
                "crc_current.contact_id = contacts.id", sql
            )
            self.assertIn("cr_current.status = 'current'", sql)
            self.assertNotIn("pipeline_stage = %s", sql)

        self.assertEqual(count_params, (101, 101, 101))
        self.assertEqual(data_params, (101, 101, 101, 101, 10, 0))

        render_kwargs = render_template.call_args.kwargs
        self.assertEqual(render_kwargs["active_tab"], "clients")
        self.assertEqual(render_kwargs["client_status"], "past")



    @patch("app.render_template")
    @patch("app.get_db")
    def test_all_clients_includes_current_or_ended_relationships(
        self,
        get_db,
        render_template,
    ):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = {"total": 1}
        cur.fetchall.return_value = []
        get_db.return_value = conn
        render_template.return_value = "rendered"

        self.login_as(101)

        response = self.client.get("/contacts?tab=clients&client_status=all")

        self.assertEqual(response.status_code, 200)

        count_sql, count_params = cur.execute.call_args_list[0].args
        data_sql, data_params = cur.execute.call_args_list[1].args

        for sql in (
            " ".join(count_sql.split()),
            " ".join(data_sql.split()),
        ):
            self.assertIn("FROM contacts", sql)
            self.assertIn("user_id = %s", sql)
            self.assertIn("EXISTS (", sql)
            self.assertIn("FROM client_relationships cr", sql)
            self.assertIn(
                "JOIN client_relationship_contacts crc", sql
            )
            self.assertIn("cr.user_id = %s", sql)
            self.assertIn("crc.user_id = cr.user_id", sql)
            self.assertIn("crc.relationship_id = cr.id", sql)
            self.assertIn("crc.contact_id = contacts.id", sql)
            self.assertIn(
                "cr.status IN ('current', 'ended')",
                sql,
            )
            self.assertNotIn("JOIN client_relationships", sql)

        self.assertEqual(count_params, (101, 101))
        self.assertEqual(data_params, (101, 101, 101, 10, 0))

        render_kwargs = render_template.call_args.kwargs
        self.assertEqual(render_kwargs["active_tab"], "clients")
        self.assertEqual(render_kwargs["client_status"], "all")


    @patch("app.render_template")
    @patch("app.get_db")
    def test_client_views_exclude_archived_contacts(
        self,
        get_db,
        render_template,
    ):
        for client_status in ("current", "past", "all"):
            with self.subTest(client_status=client_status):
                conn = MagicMock()
                cur = MagicMock()
                conn.cursor.return_value = cur
                cur.fetchone.return_value = {"total": 0}
                cur.fetchall.return_value = []
                get_db.return_value = conn
                render_template.return_value = "rendered"

                self.login_as(101)

                response = self.client.get(
                    f"/contacts?tab=clients&client_status={client_status}"
                    "&show_archived=1"
                )

                self.assertEqual(response.status_code, 200)

                count_sql = cur.execute.call_args_list[0].args[0]
                data_sql = cur.execute.call_args_list[1].args[0]

                for sql in (
                    " ".join(count_sql.split()),
                    " ".join(data_sql.split()),
                ):
                    self.assertIn("user_id = %s", sql)
                    self.assertIn("archived_at IS NULL", sql)
                    self.assertIn("FROM client_relationships", sql)
                    self.assertIn(
                        "JOIN client_relationship_contacts", sql
                    )



    @patch("app.render_template")
    @patch("app.get_db")
    def test_client_type_select_is_tenant_scoped_and_status_aware(
        self,
        get_db,
        render_template,
    ):
        expectations = {
            "current": "cr_types.status = 'current'",
            "past": "cr_types.status = 'ended'",
            "all": "cr_types.status IN ('current', 'ended')",
        }

        for client_status, status_sql in expectations.items():
            with self.subTest(client_status=client_status):
                conn = MagicMock()
                cur = MagicMock()
                conn.cursor.return_value = cur
                cur.fetchone.return_value = {"total": 0}
                cur.fetchall.return_value = []
                get_db.return_value = conn
                render_template.return_value = "rendered"

                self.login_as(101)

                response = self.client.get(
                    f"/contacts?tab=clients&client_status={client_status}"
                )

                self.assertEqual(response.status_code, 200)

                data_sql, data_params = cur.execute.call_args_list[1].args
                normalized = " ".join(data_sql.split())

                self.assertIn(
                    "string_agg( DISTINCT cr_types.relationship_type",
                    normalized,
                )
                self.assertIn(
                    "FROM client_relationships cr_types",
                    normalized,
                )
                self.assertIn("cr_types.user_id = %s", normalized)
                self.assertNotIn("cr_types.user_id = 101", normalized)
                self.assertEqual(data_params[0], 101)
                self.assertIn(
                    "JOIN client_relationship_contacts crc_types",
                    normalized,
                )
                self.assertIn(
                    "crc_types.user_id = cr_types.user_id",
                    normalized,
                )
                self.assertIn(
                    "crc_types.relationship_id = cr_types.id",
                    normalized,
                )
                self.assertIn(
                    "crc_types.contact_id = contacts.id",
                    normalized,
                )
                self.assertIn(status_sql, normalized)
                self.assertIn("AS client_types", normalized)


    def test_client_pagination_preserves_client_status(self):
        template = Path("templates/contacts.html").read_text()

        self.assertIn(
            "client_status=client_status if active_tab == 'clients' else None",
            template,
        )
        self.assertEqual(
            template.count(
                "client_status=client_status if active_tab == 'clients' else None"
            ),
            3,
        )



if __name__ == "__main__":
    unittest.main()
