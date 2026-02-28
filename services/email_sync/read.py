# services/email_sync/read.py

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _format_timestamp(dt) -> str:
    if not dt:
        return ""
    return dt.strftime("%b %d, %Y at %-I:%M %p")


def list_messages_for_contact(
    conn,
    *,
    user_id: int,
    contact_id: int,
    limit: int = 50,
    offset: int = 0,
    direction: str = "all",     # inbound|outbound|unknown|all
    days: str = "90",           # 30|90|365|all
    q: str = "",                # free-text search over subject/snippet
    from_email: str = "",       # free-text search over from_email
) -> List[Dict[str, Any]]:
    """
    Returns email messages linked to a contact via email_message_links, newest first.
    Includes link_count for display.
    Supports basic filters: direction, date window (days), search (q), from_email.
    """
    direction = (direction or "all").strip().lower()
    days = (days or "90").strip().lower()
    q = (q or "").strip()
    from_email = (from_email or "").strip()

    where_clauses = [
        "em.user_id = %s",
        "l.contact_id = %s",
    ]
    params: List[Any] = [user_id, contact_id]

    # Direction filter
    if direction in ("inbound", "outbound", "unknown"):
        where_clauses.append("em.direction = %s")
        params.append(direction)

    # Date window filter (message_date can be NULL; exclude NULLs when filtering by days)
    if days in ("30", "90", "365"):
        where_clauses.append("em.message_date IS NOT NULL")
        where_clauses.append("em.message_date >= NOW() - (%s || ' days')::interval")
        params.append(days)

    # Free-text filter over subject/snippet
    if q:
        where_clauses.append("(COALESCE(em.subject,'') ILIKE %s OR COALESCE(em.snippet,'') ILIKE %s)")
        like = f"%{q}%"
        params.extend([like, like])

    # From filter
    if from_email:
        where_clauses.append("COALESCE(em.from_email,'') ILIKE %s")
        params.append(f"%{from_email}%")

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT
            em.id,
            em.message_date,
            em.direction,
            em.subject,
            em.snippet,
            em.from_email,
            em.to_emails,
            em.cc_emails,
            COUNT(l2.id) AS link_count
        FROM email_messages em
        JOIN email_message_links l
          ON l.user_id = em.user_id
         AND l.email_message_id = em.id
        LEFT JOIN email_message_links l2
          ON l2.user_id = em.user_id
         AND l2.email_message_id = em.id
        WHERE {where_sql}
        GROUP BY em.id
        ORDER BY em.message_date DESC NULLS LAST, em.id DESC
        LIMIT %s OFFSET %s
    """

    params.extend([int(limit), int(offset)])

    cur = conn.cursor()
    cur.execute(sql, tuple(params))

    rows = cur.fetchall() or []
    out: List[Dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        row["message_date_display"] = _format_timestamp(row.get("message_date"))
        out.append(row)
    return out