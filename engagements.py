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
          follow_up_completed,
          parent_engagement_id
        FROM engagements
        WHERE user_id = %s
          AND contact_id = %s
          AND parent_engagement_id IS NULL
        ORDER BY occurred_at DESC NULLS LAST, id DESC
        LIMIT %s OFFSET %s
        """,
        (user_id, contact_id, limit, offset),
    )
    return cur.fetchall() or []
def list_child_followups_for_parents(conn, user_id: int, contact_id: int, parent_ids: list[int]):
    if not parent_ids:
        return []

    cur = conn.cursor()
    cur.execute(
        """
        SELECT
          id,
          user_id,
          contact_id,
          parent_engagement_id,
          engagement_type,
          occurred_at,
          outcome,
          notes,
          summary_clean,
          requires_follow_up,
          follow_up_due_at,
          follow_up_completed,
          follow_up_completed_at
        FROM engagements
        WHERE user_id = %s
          AND contact_id = %s
          AND parent_engagement_id = ANY(%s)
        ORDER BY
          follow_up_completed ASC,
          follow_up_due_at ASC NULLS LAST,
          id DESC
        """,
        (user_id, contact_id, parent_ids),
    )
    return cur.fetchall() or []
    
from collections.abc import Mapping

def insert_engagement(
    conn,
    user_id: int,
    contact_id: int,
    engagement_type: str,
    occurred_at,
    outcome=None,
    notes=None,
    transcript_raw=None,
    summary_clean=None,
    parent_engagement_id=None,
    requires_follow_up: bool = False,
    follow_up_due_at=None,
    follow_up_completed: bool = False,
    follow_up_completed_at=None,
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
                parent_engagement_id,
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
              (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                contact_id,
                parent_engagement_id,
                engagement_type,
                occurred_at,
                outcome,
                notes,
                transcript_raw,
                summary_clean,
                requires_follow_up,
                follow_up_due_at,
                follow_up_completed,
                follow_up_completed_at,
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
