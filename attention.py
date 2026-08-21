from datetime import datetime, timezone
from psycopg2.extras import RealDictCursor


ATTENTION_TYPE_OVERDUE_FOLLOWUP = "overdue_followup"


def _require_aware_datetime(value):
    if value is None:
        return datetime.now(timezone.utc)

    if not isinstance(value, datetime):
        raise TypeError("now must be a datetime or None")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    return value


def list_attention_items(conn, user_id: int, now=None):
    """
    Return current deterministic Attention candidates for one user.

    V1A scope:
      - overdue child Follow-ups only
      - read-only
      - no database writes
      - no AI
      - no tasks or transaction deadlines

    A Follow-up requires attention when:
      - it is a child engagement
      - requires_follow_up is true
      - it is not completed
      - it has a due timestamp
      - its due timestamp is at or before `now`
    """
    if not user_id:
        raise ValueError("user_id is required")

    now = _require_aware_datetime(now)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                e.id AS source_id,
                e.contact_id,
                COALESCE(
                    NULLIF(TRIM(CONCAT_WS(' ', c.first_name, c.last_name)), ''),
                    NULLIF(TRIM(c.name), ''),
                    '(Unnamed contact)'
                ) AS contact_name,
                e.follow_up_due_at AS due_at,

                COALESCE(
                    NULLIF(TRIM(e.outcome), ''),
                    NULLIF(TRIM(e.summary_clean), ''),
                    NULLIF(TRIM(e.notes), ''),
                    NULLIF(TRIM(p.outcome), ''),
                    NULLIF(TRIM(p.summary_clean), ''),
                    NULLIF(TRIM(p.notes), ''),
                    'Follow-up requires attention'
                ) AS snippet

            FROM engagements e

            JOIN contacts c
              ON c.id = e.contact_id
             AND c.user_id = e.user_id

            LEFT JOIN engagements p
              ON p.id = e.parent_engagement_id
             AND p.user_id = e.user_id

            WHERE e.user_id = %s
              AND c.archived_at IS NULL
              AND e.parent_engagement_id IS NOT NULL
              AND e.requires_follow_up = TRUE
              AND e.follow_up_completed = FALSE
              AND e.follow_up_due_at IS NOT NULL
              AND e.follow_up_due_at <= %s

            ORDER BY
                e.follow_up_due_at ASC,
                e.id ASC
            """,
            (user_id, now),
        )

        rows = cur.fetchall()

    items = []

    for row in rows:
        items.append(
            {
                "attention_type": ATTENTION_TYPE_OVERDUE_FOLLOWUP,
                "source_type": "engagement",
                "source_id": row["source_id"],
                "contact_id": row["contact_id"],
                "contact_name": row["contact_name"],
                "due_at": row["due_at"],
                "snippet": row["snippet"],
            }
        )

    return items
