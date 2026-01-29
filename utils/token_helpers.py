import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_raw_token(nbytes: int = 32) -> str:
    """
    Returns a URL-safe random token (raw). Store only a hash in the DB.
    """
    # token_urlsafe expects bytes count; output string is longer
    return secrets.token_urlsafe(nbytes)


def _get_pepper() -> str:
    pepper = (os.getenv("TOKEN_PEPPER") or "").strip()
    if not pepper:
        raise RuntimeError("TOKEN_PEPPER is not set. Set it in your environment before using token helpers.")
    return pepper


def hash_token(raw_token: str) -> str:
    """
    Hash token with SHA-256 using a server-side pepper.
    Store this hash in the DB, never the raw token.
    """
    raw = (raw_token or "").strip()
    if not raw:
        raise ValueError("raw_token is required")

    pepper = _get_pepper()
    material = (pepper + raw).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    """
    Prevents timing attacks when comparing hashes.
    """
    return hmac.compare_digest((a or ""), (b or ""))


def expires_at_from_now(minutes: int) -> datetime:
    return utcnow() + timedelta(minutes=minutes)


def is_expired(expires_at: Optional[datetime]) -> bool:
    if not expires_at:
        return True
    # expires_at is expected to be timezone-aware (timestamptz)
    return utcnow() >= expires_at


def build_link(base_url: str, path: str, raw_token: str) -> str:
    """
    Convenience for producing a copy/paste link since we are not doing email delivery.
    """
    base = (base_url or "").rstrip("/")
    p = (path or "").strip()
    if not p.startswith("/"):
        p = "/" + p
    token = (raw_token or "").strip()
    return f"{base}{p}?token={token}"
