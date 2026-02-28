# services/email_sync/outlook_importer.py
# Phase 10D: Outlook importer v1 (manual pull, snippet + recipients, contact auto-link)

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

# Reuse the proven helpers + schema insert/link behavior from Gmail importer
from services.email_sync.gmail_importer import (
    _decrypt_token,
    _encrypt_token,
    _fetch_account,
    _insert_email_message,
    _contact_id_for_email,
    _insert_link,
)

MS_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
MS_GRAPH_INBOX = f"{MS_GRAPH_BASE}/me/mailFolders/inbox/messages"
MS_GRAPH_SENT = f"{MS_GRAPH_BASE}/me/mailFolders/sentitems/messages"
MS_OAUTH_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


def _parse_graph_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        # "2026-02-26T03:12:34Z" or "...+00:00"
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _format_message_date(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    # Match the gmail_importer style: "%Y-%m-%d %H:%M:%S%z"
    # Ensure we have tz info; Graph should provide it
    try:
        return dt.strftime("%Y-%m-%d %H:%M:%S%z")
    except Exception:
        return None


def _extract_email_name(addr_obj: Optional[dict]) -> Tuple[Optional[str], Optional[str]]:
    """
    Graph shape: {"emailAddress": {"name": "...", "address": "x@y.com"}}
    """
    if not addr_obj:
        return (None, None)
    ea = addr_obj.get("emailAddress") or {}
    name = (ea.get("name") or "").strip() or None
    addr = (ea.get("address") or "").strip().lower() or None
    return (name, addr)


def _extract_emails(items: Optional[list]) -> List[str]:
    if not items:
        return []
    out: List[str] = []
    for it in items:
        _, addr = _extract_email_name(it)
        if addr:
            out.append(addr)
    # de-dupe preserving order
    seen = set()
    deduped: List[str] = []
    for e in out:
        if e not in seen:
            seen.add(e)
            deduped.append(e)
    return deduped


def _ms_refresh_access_token(refresh_token: str) -> Tuple[str, int]:
    # Uses MS_OAUTH_CLIENT_ID / MS_OAUTH_CLIENT_SECRET env vars (same as your callback)
    import os

    client_id = (os.getenv("MS_OAUTH_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("MS_OAUTH_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("Missing MS_OAUTH_CLIENT_ID / MS_OAUTH_CLIENT_SECRET for refresh.")

    resp = requests.post(
        MS_OAUTH_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            # scope is optional for refresh in many cases; omit to keep minimal
        },
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"MS token refresh failed {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    access_token = (data.get("access_token") or "").strip()
    expires_in = int(data.get("expires_in") or 0)
    if not access_token or expires_in <= 0:
        raise RuntimeError("MS token refresh returned invalid payload.")
    return access_token, expires_in


def _ensure_fresh_access_token_outlook(conn, account_row: Dict[str, Any]) -> str:
    enc_access = account_row["access_token_enc"]
    enc_refresh = account_row.get("refresh_token_enc")
    token_expires_at = account_row.get("token_expires_at")

    access = _decrypt_token(enc_access)

    must_refresh = token_expires_at is None
    if token_expires_at is not None:
        cur = conn.cursor()
        cur.execute("SELECT (NOW() >= %s::timestamptz) AS expired", (token_expires_at,))
        row = cur.fetchone()
        must_refresh = bool(row["expired"])

    if not must_refresh:
        return access

    if not enc_refresh:
        # No refresh token stored; try the access token anyway
        return access

    refresh = _decrypt_token(enc_refresh)
    new_access, expires_in = _ms_refresh_access_token(refresh)
    enc_new_access = _encrypt_token(new_access)

    cur = conn.cursor()
    cur.execute(
        """
        UPDATE email_accounts
        SET access_token_enc = %s,
            token_expires_at = NOW() + (%s || ' seconds')::interval,
            updated_at = NOW()
        WHERE id = %s AND user_id = %s
        """,
        (enc_new_access, str(expires_in), account_row["id"], account_row["user_id"]),
    )
    conn.commit()
    return new_access


def _graph_list_messages(access_token: str, *, url: str, top: int) -> List[dict]:
    params = {
        "$top": str(top),
        "$orderby": "receivedDateTime DESC",
        "$select": ",".join(
            [
                "id",
                "internetMessageId",
                "conversationId",
                "subject",
                "bodyPreview",
                "from",
                "sender",
                "toRecipients",
                "ccRecipients",
                "receivedDateTime",
                "sentDateTime",
            ]
        ),
    }

    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Graph API error {resp.status_code}: {resp.text[:300]}")
    data = resp.json() or {}
    return data.get("value") or []


def import_last_messages_outlook(
    conn,
    *,
    user_id: int,
    email_account_id: int,
    limit: int = 25,
) -> Dict[str, Any]:
    account = _fetch_account(conn, user_id, email_account_id)

    if account["provider"] != "outlook":
        raise RuntimeError("Only outlook provider is supported in this importer.")
    if not account.get("sync_enabled"):
        raise RuntimeError("Email account sync is disabled.")

    access_token = _ensure_fresh_access_token_outlook(conn, account)

    # Pull from both inbox and sent so the “I emailed them” test works.
    half = max(1, int(limit) // 2)
    inbox_msgs = _graph_list_messages(access_token, url=MS_GRAPH_INBOX, top=half)
    sent_msgs = _graph_list_messages(access_token, url=MS_GRAPH_SENT, top=int(limit) - half)
    msgs = inbox_msgs + sent_msgs

    imported = 0
    linked = 0

    primary = (account.get("primary_email") or "").strip().lower()

    for m in msgs:
        provider_message_id = (m.get("id") or "").strip()
        if not provider_message_id:
            continue

        subject = (m.get("subject") or "").strip() or None
        snippet = (m.get("bodyPreview") or "").strip() or None

        from_name, from_email = _extract_email_name(m.get("from"))
        # Fallback if "from" is missing
        if not from_email:
            from_name, from_email = _extract_email_name(m.get("sender"))

        to_emails = _extract_emails(m.get("toRecipients"))
        cc_emails = _extract_emails(m.get("ccRecipients"))

        sent_dt = _parse_graph_dt(m.get("sentDateTime"))
        recv_dt = _parse_graph_dt(m.get("receivedDateTime"))
        message_date = _format_message_date(sent_dt or recv_dt)

        provider_thread_id = (m.get("conversationId") or m.get("internetMessageId") or "").strip() or None

        direction = "unknown"
        if primary and from_email == primary:
            direction = "outbound"
        elif primary and (primary in to_emails or primary in cc_emails):
            direction = "inbound"

        row_payload = {
            "user_id": user_id,
            "email_account_id": email_account_id,
            "provider": "outlook",
            "provider_message_id": provider_message_id,
            "provider_thread_id": provider_thread_id,
            "message_date": message_date,
            "subject": subject,
            "from_name": from_name,
            "from_email": from_email,
            "to_emails": to_emails,
            "cc_emails": cc_emails,
            "snippet": snippet,
            "body_text": None,
            "body_html": None,
            "direction": direction,
        }

        email_message_id = _insert_email_message(conn, row_payload)
        if not email_message_id:
            continue

        imported += 1

        candidates: List[Tuple[str, str]] = []

        if from_email:
            candidates.append(("from", from_email))

        for e in to_emails:
            candidates.append(("to", e))

        for e in cc_emails:
            candidates.append(("cc", e))

        for match_type, email in candidates:
            cid = _contact_id_for_email(conn, user_id, email)
            if not cid:
                continue
            _insert_link(conn, user_id, email_message_id, cid, match_type, email)
            linked += 1

    conn.commit()

    return {
        "email_account_id": email_account_id,
        "requested": int(limit),
        "imported_messages": imported,
        "links_created": linked,
    }