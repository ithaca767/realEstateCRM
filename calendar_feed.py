from typing import Any, Dict, Optional

from utils.token_helpers import generate_raw_token, hash_token, utcnow


def create_calendar_feed_token(conn, user_id: int) -> Dict[str, Any]:
    """
    Create a new active calendar-feed credential for exactly one user.

    Any existing active credential for that user is revoked first.
    The raw token is returned once and is never stored.
    """
    raw_token = generate_raw_token()
    token_hash = hash_token(raw_token)
    now = utcnow()

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE calendar_feed_tokens
            SET revoked_at = %s
            WHERE user_id = %s
              AND revoked_at IS NULL;
            """,
            (now, user_id),
        )

        cur.execute(
            """
            INSERT INTO calendar_feed_tokens (
                user_id,
                token_hash
            )
            VALUES (%s, %s)
            RETURNING id, user_id, created_at;
            """,
            (user_id, token_hash),
        )
        row = cur.fetchone()

    conn.commit()

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "created_at": row["created_at"],
        "raw_token": raw_token,
    }


def resolve_calendar_feed_token(
    conn,
    raw_token: str,
) -> Optional[Dict[str, Any]]:
    """
    Resolve an active raw calendar token to exactly one owning user.

    Tenant identity comes only from the credential. Callers must not supply
    or override user_id.

    Returns None for missing, invalid, revoked, inactive-user, or ambiguous
    credentials.
    """
    raw = (raw_token or "").strip()
    if not raw:
        return None

    token_hash = hash_token(raw)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                cft.id AS calendar_feed_token_id,
                cft.user_id,
                u.timezone_name
            FROM calendar_feed_tokens cft
            JOIN users u
              ON u.id = cft.user_id
            WHERE cft.token_hash = %s
              AND cft.revoked_at IS NULL
              AND u.is_active = TRUE
            LIMIT 2;
            """,
            (token_hash,),
        )
        rows = cur.fetchall()

    if len(rows) != 1:
        return None

    row = rows[0]

    return {
        "calendar_feed_token_id": row["calendar_feed_token_id"],
        "user_id": row["user_id"],
        "timezone_name": row.get("timezone_name") or "America/New_York",
    }


def revoke_calendar_feed_token(conn, user_id: int) -> bool:
    """
    Revoke the active calendar-feed credential belonging to exactly one user.
    """
    now = utcnow()

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE calendar_feed_tokens
            SET revoked_at = %s
            WHERE user_id = %s
              AND revoked_at IS NULL;
            """,
            (now, user_id),
        )
        updated = cur.rowcount

    conn.commit()
    return updated == 1
