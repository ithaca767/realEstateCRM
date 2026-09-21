import unittest
from unittest.mock import MagicMock, patch

from services import ai_search
from services.search_service import (
    search_all,
    semantic_broaden,
)


class AISearchTenantIsolationTests(unittest.TestCase):
    def test_search_all_scopes_every_object_type_to_supplied_user(self):
        conn = MagicMock()

        with (
            patch(
                "services.search_service.search_contacts",
                return_value=[],
            ) as search_contacts,
            patch(
                "services.search_service.search_engagements",
                return_value=[],
            ) as search_engagements,
            patch(
                "services.search_service.search_transactions",
                return_value=[],
            ) as search_transactions,
            patch(
                "services.search_service.search_professionals",
                return_value=[],
            ) as search_professionals,
        ):
            search_all(conn, 101, "Tyler")

        search_contacts.assert_called_once_with(
            conn, 101, "Tyler", limit=20
        )
        search_engagements.assert_called_once_with(
            conn, 101, "Tyler", limit=30
        )
        search_transactions.assert_called_once_with(
            conn, 101, "Tyler", limit=20
        )
        search_professionals.assert_called_once_with(
            conn, 101, "Tyler", limit=20
        )

    @patch(
        "services.openai_client.call_embeddings_model",
        return_value=[0.1, 0.2, 0.3],
    )
    def test_semantic_search_is_tenant_scoped(
        self,
        call_embeddings_model,
    ):
        conn = MagicMock()
        cur = conn.cursor.return_value
        cur.fetchall.return_value = []

        result = semantic_broaden(
            conn,
            101,
            "Franklin",
            per_type_limit=10,
        )

        self.assertEqual(
            result,
            {
                "contacts": [],
                "engagements": [],
                "transactions": [],
                "professionals": [],
            },
        )

        sql, params = cur.execute.call_args.args
        normalized = " ".join(sql.split())

        self.assertIn("FROM search_index", normalized)
        self.assertIn("WHERE user_id = %s", normalized)
        self.assertEqual(params[1], 101)

    def test_engagement_hydration_is_tenant_scoped(self):
        conn = MagicMock()
        cur = conn.cursor.return_value
        cur.fetchall.return_value = []

        candidates = [
            ai_search.Candidate(
                type="engagement",
                id=77,
                label="Call",
                url="",
                snippet="",
                score=1.0,
                contact_id=55,
            )
        ]

        ai_search._hydrate_engagement_snippets(
            conn,
            101,
            candidates,
        )

        sql, params = cur.execute.call_args.args
        normalized = " ".join(sql.split())

        self.assertIn("FROM engagements", normalized)
        self.assertIn("WHERE user_id = %s", normalized)
        self.assertIn("AND id = ANY(%s::int[])", normalized)
        self.assertEqual(params, (101, [77]))

    @patch("services.ai_search.call_answer_model")
    @patch("services.ai_search.retrieve_candidates")
    @patch("services.ai_search._snapshot_allows")
    @patch("services.ai_search.ensure_ai_allowed_and_reset_if_needed")
    @patch("services.ai_search.is_ai_available", return_value=True)
    def test_guard_denial_stops_before_retrieval_or_model(
        self,
        is_ai_available,
        ensure_ai_allowed,
        snapshot_allows,
        retrieve_candidates,
        call_answer_model,
    ):
        ensure_ai_allowed.return_value = MagicMock()
        snapshot_allows.return_value = (
            False,
            "AI daily limit reached.",
        )

        result = ai_search.generate_answer(
            MagicMock(),
            101,
            "Tell me about Tyler",
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["no_answer"])
        self.assertEqual(result["answer"], "")
        self.assertEqual(result["citations"], [])
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(
            result["warning"],
            "AI daily limit reached.",
        )

        retrieve_candidates.assert_not_called()
        call_answer_model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
