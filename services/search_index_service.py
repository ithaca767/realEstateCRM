from psycopg2.extras import RealDictCursor
from services.search_indexer import upsert_search_index


def upsert_engagement_index(conn, user_id: int, engagement_id: int):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT id, contact_id, occurred_at, engagement_type, summary_clean, notes, transcript_raw
        FROM engagements
        WHERE id = %s AND user_id = %s
        """,
        (engagement_id, user_id),
    )
    e = cur.fetchone()
    if not e:
        return

    etype = (e.get("engagement_type") or "").replace("_", " ").title()
    occurred = e.get("occurred_at")
    occurred_label = occurred.date().isoformat() if occurred else ""
    label = f"{etype} {occurred_label}".strip() or f"Engagement {e['id']}"

    best_text = (
        (e.get("summary_clean") or "").strip()
        or (e.get("notes") or "").strip()
        or (e.get("transcript_raw") or "").strip()
    )

    search_text = " \n".join([x for x in [label, best_text] if x])

    upsert_search_index(
        conn,
        user_id=user_id,
        object_type="engagement",
        object_id=e["id"],
        contact_id=e.get("contact_id"),
        label=label,
        search_text=search_text,
    )
