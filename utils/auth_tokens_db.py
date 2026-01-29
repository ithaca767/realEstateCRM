from typing import Any, Dict, Optional

from utils.token_helpers import (
    expires_at_from_now,
    generate_raw_token,
    hash_token,
    is_expired,
    utcnow,
)

# Suggested defaults (canon-safe and adjustable later)
INVITE_TTL_MINUTES = 60 * 24 * 3  # 3 days
RESET_TTL_MINUTES = 60            # 60 minutes


def create_user_invite(
    conn,
    invited_email: str,
    role: str,
    invited_by_user_id: int,
    note: Optional[str] = None,
    ttl_minutes: int = INVITE_TTL_MINUTES,
) -> Dict[str, Any]:
    raw = generate_raw_token()
    token_hash = hash_token(raw)
    expires_at = expires_at_from_now(ttl_minutes)

    email_norm = (invited_email or "").strip().lower()
    if not email_norm:
        raise ValueError("invited_email is required")

    role_norm = (role or "").strip().lower() or "user"
    if role_norm not in ("owner", "user"):
        raise ValueError("role must be 'owner' or 'user'")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_invites (invited_email, role, token_hash, invited_by_user_id, note, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, invited_email, role, created_at, expires_at;
            """,
            (email_norm, role_norm, token_hash, invited_by_user_id, note, expires_at),
        )
        row = cur.fetchone()

    conn.commit()

    return {
        "id": row["id"],
        "invited_email": row["invited_email"],
        "role": row["role"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "raw_token": raw,          # show once to the owner/admin
        "token_hash": token_hash,  # never display
    }


def get_valid_invite_by_raw_token(conn, raw_token: str) -> Optional[Dict[str, Any]]:
    """
    Returns invite row if token exists and is active.
    Active means: not used, not revoked, not expired.
    """
    token_hash = hash_token(raw_token)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, invited_email, role, invited_by_user_id, created_at, expires_at, used_at, revoked_at
            FROM user_invites
            WHERE token_hash = %s
            LIMIT 1;
            """,
            (token_hash,),
        )
        row = cur.fetchone()

    if not row:
        return None

    invite = dict(row)

    if invite.get("used_at") is not None:
        return None
    if invite.get("revoked_at") is not None:
        return None
    if is_expired(invite.get("expires_at")):
        return None

    return invite


def consume_invite(conn, invite_id, used_by_user_id: int) -> bool:
    """
    Marks invite as used exactly once.
    Returns True if consumed now, False if it was not consumable.
    """
    now = utcnow()
    invite_id_str = str(invite_id)

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE user_invites
            SET used_at = %s, used_by_user_id = %s
            WHERE id = %s::uuid
              AND used_at IS NULL
              AND revoked_at IS NULL
              AND expires_at > %s;
            """,
            (now, used_by_user_id, invite_id, now),
        )
        updated = cur.rowcount

    conn.commit()
    return updated == 1


def revoke_invite(conn, invite_id) -> bool:
    now = utcnow()
    invite_id_str = str(invite_id)

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE user_invites
            SET revoked_at = %s
            WHERE id = %s::uuid
              AND used_at IS NULL
              AND revoked_at IS NULL;
            """,
            (now, invite_id_str),
        )
        updated = cur.rowcount

    conn.commit()
    return updated == 1

def create_password_reset(
    conn,
    user_id: int,
    request_ip: Optional[str],
    request_user_agent: Optional[str],
    ttl_minutes: int = RESET_TTL_MINUTES,
) -> Dict[str, Any]:
    raw = generate_raw_token()
    token_hash = hash_token(raw)
    expires_at = expires_at_from_now(ttl_minutes)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO password_resets (user_id, token_hash, request_ip, request_user_agent, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, user_id, created_at, expires_at;
            """,
            (user_id, token_hash, request_ip, request_user_agent, expires_at),
        )
        row = cur.fetchone()

    conn.commit()

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "raw_token": raw,          # show once for copy/paste link
        "token_hash": token_hash,  # never display
    }


def get_valid_password_reset_by_raw_token(conn, raw_token: str) -> Optional[Dict[str, Any]]:
    token_hash = hash_token(raw_token)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, created_at, expires_at, used_at, revoked_at
            FROM password_resets
            WHERE token_hash = %s
            LIMIT 1;
            """,
            (token_hash,),
        )
        row = cur.fetchone()

    if not row:
        return None

    reset = dict(row)

    if reset.get("used_at") is not None:
        return None
    if reset.get("revoked_at") is not None:
        return None
    if is_expired(reset.get("expires_at")):
        return None

    return reset


def consume_password_reset(conn, reset_id) -> bool:
    now = utcnow()

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE password_resets
            SET used_at = %s
            WHERE id = %s
              AND used_at IS NULL
              AND revoked_at IS NULL
              AND expires_at > %s;
            """,
            (now, reset_id, now),
        )
        updated = cur.rowcount

    conn.commit()
    return updated == 1


def revoke_all_password_resets_for_user(conn, user_id: int) -> int:
    now = utcnow()

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE password_resets
            SET revoked_at = %s
            WHERE user_id = %s
              AND used_at IS NULL
              AND revoked_at IS NULL;
            """,
            (now, user_id),
        )
        updated = cur.rowcount

    conn.commit()
    return updated
