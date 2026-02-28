# services/email_sync/gmail_importer.py
# Phase 10C: Gmail importer v1 (manual pull, snippet + headers, contact auto-link)

from __future__ import annotations

import json
import os
import time
from email.utils import getaddresses, parseaddr
from typing import Any, Dict, List, Optional, Tuple

import requests
from cryptography.fernet import Fernet


GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"


def _require_env(name: str) -> str:
    v = (os.getenv(name) or "").strip()
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def _get_fernet() -> Fernet:
    key = _require_env("EMAIL_TOKEN_ENCRYPTION_KEY")
    return Fernet(key.encode("utf-8"))


def _decrypt_token(token_ciphertext: str) -> str:
    f = _get_fernet()
    return f.decrypt(token_ciphertext.encode("utf-8")).decode("utf-8")


def _encrypt_token(token_plain: str) -> str:
    f = _get_fernet()
    return f.encrypt(token_plain.encode("utf-8")).decode("utf-8")


def _parse_email_list(header_value: Optional[str]) -> List[str]:
    if not header_value:
        return []
    addrs = getaddresses([header_value])
    emails: List[str] = []
    for _, addr in addrs:
        addr = (addr or "").strip().lower()
        if addr:
            emails.append(addr)

    seen = set()
    out: List[str] = []
    for e in emails:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def _parse_from(header_value: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not header_value:
        return (None, None)
    name, addr = parseaddr(header_value)
    name = (name or "").strip() or None
    addr = (addr or "").strip().lower() or None
    return (name, addr)


def _direction_from_labels(label_ids: List[str]) -> str:
    s = set(label_ids or [])
    if "SENT" in s:
        return "outbound"
    if "INBOX" in s:
        return "inbound"
    return "unknown"


def _safe_get_header(headers: List[Dict[str, Any]], name: str) -> Optional[str]:
    target = name.lower()
    for h in headers or []:
        if (h.get("name") or "").lower() == target:
            return h.get("value")
    return None


def _gmail_get(
    access_token: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    url = f"{GMAIL_API_BASE}{path}"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params=params or {},
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Gmail API error {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _gmail_refresh_access_token(refresh_token: str) -> Tuple[str, int]:
    client_id = _require_env("GMAIL_OAUTH_CLIENT_ID")
    client_secret = _require_env("GMAIL_OAUTH_CLIENT_SECRET")

    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Token refresh failed {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    access_token = (data.get("access_token") or "").strip()
    expires_in = int(data.get("expires_in") or 0)
    if not access_token or expires_in <= 0:
        raise RuntimeError("Token refresh returned invalid payload.")
    return access_token, expires_in


def _ensure_fresh_access_token(conn, account_row: Dict[str, Any]) -> str:
    enc_access = account_row["access_token_enc"]
    enc_refresh = account_row["refresh_token_enc"]
    token_expires_at = account_row.get("token_expires_at")

    access = _decrypt_token(enc_access)
    refresh = _decrypt_token(enc_refresh)

    must_refresh = token_expires_at is None

    if token_expires_at is not None:
        cur = conn.cursor()
        cur.execute("SELECT (NOW() >= %s::timestamptz) AS expired", (token_expires_at,))
        row = cur.fetchone()
        must_refresh = bool(row["expired"])
        
    if not must_refresh:
        return access

    new_access, expires_in = _gmail_refresh_access_token(refresh)
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


def _fetch_account(conn, user_id: int, email_account_id: int) -> Dict[str, Any]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, user_id, provider, primary_email, sync_enabled,
               access_token_enc, refresh_token_enc, token_expires_at
        FROM email_accounts
        WHERE id = %s AND user_id = %s
        """,
        (email_account_id, user_id),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError("Email account not found.")
    return dict(row)


def _insert_email_message(conn, payload: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO email_messages (
          user_id, email_account_id,
          provider, provider_message_id, provider_thread_id,
          message_date, subject, from_name, from_email,
          to_emails, cc_emails, snippet,
          body_text, body_html,
          direction, created_at
        )
        VALUES (
          %(user_id)s, %(email_account_id)s,
          %(provider)s, %(provider_message_id)s, %(provider_thread_id)s,
          %(message_date)s, %(subject)s, %(from_name)s, %(from_email)s,
          %(to_emails)s::jsonb, %(cc_emails)s::jsonb, %(snippet)s,
          %(body_text)s, %(body_html)s,
          %(direction)s, NOW()
        )
        ON CONFLICT (user_id, email_account_id, provider, provider_message_id)
        DO NOTHING
        RETURNING id
        """,
        {
            **payload,
            "to_emails": json.dumps(payload.get("to_emails") or []),
            "cc_emails": json.dumps(payload.get("cc_emails") or []),
        },
    )

    row = cur.fetchone()
    if row and row.get("id"):
        return int(row["id"])

    cur.execute(
        """
        SELECT id
        FROM email_messages
        WHERE user_id = %s
          AND email_account_id = %s
          AND provider = %s
          AND provider_message_id = %s
        """,
        (
            payload["user_id"],
            payload["email_account_id"],
            payload["provider"],
            payload["provider_message_id"],
        ),
    )
    existing = cur.fetchone()
    if existing and existing.get("id"):
        return int(existing["id"])
    return None


def _contact_id_for_email(conn, user_id: int, email: str) -> Optional[int]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT contact_id
        FROM contact_emails
        WHERE user_id = %s AND lower(email) = lower(%s)
        LIMIT 1
        """,
        (user_id, email),
    )
    row = cur.fetchone()
    if row and row.get("contact_id"):
        return int(row["contact_id"])
    return None


def _insert_link(
    conn,
    user_id: int,
    email_message_id: int,
    contact_id: int,
    match_type: str,
    matched_email: Optional[str],
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO email_message_links (
          user_id, email_message_id, contact_id,
          match_type, matched_email, created_at
        )
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (user_id, email_message_id, contact_id, match_type)
        DO NOTHING
        """,
        (user_id, email_message_id, contact_id, match_type, matched_email),
    )


def import_last_messages_gmail(
    conn,
    *,
    user_id: int,
    email_account_id: int,
    limit: int = 25,
) -> Dict[str, Any]:

    account = _fetch_account(conn, user_id, email_account_id)

    if account["provider"] != "gmail":
        raise RuntimeError("Only gmail provider is supported in Phase 10C.")
    if not account.get("sync_enabled"):
        raise RuntimeError("Email account sync is disabled.")

    access_token = _ensure_fresh_access_token(conn, account)

    listing = _gmail_get(
        access_token,
        "/users/me/messages",
        params={"maxResults": int(limit)},
    )

    msg_refs = listing.get("messages") or []
    imported = 0
    linked = 0

    for ref in msg_refs:
        mid = ref.get("id")
        if not mid:
            continue

        m = _gmail_get(
            access_token,
            f"/users/me/messages/{mid}",
            params={
                "format": "metadata",
                "metadataHeaders": ["Subject", "From", "To", "Cc", "Date"],
            },
        )

        payload = m.get("payload") or {}
        headers = payload.get("headers") or []
        label_ids = m.get("labelIds") or []

        subject = _safe_get_header(headers, "Subject")
        from_header = _safe_get_header(headers, "From")
        to_header = _safe_get_header(headers, "To")
        cc_header = _safe_get_header(headers, "Cc")

        internal_ms = int(m.get("internalDate") or 0)
        message_date = None
        if internal_ms > 0:
            message_date = time.strftime(
                "%Y-%m-%d %H:%M:%S%z",
                time.gmtime(internal_ms / 1000.0),
            )

        from_name, from_email = _parse_from(from_header)
        to_emails = _parse_email_list(to_header)
        cc_emails = _parse_email_list(cc_header)

        direction = _direction_from_labels(label_ids)

        primary = (account.get("primary_email") or "").strip().lower()
        if primary and from_email == primary:
            direction = "outbound"

        row_payload = {
            "user_id": user_id,
            "email_account_id": email_account_id,
            "provider": "gmail",
            "provider_message_id": str(m.get("id") or ""),
            "provider_thread_id": m.get("threadId"),
            "message_date": message_date,
            "subject": subject,
            "from_name": from_name,
            "from_email": from_email,
            "to_emails": to_emails,
            "cc_emails": cc_emails,
            "snippet": m.get("snippet"),
            "body_text": None,
            "body_html": None,
            "direction": direction or "unknown",
        }

        if not row_payload["provider_message_id"]:
            continue

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