# engagements.py
# CRUD helpers for Engagements in Ulysses CRM.
# Designed to be imported by app.py without creating circular imports.

from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor


def ensure_engagements_table(conn) -> None:
    """
    Creates the engagements table if it does not exist.
    Safe to run on startup.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS engagements (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NULL,
                contact_id INTEGER NOT NULL,

                engagement_type TEXT NULL,
                subject TEXT NULL,

                -- raw or cleaned transcript text
                transcript TEXT NULL,

                -- short summary
                summary TEXT NULL,

                -- CRM-ready narrative note
                notes TEXT NULL,

                -- optional: who it was with, lender name, etc.
                counterpart TEXT NULL,

                -- date/time metadata (stored separately for easier querying)
                engagement_date DATE NULL,
                engagement_time TIME NULL,

                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )

        # Helpful index for contact timeline views
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_engagements_contact_id
            ON engagements (contact_id);
            """
        )

        # If you are using multi-user scoping, this helps too
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_engagements_user_id
            ON engagements (user_id);
            """
        )

    conn.commit()


def _dict_cur(conn):
    return conn.cursor(cursor_factory=RealDictCursor)


def list_engagements_for_contact(
    conn,
    contact_id: int,
    user_id: Optional[int] = None,
    newest_first: bool = True,
) -> List[Dict[str, Any]]:
    """
    Returns all engagements for a contact.
    If user_id is provided, filters to that user.
    """
    order = "DESC" if newest_first else "ASC"
    with _dict_cur(conn) as cur:
        if user_id is None:
            cur.execute(
                f"""
                SELECT *
                FROM engagements
                WHERE contact_id = %s
                ORDER BY
                  COALESCE(engagement_date, DATE(created_at)) {order},
                  COALESCE(engagement_time, created_at::time) {order},
                  id {order};
                """,
                (contact_id,),
            )
        else:
            cur.execute(
                f"""
                SELECT *
                FROM engagements
                WHERE contact_id = %s
                  AND user_id = %s
                ORDER BY
                  COALESCE(engagement_date, DATE(created_at)) {order},
                  COALESCE(engagement_time, created_at::time) {order},
                  id {order};
                """,
                (contact_id, user_id),
            )
        return cur.fetchall() or []


def get_engagement_by_id(
    conn,
    engagement_id: int,
    user_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetch a single engagement.
    If user_id is provided, enforces ownership.
    """
    with _dict_cur(conn) as cur:
        if user_id is None:
            cur.execute("SELECT * FROM engagements WHERE id = %s;", (engagement_id,))
        else:
            cur.execute(
                "SELECT * FROM engagements WHERE id = %s AND user_id = %s;",
                (engagement_id, user_id),
            )
        return cur.fetchone()


def create_engagement(
    conn,
    contact_id: int,
    *,
    user_id: Optional[int] = None,
    engagement_type: Optional[str] = None,
    subject: Optional[str] = None,
    transcript: Optional[str] = None,
    summary: Optional[str] = None,
    notes: Optional[str] = None,
    counterpart: Optional[str] = None,
    engagement_date: Optional[date] = None,
    engagement_time: Optional[str] = None,  # "HH:MM" or "HH:MM:SS"
) -> int:
    """
    Inserts an engagement and returns the new engagement id.
    engagement_time can be a string to avoid time parsing in app.py.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO engagements
                (user_id, contact_id, engagement_type, subject,
                 transcript, summary, notes, counterpart,
                 engagement_date, engagement_time)
            VALUES
                (%s, %s, %s, %s,
                 %s, %s, %s, %s,
                 %s, %s)
            RETURNING id;
            """,
            (
                user_id,
                contact_id,
                _clean_text(engagement_type),
                _clean_text(subject),
                _clean_text(transcript),
                _clean_text(summary),
                _clean_text(notes),
                _clean_text(counterpart),
                engagement_date,
                engagement_time,
            ),
        )
        new_id = cur.fetchone()[0]
    conn.commit()
    return int(new_id)


def update_engagement(
    conn,
    engagement_id: int,
    *,
    user_id: Optional[int] = None,
    engagement_type: Optional[str] = None,
    subject: Optional[str] = None,
    transcript: Optional[str] = None,
    summary: Optional[str] = None,
    notes: Optional[str] = None,
    counterpart: Optional[str] = None,
    engagement_date: Optional[date] = None,
    engagement_time: Optional[str] = None,  # "HH:MM" or "HH:MM:SS"
) -> bool:
    """
    Updates an engagement.
    Returns True if a row was updated, False otherwise (not found / not owned).
    """
    where_clause = "id = %s"
    params: List[Any] = []

    params.extend(
        [
            _clean_text(engagement_type),
            _clean_text(subject),
            _clean_text(transcript),
            _clean_text(summary),
            _clean_text(notes),
            _clean_text(counterpart),
            engagement_date,
            engagement_time,
        ]
    )

    if user_id is None:
        where_clause = "id = %s"
        params.append(engagement_id)
    else:
        where_clause = "id = %s AND user_id = %s"
        params.extend([engagement_id, user_id])

    with conn.cursor() as cur:
        cur.execute(
            f"""
            UPDATE engagements
            SET
                engagement_type = %s,
                subject = %s,
                transcript = %s,
                summary = %s,
                notes = %s,
                counterpart = %s,
                engagement_date = %s,
                engagement_time = %s,
                updated_at = NOW()
            WHERE {where_clause};
            """,
            tuple(params),
        )
        updated = cur.rowcount > 0

    conn.commit()
    return updated


def delete_engagement(
    conn,
    engagement_id: int,
    user_id: Optional[int] = None,
) -> bool:
    """
    Deletes an engagement.
    Returns True if deleted, False otherwise (not found / not owned).
    """
    with conn.cursor() as cur:
        if user_id is None:
            cur.execute("DELETE FROM engagements WHERE id = %s;", (engagement_id,))
        else:
            cur.execute(
                "DELETE FROM engagements WHERE id = %s AND user_id = %s;",
                (engagement_id, user_id),
            )
        deleted = cur.rowcount > 0
    conn.commit()
    return deleted


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip()
    return v if v else None
