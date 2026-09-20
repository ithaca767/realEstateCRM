"""
Standards-based ICS serialization for Ulysses Calendar items.

Pure serialization layer:
- no database access
- no tenant resolution
- no Flask/session dependency
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional


PRODID = "-//Ulysses CRM//EN"
TIMED_EVENT_MINUTES = 30


def ics_escape(value: Optional[str]) -> str:
    """Escape ICS TEXT values."""
    text = value or ""
    return (
        text.replace("\\", "\\\\")
        .replace("\r\n", "\\n")
        .replace("\r", "\\n")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _utc_dtstamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("dtstamp must be timezone-aware")

    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _serialize_event(
    item: Dict[str, Any],
    *,
    dtstamp: datetime,
) -> list[str]:
    uid = (item.get("uid") or "").strip()
    title = (item.get("title") or "").strip()
    description = (item.get("description") or "").strip()
    event_kind = item.get("event_kind")

    if not uid:
        raise ValueError("calendar item uid is required")

    lines = [
        "BEGIN:VEVENT",
        f"UID:{ics_escape(uid)}",
        f"DTSTAMP:{_utc_dtstamp(dtstamp)}",
        f"SUMMARY:{ics_escape(title)}",
    ]

    if description:
        lines.append(f"DESCRIPTION:{ics_escape(description)}")

    if event_kind == "timed":
        start_at = item.get("start_at")

        if not isinstance(start_at, datetime):
            raise TypeError("timed calendar item start_at must be a datetime")

        if start_at.tzinfo is None or start_at.utcoffset() is None:
            raise ValueError("timed calendar item start_at must be timezone-aware")

        tzid = getattr(start_at.tzinfo, "key", None)
        if not tzid:
            raise ValueError("timed calendar item requires a named timezone")

        end_at = start_at + timedelta(minutes=TIMED_EVENT_MINUTES)

        lines.append(
            f"DTSTART;TZID={tzid}:"
            f"{start_at.strftime('%Y%m%dT%H%M%S')}"
        )
        lines.append(
            f"DTEND;TZID={tzid}:"
            f"{end_at.strftime('%Y%m%dT%H%M%S')}"
        )

    elif event_kind == "all_day":
        start_date = item.get("start_date")

        if start_date is None:
            raise ValueError("all-day calendar item start_date is required")

        if isinstance(start_date, datetime):
            raise TypeError("all-day calendar item start_date must be a date")

        end_date = start_date + timedelta(days=1)

        lines.append(
            f"DTSTART;VALUE=DATE:{start_date.strftime('%Y%m%d')}"
        )
        lines.append(
            f"DTEND;VALUE=DATE:{end_date.strftime('%Y%m%d')}"
        )

    else:
        raise ValueError("invalid calendar event_kind")

    lines.append("STATUS:CONFIRMED")
    lines.append("END:VEVENT")

    return lines


def serialize_calendar(
    items: Iterable[Dict[str, Any]],
    *,
    dtstamp: datetime,
) -> str:
    """Serialize provider-neutral Calendar items as one VCALENDAR."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for item in items:
        lines.extend(
            _serialize_event(
                item,
                dtstamp=dtstamp,
            )
        )

    lines.append("END:VCALENDAR")

    return "\r\n".join(lines) + "\r\n"
