"""
Provider-neutral Calendar adapter for Ulysses Activities.

The Activity Engine determines CRM semantics and tenant-scoped source data.
This module only adapts calendar-eligible Activities for calendar consumers.
"""

from datetime import date, datetime
from typing import Any, Dict, List

from activity_engine import list_activities, require_aware_datetime


def calendar_uid(activity: Dict[str, Any]) -> str:
    """
    Return a stable calendar UID derived only from Activity source identity.
    """
    activity_key = (activity.get("activity_key") or "").strip()
    if not activity_key or ":" not in activity_key:
        raise ValueError("activity_key is required")

    source_type, source_id = activity_key.split(":", 1)

    if not source_type or not source_id:
        raise ValueError("invalid activity_key")

    return f"ulysses-{source_type}-{source_id}@ulyssescrm"


def calendar_item(
    activity: Dict[str, Any],
    *,
    now: datetime,
) -> Dict[str, Any]:
    """
    Adapt one calendar-eligible Activity into provider-neutral calendar data.

    Timestamp Activities remain timed instants expressed in the timezone
    carried by ``now``.

    Date-only Activities remain true all-day calendar dates. No synthetic
    midnight or default appointment time is introduced.
    """
    now_local = require_aware_datetime(now)
    local_tz = now_local.tzinfo

    if not activity.get("calendar_eligible"):
        raise ValueError("Activity is not calendar eligible")

    due_at = activity.get("due_at")
    due_date = activity.get("due_date")

    if due_at is not None and due_date is not None:
        raise ValueError("Activity cannot have both due_at and due_date")

    base = {
        "activity_key": activity["activity_key"],
        "uid": calendar_uid(activity),
        "title": (activity.get("title") or "").strip(),
        "description": (activity.get("description") or "").strip(),
        "target_url": activity.get("target_url"),
    }

    if due_at is not None:
        start_at = require_aware_datetime(due_at).astimezone(local_tz)

        return {
            **base,
            "event_kind": "timed",
            "start_at": start_at,
            "start_date": None,
        }

    if due_date is not None:
        if not isinstance(due_date, date) or isinstance(due_date, datetime):
            raise TypeError("Activity due_date must be a date")

        return {
            **base,
            "event_kind": "all_day",
            "start_at": None,
            "start_date": due_date,
        }

    raise ValueError("Calendar Activity must have due_at or due_date")


def list_calendar_items(
    conn,
    user_id: int,
    *,
    now: datetime,
) -> List[Dict[str, Any]]:
    """
    Return calendar-eligible Activities for exactly one supplied user.

    Tenant identity must already have been resolved before this function is
    called. This adapter does not infer or override user identity.
    """
    if not user_id:
        raise ValueError("user_id is required")

    now = require_aware_datetime(now)

    activities = list_activities(
        conn,
        user_id,
        now=now,
    )

    return [
        calendar_item(activity, now=now)
        for activity in activities
        if activity.get("calendar_eligible")
    ]
