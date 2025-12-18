from datetime import datetime

def list_engagements_for_contact(conn, user_id: int, contact_id: int, limit: int = 50):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, engagement_type, occurred_at, outcome, notes, transcript_raw, summary_clean
        FROM engagements
        WHERE user_id = %s AND contact_id = %s
        ORDER BY occurred_at DESC, id DESC
        LIMIT %s
        """,
        (user_id, contact_id, limit),
    )
    rows = cur.fetchall()
    return rows

def insert_engagement(conn, user_id: int, contact_id: int, engagement_type: str, occurred_at, outcome, notes, transcript_raw, summary_clean):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO engagements
          (user_id, contact_id, engagement_type, occurred_at, outcome, notes, transcript_raw, summary_clean)
        VALUES
          (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (user_id, contact_id, engagement_type, occurred_at, outcome, notes, transcript_raw, summary_clean),
    )
    row = cur.fetchone()
    new_id = row["id"] if row else None

    conn.commit()
    return new_id

def delete_engagement(conn, user_id: int, engagement_id: int):
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM engagements WHERE id = %s AND user_id = %s",
        (engagement_id, user_id),
    )
    conn.commit()
    return cur.rowcount
