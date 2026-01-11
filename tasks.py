# tasks.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

TASK_STATUSES = ("open", "completed", "snoozed", "canceled")

TASK_SELECT = """
SELECT
  id,
  user_id,
  contact_id,
  transaction_id,
  engagement_id,
  professional_id,
  title,
  description,
  task_type,
  status,
  priority,
  due_date,
  due_at,
  snoozed_until,
  completed_at,
  canceled_at,
  created_at,
  updated_at
FROM tasks
"""


def list_tasks_for_user(cur, user_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    if status and status not in TASK_STATUSES:
        raise ValueError("Invalid status")

    if status:
        cur.execute(
            TASK_SELECT
            + """
            WHERE user_id = %s AND status = %s
            ORDER BY COALESCE(due_at, due_date::timestamptz, updated_at) ASC, id ASC
            """,
            (user_id, status),
        )
    else:
        cur.execute(
            TASK_SELECT
            + """
            WHERE user_id = %s
            ORDER BY COALESCE(due_at, due_date::timestamptz, updated_at) ASC, id ASC
            """,
            (user_id,),
        )

    rows = cur.fetchall() or []
    return [dict(r) for r in rows]


def get_task(cur, user_id: int, task_id: int) -> Optional[Dict[str, Any]]:
    cur.execute(
        TASK_SELECT + " WHERE user_id = %s AND id = %s",
        (user_id, task_id),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def create_task(cur, user_id: int, data: Dict[str, Any]) -> int:
    title = (data.get("title") or "").strip()
    if not title:
        raise ValueError("Title is required")

    status = data.get("status") or "open"
    if status not in TASK_STATUSES:
        raise ValueError("Invalid status")

    cur.execute(
        """
        INSERT INTO tasks (
          user_id, contact_id, transaction_id, engagement_id, professional_id,
          title, description, task_type, status, priority, due_date, due_at
        ) VALUES (
          %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id
        """,
        (
            user_id,
            data.get("contact_id"),
            data.get("transaction_id"),
            data.get("engagement_id"),
            data.get("professional_id"),
            title,
            data.get("description"),
            data.get("task_type"),
            status,
            data.get("priority"),
            data.get("due_date"),
            data.get("due_at"),
        ),
    )
    row = cur.fetchone()
    if not row or "id" not in row:
        raise RuntimeError("Insert failed: no id returned")
    return int(row["id"])


def update_task(cur, user_id: int, task_id: int, data: Dict[str, Any]) -> None:
    title = (data.get("title") or "").strip()
    if not title:
        raise ValueError("Title is required")

    status = data.get("status") or "open"
    if status not in TASK_STATUSES:
        raise ValueError("Invalid status")

    cur.execute(
        """
        UPDATE tasks
        SET
          contact_id = %s,
          transaction_id = %s,
          engagement_id = %s,
          professional_id = %s,
          title = %s,
          description = %s,
          task_type = %s,
          status = %s,
          priority = %s,
          due_date = %s,
          due_at = %s,
          updated_at = NOW()
        WHERE user_id = %s AND id = %s
        """,
        (
            data.get("contact_id"),
            data.get("transaction_id"),
            data.get("engagement_id"),
            data.get("professional_id"),
            title,
            data.get("description"),
            data.get("task_type"),
            status,
            data.get("priority"),
            data.get("due_date"),
            data.get("due_at"),
            user_id,
            task_id,
        ),
    )


def complete_task(cur, user_id: int, task_id: int) -> None:
    cur.execute(
        """
        UPDATE tasks
        SET status = 'completed', completed_at = NOW(), updated_at = NOW()
        WHERE user_id = %s AND id = %s
        """,
        (user_id, task_id),
    )


def snooze_task(cur, user_id: int, task_id: int, snoozed_until) -> None:
    cur.execute(
        """
        UPDATE tasks
        SET status = 'snoozed', snoozed_until = %s, updated_at = NOW()
        WHERE user_id = %s AND id = %s
        """,
        (snoozed_until, user_id, task_id),
    )


def reopen_task(cur, user_id: int, task_id: int) -> None:
    cur.execute(
        """
        UPDATE tasks
        SET status = 'open', snoozed_until = NULL, canceled_at = NULL, updated_at = NOW()
        WHERE user_id = %s AND id = %s
        """,
        (user_id, task_id),
    )


def cancel_task(cur, user_id: int, task_id: int) -> None:
    cur.execute(
        """
        UPDATE tasks
        SET status = 'canceled', canceled_at = NOW(), updated_at = NOW()
        WHERE user_id = %s AND id = %s
        """,
        (user_id, task_id),
    )

def delete_task(cur, user_id: int, task_id: int) -> bool:
    cur.execute(
        """
        DELETE FROM tasks
        WHERE user_id = %s AND id = %s
        """,
        (user_id, task_id),
    )
    return cur.rowcount == 1
