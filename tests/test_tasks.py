import unittest

from tasks import _validate_task_associations


class FakeCursor:
    def __init__(self, results):
        self.results = list(results)
        self.executions = []

    def execute(self, sql, params):
        self.executions.append((sql, params))

    def fetchone(self):
        if not self.results:
            return None
        return self.results.pop(0)


class TaskAssociationValidationTests(unittest.TestCase):
    def test_independent_task_requires_no_association_queries(self):
        cur = FakeCursor([])

        _validate_task_associations(cur, 101, {})

        self.assertEqual(cur.executions, [])

    def test_contact_must_belong_to_user(self):
        cur = FakeCursor([None])

        with self.assertRaisesRegex(ValueError, "Invalid contact association"):
            _validate_task_associations(
                cur,
                101,
                {"contact_id": 55},
            )

        sql, params = cur.executions[0]
        self.assertIn("contacts", sql)
        self.assertIn("user_id", sql)
        self.assertEqual(params, (55, 101))

    def test_transaction_with_contact_must_match_user_and_contact(self):
        cur = FakeCursor([{"?column?": 1}, None])

        with self.assertRaisesRegex(ValueError, "Invalid transaction association"):
            _validate_task_associations(
                cur,
                101,
                {
                    "contact_id": 55,
                    "transaction_id": 77,
                },
            )

        sql, params = cur.executions[1]
        self.assertIn("transactions", sql)
        self.assertIn("user_id", sql)
        self.assertIn("contact_id", sql)
        self.assertEqual(params, (77, 101, 55))

    def test_engagement_with_contact_must_match_user_and_contact(self):
        cur = FakeCursor([{"?column?": 1}, None])

        with self.assertRaisesRegex(ValueError, "Invalid engagement association"):
            _validate_task_associations(
                cur,
                101,
                {
                    "contact_id": 55,
                    "engagement_id": 88,
                },
            )

        sql, params = cur.executions[1]
        self.assertIn("engagements", sql)
        self.assertIn("user_id", sql)
        self.assertIn("contact_id", sql)
        self.assertEqual(params, (88, 101, 55))

    def test_transaction_without_contact_is_allowed_when_user_owns_it(self):
        cur = FakeCursor([{"?column?": 1}])

        _validate_task_associations(
            cur,
            101,
            {"transaction_id": 77},
        )

        sql, params = cur.executions[0]
        self.assertIn("transactions", sql)
        self.assertIn("user_id", sql)
        self.assertEqual(params, (77, 101))

    def test_engagement_without_contact_is_allowed_when_user_owns_it(self):
        cur = FakeCursor([{"?column?": 1}])

        _validate_task_associations(
            cur,
            101,
            {"engagement_id": 88},
        )

        sql, params = cur.executions[0]
        self.assertIn("engagements", sql)
        self.assertIn("user_id", sql)
        self.assertEqual(params, (88, 101))

    def test_professional_must_belong_to_user(self):
        cur = FakeCursor([None])

        with self.assertRaisesRegex(ValueError, "Invalid professional association"):
            _validate_task_associations(
                cur,
                101,
                {"professional_id": 99},
            )

        sql, params = cur.executions[0]
        self.assertIn("professionals", sql)
        self.assertIn("user_id", sql)
        self.assertEqual(params, (99, 101))

    def test_valid_combined_associations_pass(self):
        cur = FakeCursor(
            [
                {"?column?": 1},
                {"?column?": 1},
                {"?column?": 1},
                {"?column?": 1},
            ]
        )

        _validate_task_associations(
            cur,
            101,
            {
                "contact_id": 55,
                "transaction_id": 77,
                "engagement_id": 88,
                "professional_id": 99,
            },
        )

        self.assertEqual(len(cur.executions), 4)


if __name__ == "__main__":
    unittest.main()
