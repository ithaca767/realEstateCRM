from datetime import datetime

def list_engagements_for_contact(conn, user_id, contact_id, limit=50, offset=0):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
          id,
          engagement_type,
          occurred_at,
          outcome,
          notes,
          summary_clean,
          transcript_raw,
          requires_follow_up,
          follow_up_due_at,
          follow_up_completed
        FROM engagements
        WHERE user_id = %s AND contact_id = %s
        ORDER BY occurred_at DESC NULLS LAST, id DESC
        LIMIT %s OFFSET %s
        """,
        (user_id, contact_id, limit, offset),
    )
    rows = cur.fetchall() or []
    return rows

from collections.abc import Mapping

def insert_engagement(
    conn,
    user_id: int,
    contact_id: int,
    engagement_type: str,
    occurred_at,
    outcome,
    notes,
    transcript_raw,
    summary_clean,
    requires_follow_up: bool = False,
    follow_up_due_at=None,
    commit: bool = True,
):
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO engagements
              (
                user_id,
                contact_id,
                engagement_type,
                occurred_at,
                outcome,
                notes,
                transcript_raw,
                summary_clean,
                requires_follow_up,
                follow_up_due_at,
                follow_up_completed,
                follow_up_completed_at
              )
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, NULL)
            RETURNING id
            """,
            (
                user_id,
                contact_id,
                engagement_type,
                occurred_at,
                outcome,
                notes,
                transcript_raw,
                summary_clean,
                requires_follow_up,
                follow_up_due_at,
            ),
        )
        row = cur.fetchone()
        new_id = None
        if row:
            new_id = row["id"] if isinstance(row, Mapping) else row[0]

        if commit:
            conn.commit()

        return new_id
    finally:
        cur.close()

def delete_engagement(conn, user_id: int, engagement_id: int):
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM engagements WHERE id = %s AND user_id = %s",
        (engagement_id, user_id),
    )
    conn.commit()
    return cur.rowcount
