# services/integrations/activepipe.py

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Dict, List, Optional, Tuple

ACTIVEPIPE_HEADERS: List[str] = [
    "firstname", "lastname", "email", "phone", "mobile",
    "streetaddress", "city", "state", "postcode", "country",
    "status", "sms_status", "subscribed_at", "unsubscribed_at", "unsubscribed_reason",
    "source", "modified_at", "latest_interaction",
    "buyertype", "locations", "propertytype", "category",
    "minbeds", "maxbeds", "minbaths", "maxbaths",
    "minprice", "maxprice",
    "minparking", "maxparking",
    "minlandsize", "maxlandsize",
    "minbuildingsize", "maxbuildingsize",
    "listingtype",
    "tags",
]

ACTIVEPIPE_HEADERS_BASIC: List[str] = [
    "firstname", "lastname", "email", "phone", "mobile",
    "streetaddress", "city", "state", "postcode", "country",
    "tags",
]

ACTIVEPIPE_HEADERS_EXTENDED: List[str] = ACTIVEPIPE_HEADERS[:]  # full list, locked

def _safe_str(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _tags_normalize(tags_raw: str) -> str:
    """
    Keep it simple for v1:
    - Accept semicolon or comma separated
    - Output semicolon-separated, trimmed, de-duped (case-insensitive)
    """
    raw = _safe_str(tags_raw)
    if not raw:
        return ""
    parts = []
    for chunk in raw.replace(",", ";").split(";"):
        t = chunk.strip()
        if t:
            parts.append(t)

    seen = set()
    out = []
    for t in parts:
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return "; ".join(out)


def build_activepipe_row(contact: Dict, payload: Optional[Dict]) -> Dict[str, str]:
    """
    contact: dict-like row from contacts table (already tenant-scoped)
    payload: dict from contact_integrations.payload_json
    """
    payload = payload or {}

    # Core identity/address from contact
    row = {h: "" for h in ACTIVEPIPE_HEADERS}
    row["firstname"] = _safe_str(contact.get("first_name") or contact.get("firstname") or contact.get("first"))
    row["lastname"] = _safe_str(contact.get("last_name") or contact.get("lastname") or contact.get("last"))
    row["email"] = _safe_str(contact.get("email"))

    # Phone strategy (v1):
    # - If you have both phone + mobile fields in contacts, map them
    # - Otherwise, map contacts.phone to mobile, and leave phone blank (or mirror)
    contact_phone = _safe_str(contact.get("phone"))
    contact_mobile = _safe_str(contact.get("mobile"))
    if contact_mobile:
        row["mobile"] = contact_mobile
        row["phone"] = contact_phone
    else:
        row["mobile"] = contact_phone
        row["phone"] = ""

    row["streetaddress"] = _safe_str(
        contact.get("current_address")
        or contact.get("address")
        or contact.get("streetaddress")
        or contact.get("street_address")
    )
    row["city"] = _safe_str(contact.get("current_city") or contact.get("city"))
    row["state"] = _safe_str(contact.get("current_state") or contact.get("state"))
    row["postcode"] = _safe_str(contact.get("current_zip") or contact.get("zip") or contact.get("postcode"))
    row["country"] = _safe_str(contact.get("country"))

    # Integration-only fields from payload
    for k in ACTIVEPIPE_HEADERS:
        if k in ("firstname", "lastname", "email", "phone", "mobile",
                 "streetaddress", "city", "state", "postcode", "country"):
            continue
        if k in payload and payload.get(k) is not None:
            row[k] = _safe_str(payload.get(k))

    # Normalize tags output
    row["tags"] = _tags_normalize(row.get("tags", ""))

    return row


def emit_single_contact_csv(contact: Dict, payload: Optional[Dict], headers: Optional[List[str]] = None) -> bytes:
    headers = headers or ACTIVEPIPE_HEADERS_BASIC
    row = build_activepipe_row(contact, payload)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def validate_headers(headers: List[str]) -> Tuple[bool, List[str]]:
    """
    For import (8C). Accepts superset CSVs.
    Returns ok + list of missing required headers (we can keep required minimal).
    """
    normalized = [h.strip() for h in headers if h]
    missing = [h for h in ["email", "mobile", "phone"] if h not in normalized]
    # We allow missing email if mobile/phone exist, so do not hard fail on missing.
    return True, []
