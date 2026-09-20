"""
Ulysses Activity Engine.

Read-only normalization layer for actionable CRM records.

Source records remain authoritative. This module does not create or maintain
a separate Activity database.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo


NY = ZoneInfo("America/New_York")

ACTIVITY_TYPE_FOLLOWUP = "followup"
ACTIVITY_TYPE_TASK = "task"
ACTIVITY_TYPE_TRANSACTION_DEADLINE = "transaction_deadline"

VALID_ACTIVITY_TYPES = {
    ACTIVITY_TYPE_FOLLOWUP,
    ACTIVITY_TYPE_TASK,
    ACTIVITY_TYPE_TRANSACTION_DEADLINE,
}


def require_aware_datetime(value: datetime) -> datetime:
    """Require a timezone-aware datetime."""
    if not isinstance(value, datetime):
        raise TypeError("value must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("value must be timezone-aware")
    return value


def to_new_york(value: datetime) -> datetime:
    """Convert an aware instant to America/New_York."""
    return require_aware_datetime(value).astimezone(NY)


def activity_key(source_type: str, source_id: int) -> str:
    """
    Return stable Ulysses identity for a normalized Activity.

    This identifies the source record. It does not replace the source record.
    """
    source_type = (source_type or "").strip()

    if source_type not in VALID_ACTIVITY_TYPES:
        raise ValueError("invalid activity source type")

    if not isinstance(source_id, int) or source_id <= 0:
        raise ValueError("source_id must be a positive integer")

    return f"{source_type}:{source_id}"


def classify_due(
    *,
    due_at: Optional[datetime] = None,
    due_date: Optional[date] = None,
    now: datetime,
) -> Dict[str, bool]:
    """
    Classify an incomplete Activity relative to America/New_York.

    Timestamp semantics:
      - earlier than now -> overdue
      - today and now-or-later -> today
      - after today -> upcoming

    Date-only semantics:
      - before today's NY date -> overdue
      - today's NY date -> today
      - after today's NY date -> upcoming

    Exactly one of due_at or due_date may be supplied.
    """
    now_ny = to_new_york(now)

    if due_at is not None and due_date is not None:
        raise ValueError("provide due_at or due_date, not both")

    if due_at is None and due_date is None:
        return {
            "is_overdue": False,
            "is_today": False,
            "is_upcoming": False,
        }

    if due_at is not None:
        due_ny = to_new_york(due_at)

        if due_ny < now_ny:
            return {
                "is_overdue": True,
                "is_today": False,
                "is_upcoming": False,
            }

        if due_ny.date() == now_ny.date():
            return {
                "is_overdue": False,
                "is_today": True,
                "is_upcoming": False,
            }

        return {
            "is_overdue": False,
            "is_today": False,
            "is_upcoming": True,
        }

    if not isinstance(due_date, date) or isinstance(due_date, datetime):
        raise TypeError("due_date must be a date")

    today_ny = now_ny.date()

    if due_date < today_ny:
        return {
            "is_overdue": True,
            "is_today": False,
            "is_upcoming": False,
        }

    if due_date == today_ny:
        return {
            "is_overdue": False,
            "is_today": True,
            "is_upcoming": False,
        }

    return {
        "is_overdue": False,
        "is_today": False,
        "is_upcoming": True,
    }


def make_activity(
    *,
    activity_type: str,
    source_id: int,
    title: str,
    now: datetime,
    description: Optional[str] = None,
    contact_id: Optional[int] = None,
    contact_name: Optional[str] = None,
    transaction_id: Optional[int] = None,
    due_date: Optional[date] = None,
    due_at: Optional[datetime] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    calendar_eligible: bool = False,
    target_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Build one normalized Activity result."""
    key = activity_key(activity_type, source_id)
    classification = classify_due(
        due_at=due_at,
        due_date=due_date,
        now=now,
    )

    return {
        "activity_key": key,
        "activity_type": activity_type,
        "source_type": activity_type,
        "source_id": source_id,
        "title": (title or "").strip(),
        "description": (description or "").strip(),
        "contact_id": contact_id,
        "contact_name": contact_name,
        "transaction_id": transaction_id,
        "due_date": due_date,
        "due_at": due_at,
        "status": status,
        "priority": priority,
        "is_overdue": classification["is_overdue"],
        "is_today": classification["is_today"],
        "is_upcoming": classification["is_upcoming"],
        "calendar_eligible": bool(calendar_eligible),
        "target_url": target_url,
    }


def list_followup_activities(conn, user_id: int, *, now: datetime):
    """
    Return normalized open engagement Follow-ups for one user.

    Source-of-truth rules:
      - child engagement
      - requires_follow_up = TRUE
      - follow_up_completed = FALSE
      - follow_up_due_at IS NOT NULL
      - contact belongs to the same user
      - contact is not archived

    Read-only. No database writes.
    """
    if not user_id:
        raise ValueError("user_id is required")

    now = require_aware_datetime(now)

    from psycopg2.extras import RealDictCursor

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                e.id AS source_id,
                e.contact_id,
                e.follow_up_due_at AS due_at,
                e.outcome,
                e.summary_clean,
                e.notes,
                e.engagement_type,
                p.outcome AS parent_outcome,
                p.summary_clean AS parent_summary_clean,
                p.notes AS parent_notes,
                p.engagement_type AS parent_engagement_type,
                COALESCE(
                    NULLIF(TRIM(CONCAT_WS(' ', c.first_name, c.last_name)), ''),
                    NULLIF(TRIM(c.name), ''),
                    '(Unnamed contact)'
                ) AS contact_name
            FROM engagements e
            JOIN contacts c
              ON c.id = e.contact_id
             AND c.user_id = e.user_id
            LEFT JOIN engagements p
              ON p.id = e.parent_engagement_id
             AND p.user_id = e.user_id
            WHERE e.user_id = %s
              AND c.archived_at IS NULL
              AND e.parent_engagement_id IS NOT NULL
              AND e.requires_follow_up = TRUE
              AND e.follow_up_completed = FALSE
              AND e.follow_up_due_at IS NOT NULL
            ORDER BY e.follow_up_due_at ASC, e.id ASC
            """,
            (user_id,),
        )
        rows = cur.fetchall() or []

    activities = []

    for row in rows:
        row = dict(row)

        description = _first_text(
            row.get("outcome"),
            row.get("summary_clean"),
            row.get("notes"),
            row.get("engagement_type"),
            row.get("parent_outcome"),
            row.get("parent_summary_clean"),
            row.get("parent_notes"),
            row.get("parent_engagement_type"),
        )

        contact_name = row.get("contact_name") or "(Unnamed contact)"

        activities.append(
            make_activity(
                activity_type=ACTIVITY_TYPE_FOLLOWUP,
                source_id=row["source_id"],
                title=f"Follow up with {contact_name}",
                description=description,
                contact_id=row.get("contact_id"),
                contact_name=contact_name,
                due_at=row.get("due_at"),
                now=now,
                status="open",
                calendar_eligible=True,
                target_url=f"/engagements/{row['source_id']}/edit",
            )
        )

    return activities


def _clean_text(value: Any, max_len: int = 180) -> str:
    value = (value or "").strip()

    if not value:
        return ""

    value = " ".join(value.split())

    if len(value) <= max_len:
        return value

    return value[:max_len] + "…"


def _first_text(*values: Any) -> str:
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned

    return ""


def list_task_activities(conn, user_id: int, *, now: datetime):
    """
    Return normalized actionable Tasks for one user.

    Source-of-truth rules:
      - completed and canceled tasks are excluded
      - future snoozed tasks are excluded
      - expired snoozed tasks become actionable again
      - only tasks with due_at or due_date are Activities in V1

    Read-only. No database writes.
    """
    if not user_id:
        raise ValueError("user_id is required")

    now = require_aware_datetime(now)

    from psycopg2.extras import RealDictCursor

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                t.id AS source_id,
                t.contact_id,
                t.transaction_id,
                t.engagement_id,
                t.title,
                t.description,
                t.task_type,
                t.status,
                t.priority,
                t.due_date,
                t.due_at,
                t.snoozed_until,
                COALESCE(
                    NULLIF(TRIM(CONCAT_WS(' ', c.first_name, c.last_name)), ''),
                    NULLIF(TRIM(c.name), ''),
                    '(Unnamed contact)'
                ) AS contact_name
            FROM tasks t
            LEFT JOIN contacts c
              ON c.id = t.contact_id
             AND c.user_id = t.user_id
            WHERE t.user_id = %s
              AND t.status NOT IN ('completed', 'canceled')
              AND (
                    t.status <> 'snoozed'
                    OR t.snoozed_until IS NULL
                    OR t.snoozed_until <= %s
              )
              AND (t.due_at IS NOT NULL OR t.due_date IS NOT NULL)
            ORDER BY
                COALESCE(
                    t.due_at,
                    t.due_date::timestamp AT TIME ZONE 'America/New_York'
                ) ASC,
                t.id ASC
            """,
            (user_id, now),
        )
        rows = cur.fetchall() or []

    activities = []

    for row in rows:
        row = dict(row)

        due_at = row.get("due_at")
        due_date = row.get("due_date")

        # Preserve date-only semantics. A date-only Task is not silently
        # converted into a midnight timestamp.
        if due_at is not None:
            normalized_due_at = due_at
            normalized_due_date = None
        else:
            normalized_due_at = None
            normalized_due_date = due_date

        contact_name = row.get("contact_name")

        activities.append(
            make_activity(
                activity_type=ACTIVITY_TYPE_TASK,
                source_id=row["source_id"],
                title=row.get("title") or "Task",
                description=_clean_text(row.get("description")),
                contact_id=row.get("contact_id"),
                contact_name=contact_name,
                transaction_id=row.get("transaction_id"),
                due_date=normalized_due_date,
                due_at=normalized_due_at,
                now=now,
                status=row.get("status"),
                priority=row.get("priority"),
                calendar_eligible=False,
                target_url=f"/tasks/{row['source_id']}",
            )
        )

    return activities


def list_transaction_deadline_activities(conn, user_id: int, *, now: datetime):
    """
    Return normalized open Transaction Deadlines for one user.

    Source-of-truth rules:
      - deadline belongs to the user
      - deadline is not done
      - due_date is assigned

    Transaction Deadlines are date-only in V1. They are not silently
    converted into timestamp instants.

    Read-only. No database writes.
    """
    if not user_id:
        raise ValueError("user_id is required")

    now = require_aware_datetime(now)

    from psycopg2.extras import RealDictCursor

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                d.id AS source_id,
                d.transaction_id,
                d.name,
                d.due_date,
                d.notes,
                t.contact_id,
                COALESCE(
                    NULLIF(TRIM(CONCAT_WS(' ', c.first_name, c.last_name)), ''),
                    NULLIF(TRIM(c.name), ''),
                    '(Unnamed contact)'
                ) AS contact_name
            FROM transaction_deadlines d
            JOIN transactions t
              ON t.id = d.transaction_id
             AND t.user_id = d.user_id
            LEFT JOIN contacts c
              ON c.id = t.contact_id
             AND c.user_id = d.user_id
            WHERE d.user_id = %s
              AND d.is_done = FALSE
              AND d.due_date IS NOT NULL
            ORDER BY d.due_date ASC, d.id ASC
            """,
            (user_id,),
        )
        rows = cur.fetchall() or []

    activities = []

    for row in rows:
        row = dict(row)

        activities.append(
            make_activity(
                activity_type=ACTIVITY_TYPE_TRANSACTION_DEADLINE,
                source_id=row["source_id"],
                title=row.get("name") or "Transaction deadline",
                description=_clean_text(row.get("notes")),
                contact_id=row.get("contact_id"),
                contact_name=row.get("contact_name"),
                transaction_id=row.get("transaction_id"),
                due_date=row.get("due_date"),
                now=now,
                status="open",
                calendar_eligible=True,
                target_url=f"/transactions/{row['transaction_id']}/edit",
            )
        )

    return activities


def _activity_sort_key(activity: Dict[str, Any]):
    """
    Return a deterministic sort key without changing Activity due semantics.

    Timestamp Activities sort by their New York instant.
    Date-only Activities sort at the beginning of their New York calendar day
    for ordering purposes only. Their stored due_date remains date-only.
    """
    due_at = activity.get("due_at")
    due_date = activity.get("due_date")

    if due_at is not None:
        sortable_due = to_new_york(due_at)
    elif due_date is not None:
        if not isinstance(due_date, date) or isinstance(due_date, datetime):
            raise TypeError("Activity due_date must be a date")

        sortable_due = datetime(
            due_date.year,
            due_date.month,
            due_date.day,
            0,
            0,
            tzinfo=NY,
        )
    else:
        sortable_due = datetime.max.replace(tzinfo=NY)

    return (
        sortable_due,
        activity.get("activity_type") or "",
        activity.get("source_id") or 0,
    )


def list_activities(conn, user_id: int, *, now: datetime):
    """
    Return the unified Ulysses Activity List for one user.

    V1 sources:
      - engagement Follow-ups
      - Tasks
      - Transaction Deadlines

    Source records remain authoritative. Results are normalized, de-duplicated
    by stable source identity, and sorted deterministically.

    Read-only. No database writes.
    """
    if not user_id:
        raise ValueError("user_id is required")

    now = require_aware_datetime(now)

    combined = []

    combined.extend(
        list_followup_activities(
            conn,
            user_id,
            now=now,
        )
    )

    combined.extend(
        list_task_activities(
            conn,
            user_id,
            now=now,
        )
    )

    combined.extend(
        list_transaction_deadline_activities(
            conn,
            user_id,
            now=now,
        )
    )

    deduped = {}
    for activity in combined:
        key = activity["activity_key"]

        if key not in deduped:
            deduped[key] = activity

    return sorted(
        deduped.values(),
        key=_activity_sort_key,
    )


def list_dashboard_activities(conn, user_id: int, *, now: datetime):
    """
    Return Activity Engine records eligible for the Dashboard snapshot.

    Dashboard V1 shows:
      - overdue Activities
      - Activities due today

    Future/upcoming Activities remain available through list_activities()
    but are not part of Today's Snapshot.

    Read-only. No database writes.
    """
    now = require_aware_datetime(now)

    activities = list_activities(
        conn,
        user_id,
        now=now,
    )

    return [
        activity
        for activity in activities
        if activity.get("is_overdue") or activity.get("is_today")
    ]


def dashboard_snapshot_item(activity: Dict[str, Any], *, now: datetime):
    """
    Adapt one normalized Activity into the existing Dashboard snapshot contract.

    This compatibility layer lets the Dashboard move to Activity Engine data
    without requiring an unrelated visual redesign.
    """
    now_ny = to_new_york(now)

    due_at = activity.get("due_at")
    due_date = activity.get("due_date")

    if due_at is not None:
        due_ny = to_new_york(due_at)
        due_day = due_ny.date()
    elif due_date is not None:
        due_ny = None
        due_day = due_date
    else:
        due_ny = None
        due_day = None

    if activity.get("is_overdue") and due_day is not None:
        overdue_days = max(0, (now_ny.date() - due_day).days)
        snap_status = "overdue"
    else:
        overdue_days = 0
        snap_status = "today"

    item = dict(activity)

    item["item_type"] = activity["activity_type"]
    item["snap_status"] = snap_status
    item["overdue_days"] = overdue_days
    item["snippet"] = activity.get("description") or ""

    if activity["activity_type"] == ACTIVITY_TYPE_FOLLOWUP:
        item["engagement_id"] = activity["source_id"]
        item["follow_up_due_at"] = due_at

    elif activity["activity_type"] == ACTIVITY_TYPE_TASK:
        item["task_id"] = activity["source_id"]

        # Preserve the old Dashboard field name for timestamp Tasks.
        # Date-only Tasks remain date-only and are not given a fake timestamp.
        item["due_ts"] = due_at

    elif activity["activity_type"] == ACTIVITY_TYPE_TRANSACTION_DEADLINE:
        item["deadline_id"] = activity["source_id"]

    return item


def list_dashboard_snapshot_items(conn, user_id: int, *, now: datetime):
    """
    Return Dashboard-compatible snapshot records sourced entirely from
    the unified Activity Engine.
    """
    activities = list_dashboard_activities(
        conn,
        user_id,
        now=now,
    )

    return [
        dashboard_snapshot_item(activity, now=now)
        for activity in activities
    ]
