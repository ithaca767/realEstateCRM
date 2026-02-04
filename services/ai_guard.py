import os
from dataclasses import dataclass
from datetime import date

from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


class AIGuardError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AIUsageSnapshot:
    daily_requests_used: int
    daily_request_limit: int
    monthly_spend_cents: int
    from typing import Optional
		monthly_cap_cents: Optional[int]


def _is_ai_globally_available() -> bool:
    raw = (os.getenv("AI_FEATURES_AVAILABLE") or "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _today_ny() -> date:
    # Using date.today() is fine since your server timezone is NY, but this is explicit.
    return date.today()


def _current_month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def ensure_ai_allowed_and_reset_if_needed(conn, user_id: int) -> AIUsageSnapshot:
    """
    Canon behavior:
    - Enforce global flag
    - Enforce user opt-in
    - Reset daily counter when last reset != today
    - Reset monthly spend when last reset month != current month
    - Enforce daily request limit and monthly cap
    """
    if not _is_ai_globally_available():
        raise AIGuardError("ai_globally_disabled", "AI features are currently disabled.")

    cur = conn.cursor()

    # Lock row to avoid race conditions on counters
    cur.execute(
        """
        SELECT
            ai_enabled,
            ai_daily_request_limit,
            ai_daily_requests_used,
            ai_last_daily_reset_at,
            ai_monthly_cap_cents,
            ai_monthly_spend_cents,
            ai_last_monthly_reset_at
        FROM users
        WHERE id = %s
        FOR UPDATE
        """,
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        raise AIGuardError("invalid_request", "User not found.")

    ai_enabled = bool(row["ai_enabled"])
    if not ai_enabled:
        raise AIGuardError("ai_not_enabled", "AI is not enabled for this account.")

    daily_limit = int(row["ai_daily_request_limit"] or 0)
    daily_used = int(row["ai_daily_requests_used"] or 0)
    last_daily_reset = row["ai_last_daily_reset_at"]  # may be None

    monthly_cap = row["ai_monthly_cap_cents"]  # may be None
    monthly_spend = int(row["ai_monthly_spend_cents"] or 0)
    last_monthly_reset = row["ai_last_monthly_reset_at"]  # may be None

    today = _today_ny()

    # Daily reset
    if last_daily_reset is None or last_daily_reset != today:
        daily_used = 0
        cur.execute(
            """
            UPDATE users
            SET ai_daily_requests_used = 0,
                ai_last_daily_reset_at = %s
            WHERE id = %s
            """,
            (today, user_id),
        )

    # Monthly reset (compare month keys)
    current_month = _current_month_key(today)
    last_month = _current_month_key(last_monthly_reset) if last_monthly_reset else None

    if last_month is None or last_month != current_month:
        monthly_spend = 0
        cur.execute(
            """
            UPDATE users
            SET ai_monthly_spend_cents = 0,
                ai_last_monthly_reset_at = %s
            WHERE id = %s
            """,
            (today, user_id),
        )

    # Enforce daily limit (0 means disallowed)
    if daily_limit <= 0:
        raise AIGuardError("ai_daily_limit_reached", "AI usage is not available because the daily request limit is set to 0.")

    if daily_used >= daily_limit:
        raise AIGuardError("ai_daily_limit_reached", "Daily AI request limit reached.")

    # Enforce monthly cap if set
    if monthly_cap is not None:
        monthly_cap = int(monthly_cap)
        if monthly_spend >= monthly_cap:
            raise AIGuardError("ai_monthly_cap_reached", "Monthly AI spend cap reached.")

    return AIUsageSnapshot(
        daily_requests_used=daily_used,
        daily_request_limit=daily_limit,
        monthly_spend_cents=monthly_spend,
        monthly_cap_cents=monthly_cap,
    )


def increment_ai_usage_on_success(conn, user_id: int, add_spend_cents: int = 0) -> None:
    """
    Increment counters only after success.
    Caller must be inside a transaction and should have already locked the row via guard call.
    """
    if add_spend_cents < 0:
        add_spend_cents = 0

    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users
        SET ai_daily_requests_used = ai_daily_requests_used + 1,
            ai_monthly_spend_cents = ai_monthly_spend_cents + %s
        WHERE id = %s
        """,
        (add_spend_cents, user_id),
    )
