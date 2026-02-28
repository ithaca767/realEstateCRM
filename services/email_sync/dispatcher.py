from __future__ import annotations

import json
from typing import Any, Dict


def cleanup_unlinked_messages(conn, *, user_id: int, email_account_id: int, keep_unlinked: int = 500) -> int:
    if keep_unlinked < 0:
        raise ValueError("keep_unlinked must be >= 0")

    with conn.cursor() as cur:
        cur.execute(
            """
            WITH doomed AS (
                SELECT em.id
                FROM email_messages em
                WHERE em.user_id = %s
                  AND em.email_account_id = %s
                  AND NOT EXISTS (
                    SELECT 1
                    FROM email_message_links l
                    WHERE l.user_id = em.user_id
                      AND l.email_message_id = em.id
                  )
                ORDER BY em.created_at DESC
                OFFSET %s
            )
            DELETE FROM email_messages em
            USING doomed
            WHERE em.id = doomed.id
            RETURNING em.id
            """,
            (user_id, email_account_id, int(keep_unlinked)),
        )
        rows = cur.fetchall() or []
        return len(rows)


def sync_email_account(
    conn,
    *,
    user_id: int,
    email_account_id: int,
    limit: int = 25,
) -> Dict[str, Any]:
    """
    Provider-agnostic sync entrypoint for Phase 10.
    Dispatches to the correct importer based on email_accounts.provider.
    Applies retention cleanup and updates last_synced_at/last_sync_stats.
    """
    if limit < 1 or limit > 200:
        raise ValueError("Invalid limit (1-200).")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, provider, sync_enabled
            FROM email_accounts
            WHERE id = %s AND user_id = %s
            """,
            (email_account_id, user_id),
        )
        acct = cur.fetchone()

    if not acct:
        raise ValueError("Email account not found.")
    if not acct["sync_enabled"]:
        raise ValueError("Email sync is disabled for this account.")

    provider = (acct["provider"] or "").strip().lower()

    if provider == "gmail":
        from services.email_sync.gmail_importer import import_last_messages_gmail

        stats = import_last_messages_gmail(
            conn,
            user_id=user_id,
            email_account_id=email_account_id,
            limit=limit,
        )

    elif provider == "outlook":
        from services.email_sync.outlook_importer import import_last_messages_outlook

        stats = import_last_messages_outlook(
            conn,
            user_id=user_id,
            email_account_id=email_account_id,
            limit=limit,
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")

    # retention
    deleted = cleanup_unlinked_messages(
        conn,
        user_id=user_id,
        email_account_id=email_account_id,
        keep_unlinked=500,
    )

    # telemetry (requires migration columns)
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE email_accounts
            SET last_sync_at = NOW(),
                last_sync_stats = %s::jsonb,
                updated_at = NOW()
            WHERE id = %s AND user_id = %s
            """,
            (json.dumps({**(stats or {}), "deleted_unlinked": deleted}), email_account_id, user_id),
        )

    conn.commit()

    out = dict(stats or {})
    out["deleted_unlinked"] = deleted
    return out