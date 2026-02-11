import os
import logging
import re
import secrets
import csv
import io

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from version import APP_VERSION
from functools import wraps
from datetime import date, datetime, timedelta, time, timezone
from math import ceil
from typing import Optional
from zoneinfo import ZoneInfo

from services.ai_prompts_v110 import SYSTEM_PROMPT_V110, INSTRUCTION_PROMPT_V110
from services.ai_parsers import parse_engagement_summary_output, AIParseError
from services.ai_guard import ensure_ai_allowed_and_reset_if_needed, increment_ai_usage_on_success, AIGuardError

from engagements import list_engagements_for_contact
from engagements import insert_engagement


NY = ZoneInfo("America/New_York")

def get_user_tz():
    # Phase 8: single timezone system-wide
    return NY

APP_ENV = os.getenv("APP_ENV", "LOCAL").upper()

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template,
    render_template_string,
    jsonify,
    Response,
    session,
    flash,
    abort,
)

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)

from tasks import (
    TASK_STATUSES,
    list_tasks_for_user,
    get_task,
    create_task,
    update_task,
    complete_task,
    snooze_task,
    reopen_task,
    cancel_task,
    delete_task,
)

from urllib.parse import urlparse, urljoin

from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

import psycopg2
from psycopg2.extras import RealDictCursor, DictCursor

app = Flask(__name__)

@app.template_filter("phone_display")
def phone_display_filter(v):
    return format_phone_display(v or "")

@app.context_processor
def inject_app_globals():
    return {
        "APP_VERSION": APP_VERSION,
        "APP_ENV": APP_ENV,
    }
    
@app.route("/api/ai/engagements/summarize", methods=["POST"])
@login_required
def api_ai_engagements_summarize():
    """
    Summarize an engagement transcript or notes using OpenAI.

    Canon rules:
      - user-initiated
      - no auto-save
      - guard enforced (global + per-user + limits)
      - returns structured output only
    """
    payload = request.get_json(silent=True) or {}

    engagement_id = payload.get("engagement_id")
    if engagement_id is not None:
        try:
            engagement_id = int(engagement_id)
        except Exception:
            return jsonify({
                "ok": False,
                "error": {
                    "code": "invalid_request",
                    "message": "engagement_id must be an integer."
                }
            }), 400

    transcript_override = (payload.get("transcript") or "").strip()

    # Must provide either engagement_id or transcript text
    if engagement_id is None and not transcript_override:
        return jsonify({
            "ok": False,
            "error": {
                "code": "invalid_request",
                "message": "Provide engagement_id or transcript."
            }
        }), 400

    conn = get_db()
    try:
        cur = conn.cursor()

        # Guard: global flag, per-user opt-in, resets, limits.
        # This SELECT uses FOR UPDATE internally, so keep this in the same transaction.
        usage = ensure_ai_allowed_and_reset_if_needed(conn, current_user.id)

        transcript_text = transcript_override
        contact_id = None

        if not transcript_text:
            # Fetch transcript from engagement with SQL-level ownership enforcement.
            cur.execute(
                """
                SELECT id, contact_id, transcript_raw, notes
                FROM engagements
                WHERE id = %s AND user_id = %s
                """,
                (engagement_id, current_user.id),
            )
            row = cur.fetchone()

            if not row:
                return jsonify({
                    "ok": False,
                    "error": {
                        "code": "not_found",
                        "message": "Engagement not found."
                    }
                }), 404

            contact_id = row.get("contact_id")

            transcript_text = (row.get("transcript_raw") or "").strip()
            if not transcript_text:
                transcript_text = (row.get("notes") or "").strip()

            if not transcript_text:
                return jsonify({
                    "ok": False,
                    "error": {
                        "code": "empty_transcript",
                        "message": "No transcript or notes found for this engagement."
                    }
                }), 400

        # Call OpenAI (import inside route to avoid boot-time dependency)
        try:
            from services.openai_client import call_summarize_model, OpenAIMissingDependencyError
        except Exception:
            # Extremely defensive: if import fails for any reason, treat as unavailable
            conn.rollback()
            return jsonify({
                "ok": False,
                "error": {
                    "code": "ai_unavailable",
                    "message": "AI is unavailable on this server."
                }
            }), 503

        try:
            raw_text = call_summarize_model(
                system_prompt=SYSTEM_PROMPT_V110,
                instruction_prompt=INSTRUCTION_PROMPT_V110,
                user_transcript=transcript_text,
            )
        except OpenAIMissingDependencyError:
            conn.rollback()
            return jsonify({
                "ok": False,
                "error": {
                    "code": "ai_dependency_missing",
                    "message": "AI is unavailable on this server."
                }
            }), 503

        # Parse into structured output
        parsed = parse_engagement_summary_output(raw_text)

        # Increment usage only on success (v1.1.0: count requests, no spend tracking)
        increment_ai_usage_on_success(conn, current_user.id, add_spend_cents=0)

        conn.commit()

        return jsonify({
            "ok": True,
            "data": {
                "engagement_id": engagement_id,
                "contact_id": contact_id,
                "one_sentence_summary": parsed["one_sentence_summary"],
                "crm_narrative_summary": parsed["crm_narrative_summary"],
                "suggested_follow_up_items": parsed["suggested_follow_up_items"],
                "usage": {
                    "daily_requests_used": usage.daily_requests_used + 1,
                    "daily_request_limit": usage.daily_request_limit,
                    "monthly_spend_cents": usage.monthly_spend_cents,
                    "monthly_cap_cents": usage.monthly_cap_cents,
                }
            }
        }), 200

    except AIGuardError as e:
        conn.rollback()
        return jsonify({
            "ok": False,
            "error": {
                "code": e.code,
                "message": e.message
            }
        }), 403

    except AIParseError as e:
        conn.rollback()
        return jsonify({
            "ok": False,
            "error": {
                "code": "ai_parse_error",
                "message": str(e)
            }
        }), 502

    except Exception as e:
        conn.rollback()
    
        # Safe: do not log transcript_text or raw_text.
        logging.exception(
            "AI summarize failed (user_id=%s, engagement_id=%s)",
            getattr(current_user, "id", None),
            engagement_id,
        )
    
        return jsonify({
            "ok": False,
            "error": {
                "code": "ai_request_failed",
                "message": "AI request failed."
            }
        }), 500

    finally:
        try:
            conn.close()
        except Exception:
            pass

# --- Security & session config ---
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    # Fail fast so you remember to set this in Render / .env
    raise RuntimeError("SECRET_KEY environment variable is required")

app.secret_key = SECRET_KEY

# Cookie settings
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# In production (e.g., Render), force HTTPS-only cookies if FLASK_ENV=production
if os.environ.get("FLASK_ENV") == "production":
    app.config["SESSION_COOKIE_SECURE"] = True

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Optional token for calendar feed protection
ICS_TOKEN = os.environ.get("ICS_TOKEN")

PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "").strip().rstrip("/")
app.config["PUBLIC_BASE_URL"] = PUBLIC_BASE_URL
                            
@app.context_processor
def inject_calendar_feed_url():
    calendar_url = url_for("followups_ics")
    if ICS_TOKEN:
        calendar_url = calendar_url + f"?key={ICS_TOKEN}"
    return {"calendar_feed_url": calendar_url}

@app.context_processor
def inject_current_year():
    return {"current_year": datetime.now(get_user_tz()).year}

DATABASE_URL = os.environ.get("DATABASE_URL")
SHORTCUT_API_KEY = os.environ.get("SHORTCUT_API_KEY")  # optional shared secret

def get_db():
    # Pick DB based on environment
    if APP_ENV == "PROD":
        db_url = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL")
    else:
        db_url = os.getenv("LOCAL_DATABASE_URL") or os.getenv("DATABASE_URL")

    if not db_url:
        raise RuntimeError(f"Database URL is not set for APP_ENV={APP_ENV}")

    # Normalize scheme for psycopg2 (some providers still use postgres://)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # Safety stop: never allow local environment to connect to production DB
    if APP_ENV != "PROD":
        # Block common prod indicators. Adjust if your prod URL differs.
        if "realestatecrm_db" in db_url or "render.com" in db_url or "10.22." in db_url:
            raise RuntimeError("Safety stop: LOCAL environment cannot connect to production database.")

    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.email = row["email"]
        self.first_name = row.get("first_name")
        self.last_name = row.get("last_name")
        self.role = row.get("role", "owner")
        self._is_active = row.get("is_active", True)

    def get_id(self):
        return str(self.id)

    def is_active(self):
        return bool(self._is_active)

@app.template_filter("fmt_date")
def fmt_date(value):
    if not value:
        return "—"

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date().strftime("%b %-d, %Y")
        except Exception:
            return value

    if isinstance(value, datetime):
        return value.date().strftime("%b %-d, %Y")

    if isinstance(value, date):
        return value.strftime("%b %-d, %Y")

    return str(value)


@app.template_filter("fmt_dt")
def fmt_dt(value):
    if not value:
        return "—"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except Exception: 
            return value

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=NY)
        else:
            value = value.astimezone(get_user_tz())

        return value.strftime("%b %-d, %Y %-I:%M %p")

    return str(value)

def owner_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if (getattr(current_user, "role", None) or "").strip().lower() != "owner":
            abort(403)
        return f(*args, **kwargs)
    return wrapper

def normalize_url(value):
    v = (value or "").strip()
    if not v:
        return None
    # If it already has a scheme (http://, https://, etc.), keep it
    if "://" in v:
        return v
    return f"https://{v}"

def parse_12h_time_to_24h(hour_str, minute_str, ampm_str, default_hour=9, default_minute=0):
    hour_str = (hour_str or "").strip()
    minute_str = (minute_str or "").strip()
    ampm = (ampm_str or "").strip().upper()

    if not hour_str or not minute_str or ampm not in ("AM", "PM"):
        return default_hour, default_minute

    hour12 = int(hour_str)
    minute = int(minute_str)

    if ampm == "AM":
        hour24 = 0 if hour12 == 12 else hour12
    else:  # PM
        hour24 = 12 if hour12 == 12 else hour12 + 12

    return hour24, minute
from utils.token_helpers import build_link
from utils.auth_tokens_db import (
    create_user_invite,
    get_valid_invite_by_raw_token,
    consume_invite,
    revoke_invite,
    create_password_reset,
    get_valid_password_reset_by_raw_token,
    consume_password_reset,
    revoke_all_password_resets_for_user,
)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, email, first_name, last_name, role, is_active
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return User(row) if row else None

def generate_public_token() -> str:
    return secrets.token_urlsafe(24)

def is_safe_url(target: str) -> bool:
    if not target:
        return False

    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))

    return (
        redirect_url.scheme in ("http", "https")
        and host_url.netloc == redirect_url.netloc
    )

def truthy_checkbox(value):
    return value in ("on", "true", "1", "yes")

def normalize_email(email: str) -> str:
    return (email or "").strip().lower()

def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Normalize a US phone number to E.164 (+1##########) when possible.
    Returns None for blank input so DB stores NULL.
    For non-US / unrecognized lengths, returns trimmed original string.
    """
    s = (phone or "").strip()
    if not s:
        return None

    has_plus = s.startswith("+")
    digits = re.sub(r"\D", "", s)

    # US: 10 digits or 11 starting with 1
    if len(digits) == 11 and digits.startswith("1"):
        return "+1" + digits[1:]
    if len(digits) == 10:
        return "+1" + digits

    # If user included + and we have digits, keep it like +<digits>
    if has_plus and digits:
        return "+" + digits

    # Fallback: keep as typed (trimmed)
    return s

def format_phone_display(phone: str) -> str:
    """
    Display US E.164 +1########## as 732-555-1212.
    Otherwise return the trimmed original.
    """
    s = (phone or "").strip()
    m = re.fullmatch(r"\+1(\d{10})", s)
    if not m:
        return s

    d = m.group(1)
    return f"{d[0:3]}-{d[3:6]}-{d[6:10]}"

def parse_int_or_none(value):
    """
    Convert a form field to an int, or return None if blank/invalid.
    """
    if value is None:
        return None

    s = str(value).strip()
    if not s:
        return None

    # Optional: support "500,000" style input
    s = s.replace(",", "")

    try:
        return int(s)
    except ValueError:
        return None

def get_professionals_for_dropdown(user_id: int, category=None):
    """
    Return a list of professionals for dropdowns.
    Excludes blacklist. Orders by grade priority and then by name.
    If category is given (for example 'Attorney'), filters to that category.
    Scoped by user_id for multi-tenant safety.
    """
    conn = get_db()
    cur = conn.cursor()

    try:
        base_sql = """
            SELECT id, name, company, phone, email, category, grade
            FROM professionals
            WHERE user_id = %s
              AND grade != %s
        """
        params = [user_id, 'blacklist']

        if category:
            base_sql += " AND category = %s"
            params.append(category)

        base_sql += """
            ORDER BY
                CASE grade
                    WHEN 'core' THEN 1
                    WHEN 'preferred' THEN 2
                    WHEN 'vetting' THEN 3
                    ELSE 4
                END,
                name
        """

        cur.execute(base_sql, params)
        return cur.fetchall()

    finally:
        cur.close()
        conn.close()

def init_db():
    if APP_ENV == "PROD":
        raise RuntimeError("init_db() is disabled in production.")
    conn = get_db()
    cur = conn.cursor()
    try:
        
        # Ensure base contacts table exists
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                lead_type TEXT,
                pipeline_stage TEXT,
                price_min INTEGER,
                price_max INTEGER,
                target_area TEXT,
                source TEXT,
                priority TEXT,
                last_contacted TEXT,
                next_follow_up TEXT,
                notes TEXT
            )
            """
        )
        conn.commit()
    
        # Schema upgrades for contacts (safe to re-run)
        schema_updates = [
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS first_name TEXT",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS last_name TEXT",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS current_address TEXT",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS current_city TEXT",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS current_state TEXT",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS current_zip TEXT",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS subject_address TEXT",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS subject_city TEXT",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS subject_state TEXT",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS subject_zip TEXT",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS next_follow_up_time TEXT",
        ]
    
        for stmt in schema_updates:
            try:
                cur.execute(stmt)
                conn.commit()
            except Exception as e:
                print("Schema update skipped:", e)
    
        # Interactions table for engagement log
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS interactions (
                id SERIAL PRIMARY KEY,
                contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                kind TEXT NOT NULL,
                happened_at DATE,
                notes TEXT
            )
            """
        )
        conn.commit()
    
        # Schema upgrades for interactions
        try:
            cur.execute(
                "ALTER TABLE interactions ADD COLUMN IF NOT EXISTS time_of_day TEXT"
            )
            conn.commit()
        except Exception as e:
            print("Interaction schema update skipped:", e)
    
        # # Related contacts table (associated contacts)
        # cur.execute(
        #     """
        #     CREATE TABLE IF NOT EXISTS related_contacts (
        #         id SERIAL PRIMARY KEY,
        #         contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
        #         related_name TEXT NOT NULL,
        #         relationship TEXT,
        #         email TEXT,
        #         phone TEXT,
        #         notes TEXT
        #     )
        #     """
        # )
        # conn.commit()
    
        # Buyer profiles table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS buyer_profiles (
                id SERIAL PRIMARY KEY,
                contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                timeframe TEXT,
                min_price INTEGER,
                max_price INTEGER,
                areas TEXT,
                property_types TEXT,
                preapproval_status TEXT,
                lender_name TEXT,
                referral_source TEXT,
                notes TEXT
            )
            """
        )
        
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS buyer_properties (
                id SERIAL PRIMARY KEY,
                buyer_profile_id INTEGER NOT NULL REFERENCES buyer_profiles(id) ON DELETE CASCADE,
                address_line TEXT,
                city TEXT,
                state TEXT,
                postal_code TEXT,
                offer_status TEXT CHECK (
                    offer_status IN (
                        'considering',
                        'accepted',
                        'lost',
                        'attorney review',
                        'under contract'
                    )
                ),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    
    
        # Upgrades for buyer_profiles (property type, documents checklist, professionals)
        buyer_profile_upgrades = [
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS property_type TEXT",
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS cis_signed BOOLEAN",
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS buyer_agreement_signed BOOLEAN",
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS wire_fraud_notice_signed BOOLEAN",
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS dual_agency_consent_signed BOOLEAN",
    
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS buyer_attorney_name TEXT",
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS buyer_attorney_email TEXT",
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS buyer_attorney_phone TEXT",
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS buyer_attorney_referred BOOLEAN",
    
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS buyer_lender_email TEXT",
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS buyer_lender_phone TEXT",
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS buyer_lender_referred BOOLEAN",
    
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS buyer_inspector_name TEXT",
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS buyer_inspector_email TEXT",
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS buyer_inspector_phone TEXT",
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS buyer_inspector_referred BOOLEAN",
    
            "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS other_professionals TEXT"
        ]
    
        for stmt in buyer_profile_upgrades:
            try:
                cur.execute(stmt)
                conn.commit()
            except Exception as e:
                print("buyer_profiles schema update skipped:", e)
    
        # Seller profiles table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS seller_profiles (
                id SERIAL PRIMARY KEY,
                contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                timeframe TEXT,
                motivation TEXT,
                estimated_price INTEGER,
                property_address TEXT,
                condition_notes TEXT,
                referral_source TEXT,
                notes TEXT
            )
            """
        )
        conn.commit()
    
        # Upgrades for seller_profiles (property type + professionals)
        seller_profile_upgrades = [
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS property_type TEXT",
    
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS seller_attorney_name TEXT",
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS seller_attorney_email TEXT",
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS seller_attorney_phone TEXT",
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS seller_attorney_referred BOOLEAN",
    
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS seller_lender_name TEXT",
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS seller_lender_email TEXT",
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS seller_lender_phone TEXT",
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS seller_lender_referred BOOLEAN",
    
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS seller_inspector_name TEXT",
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS seller_inspector_email TEXT",
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS seller_inspector_phone TEXT",
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS seller_inspector_referred BOOLEAN",
    
            "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS other_professionals TEXT"
        ]
    
        for stmt in seller_profile_upgrades:
            try:
                cur.execute(stmt)
                conn.commit()
            except Exception as e:
                print("seller_profiles schema update skipped:", e)
    
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS professionals (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                company TEXT,
                phone TEXT,
                email TEXT,
                category TEXT,          -- Attorney, Lender, Inspector, Contractor, etc
                grade TEXT NOT NULL,    -- core, preferred, vetting, blacklist
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()
    
def get_contact_associations(conn, user_id, contact_id):
    """
    Symmetric associations for a contact:
    if current contact is primary, other is related, and vice versa.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
          ca.id,
          ca.relationship_type,
          ca.notes,

          CASE
            WHEN ca.contact_id_primary = %s THEN ca.contact_id_related
            ELSE ca.contact_id_primary
          END AS other_contact_id,

          COALESCE(
            NULLIF(TRIM(c.name), ''),
            NULLIF(TRIM(CONCAT_WS(' ', c.first_name, c.last_name)), ''),
            '(Unnamed)'
          ) AS other_name,

          c.email AS other_email,
          c.phone AS other_phone

        FROM contact_associations ca
        JOIN contacts c
          ON c.id = CASE
            WHEN ca.contact_id_primary = %s THEN ca.contact_id_related
            ELSE ca.contact_id_primary
          END

        WHERE ca.user_id = %s
          AND (ca.contact_id_primary = %s OR ca.contact_id_related = %s)

        ORDER BY other_name ASC
        """,
        (contact_id, contact_id, user_id, contact_id, contact_id),
    )
    return cur.fetchall()

def create_contact_association(conn, user_id, contact_id_a, contact_id_b, relationship_type=None):
    """
    Store once in canonical ordering so A-B and B-A are the same row.
    """
    if contact_id_a == contact_id_b:
        raise ValueError("Cannot associate a contact with itself.")

    primary_id = min(contact_id_a, contact_id_b)
    related_id = max(contact_id_a, contact_id_b)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO contact_associations (user_id, contact_id_primary, contact_id_related, relationship_type)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, contact_id_primary, contact_id_related)
        DO UPDATE SET relationship_type = EXCLUDED.relationship_type,
                      updated_at = NOW()
        RETURNING id
        """,
        (user_id, primary_id, related_id, relationship_type),
    )
    row = cur.fetchone()
    return row["id"] if row and isinstance(row, dict) else (row[0] if row else None)


LEAD_TYPES = [
    "Buyer",
    "Seller",
    "Landlord",
    "Tenant",
    "Investor",
    "Probate / Estate",
    "Sphere",
    "Other",
]

PIPELINE_STAGES = [
    "New lead",
    "Nurture",
    "Active",
    "Under contract",
    "Closed",
    "Past Client / Relationship",
    "Lost",
]

PRIORITIES = [
    "Hot",
    "Warm",
    "Cold",
]

SOURCES = [
    "Referral",
    "Online",
    "Open house",
    "Sign call",
    "Attorney / CPA",
    "Farming",
    "Sphere",
    "Other",
]

TRANSACTION_STATUSES = [
    ("draft", "Draft"),
    ("coming_soon", "Coming Soon"),
    ("active", "Active"),
    ("attorney_review", "Attorney Review"),
    ("pending_uc", "Pending / Under Contract"),
    ("closed", "Closed"),
    ("temp_off_market", "Temporarily Off Market"),
    ("withdrawn", "Withdrawn"),
    ("canceled", "Canceled"),
    ("expired", "Expired"),
]

LISTING_STATUSES = [
    ("draft", "Draft"),
    ("coming_soon", "Coming Soon"),
    ("active", "Active"),
    ("under_contract", "Under Contract"),
    ("back_on_market", "Back on Market"),
    ("withdrawn", "Withdrawn"),
    ("expired", "Expired"),
    ("closed", "Closed"),
]

OFFER_STATUSES = [
    ("draft", "Draft"),
    ("submitted", "Submitted"),
    ("countered", "Countered"),
    ("accepted", "Accepted"),
    ("rejected", "Rejected"),
    ("withdrawn", "Withdrawn"),
    ("under_contract", "Under Contract"),
    ("closed", "Closed"),
]

LISTING_STATUS_VALUES = {v for v, _ in LISTING_STATUSES}
OFFER_STATUS_VALUES = {v for v, _ in OFFER_STATUSES}

BASE_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Ulysses CRM</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet"
    >
    <style>
      body {
        background-color: #6eb8f9;
      }
      .card-add {
        border-top: 4px solid #198754;
      }
      .card-add .card-header {
        background-color: rgba(25, 135, 84, 0.08);
        font-weight: 600;
      }
      .card-edit {
        border-top: 4px solid #0d6efd;
      }
      .card-edit .card-header {
        background-color: rgba(13, 110, 253, 0.08);
        font-weight: 600;
      }
      .card-followups .card-header {
        font-weight: 600;
      }
      @media (max-width: 576px) {
        .nav-pipe {
          display: none;
        }
      }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-md navbar-light bg-white shadow-sm border-bottom sticky-top">
  <div class="container-fluid py-2" style="font-size: 0.9rem;">
    
    <!-- Logo -->
    <a href="{{ url_for('dashboard') }}" class="navbar-brand d-flex align-items-center text-dark">
      <img
        src="{{ url_for('static', filename='ulysses-logo.svg') }}"
        alt="Ulysses CRM"
        style="height: 50px;"
        class="me-2"
      >
    </a>

    <!-- Hamburger button -->
    <button class="navbar-toggler" type="button"
            data-bs-toggle="collapse"
            data-bs-target="#mainNav"
            aria-controls="mainNav"
            aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>

    <!-- Collapsible nav links -->
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-0 ms-md-2">

        <li class="nav-item">
          <a href="{{ url_for('dashboard') }}"
             class="nav-link {% if active_page == 'dashboard' %}fw-semibold{% endif %}">
            Dashboard
          </a>
        </li>

        <li class="nav-item">
          <a href="{{ url_for('contacts') }}"
             class="nav-link {% if active_page == 'contacts' %}fw-semibold{% endif %}">
            Contacts
          </a>
        </li>

        <li class="nav-item">
          <a href="{{ url_for('followups') }}"
             class="nav-link {% if active_page == 'followups' %}fw-semibold{% endif %}">
            Follow Up Dashboard
          </a>
        </li>

        <li class="nav-item">
          <a href="{{ url_for('followups_ics') }}"
             class="nav-link"
             target="_blank">
            Calendar Feed
          </a>
        </li>

      </ul>
    </div>
  </div>
</nav>

<div class="container py-4">

    <!-- Add Contact form -->
    <div id="add-contact" class="card card-add mb-4">
        <div class="card-header">
            Add New Contact
        </div>
        <div class="card-body bg-white">
            <form method="post" action="{{ url_for('add_contact') }}">
                <div class="row g-3">
                    <div class="col-md-3">
                        <label class="form-label">First Name *</label>
                        <input name="first_name" class="form-control" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Last Name</label>
                        <input name="last_name" class="form-control">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Email</label>
                        <input name="email" type="email" class="form-control">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Phone</label>
                        <input name="phone" class="form-control">
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Lead Type</label>
                        <select name="lead_type" class="form-select">
                            <option value="">Select...</option>
                            {% for t in lead_types %}
                                <option value="{{ t }}">{{ t }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Pipeline Stage</label>
                        <select name="pipeline_stage" class="form-select">
                            <option value="">Select...</option>
                            {% for s in pipeline_stages %}
                                <option value="{{ s }}">{{ s }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Priority</label>
                        <select name="priority" class="form-select">
                            <option value="">Select...</option>
                            {% for p in priorities %}
                                <option value="{{ p }}">{{ p }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Source</label>
                        <select name="source" class="form-select">
                            <option value="">Select...</option>
                            {% for s in sources %}
                                <option value="{{ s }}">{{ s }}</option>
                            {% endfor %}
                        </select>
                    </div>

                                        <!-- Current address -->
                    <div class="col-12 mt-3">
                        <h6 class="fw-bold mb-2">Current Address</h6>
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Street Address</label>
                        <input name="current_address" class="form-control" placeholder="123 Main St">
                    </div>

                    <div class="col-md-2 col-6">
                        <label class="form-label">City</label>
                        <input name="current_city" class="form-control" placeholder="Keyport">
                    </div>
                    <div class="col-md-2 col-3">
                        <label class="form-label">State</label>
                        <input name="current_state" class="form-control" placeholder="NJ">
                    </div>
                    <div class="col-md-2 col-3">
                        <label class="form-label">ZIP</label>
                        <input name="current_zip" class="form-control" placeholder="07735">
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Last Contacted</label>
                        <input name="last_contacted" type="date" class="form-control" value="{{ today }}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Next Follow Up (Date)</label>
                        <input name="next_follow_up" type="date" class="form-control">
                    </div>

                    <div class="col-md-2">
                        <label class="form-label">Follow Up Hour</label>
                        <select name="next_follow_up_hour" class="form-select">
                            <option value="">HH</option>
                            {% for h in range(1,13) %}
                                <option value="{{ h }}">{{ h }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Follow Up Minute</label>
                        <select name="next_follow_up_minute" class="form-select">
                            <option value="">MM</option>
                            {% for m in ["00", "15", "30", "45"] %}
                                <option value="{{ m }}">{{ m }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">AM / PM</label>
                        <select name="next_follow_up_ampm" class="form-select">
                            <option value="">AM / PM</option>
                            <option value="AM">AM</option>
                            <option value="PM">PM</option>
                        </select>
                    </div>

                    <div class="col-12">
                        <label class="form-label">Notes</label>
                        <textarea name="notes" class="form-control" rows="2"
                         placeholder="Motivation, timing, specific needs..."></textarea>
                    </div>
                </div>
                <button class="btn btn-success mt-3" type="submit">Add Contact</button>
            </form>
        </div>
    </div>

    <!-- Filters -->
    <div class="card mb-3">
        <div class="card-header fw-bold">
            Filters
        </div>
        <div class="card-body bg-white">
            <form class="row g-3 mb-0" method="get" action="{{ url_for('contacts') }}">
                <div class="col-md-3">
                    <input type="text" name="q" value="{{ request.args.get('q','') }}" class="form-control"
                           placeholder="Search name, email, phone">
                </div>
                <div class="col-md-2">
                    <select name="lead_type" class="form-select">
                        <option value="">Lead Type</option>
                        {% for t in lead_types %}
                            <option value="{{ t }}" {% if request.args.get('lead_type') == t %}selected{% endif %}>{{ t }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-2">
                    <select name="pipeline_stage" class="form-select">
                        <option value="">Stage</option>
                        {% for s in pipeline_stages %}
                            <option value="{{ s }}" {% if request.args.get('pipeline_stage') == s %}selected{% endif %}>{{ s }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-2">
                    <select name="priority" class="form-select">
                        <option value="">Priority</option>
                        {% for p in priorities %}
                            <option value="{{ p }}" {% if request.args.get('priority') == p %}selected{% endif %}>{{ p }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-3">
                    <input type="text" name="target_area" value="{{ request.args.get('target_area','') }}" class="form-control"
                           placeholder="Filter by area">
                </div>
                <div class="col-md-3">
                    <button class="btn btn-outline-secondary" type="submit">Apply Filters</button>
                    <a href="{{ url_for('contacts') }}" class="btn btn-link">Clear</a>
                </div>
            </form>
        </div>
    </div>

    <!-- Contacts list -->
    <div class="card">
        <div class="card-header fw-bold">
            Contacts ({{ contacts|length }})
        </div>
        <div class="list-group list-group-flush bg-white">
            {% for c in contacts %}
                <div class="list-group-item">
                    <!-- Top row: name + quick status -->
                    <div class="d-flex justify-content-between align-items-start flex-wrap">
                        <div class="me-3">
                            <a href="{{ url_for('edit_contact', contact_id=c['id']) }}"
                               class="fw-semibold text-decoration-none">
                                {% if c["first_name"] or c["last_name"] %}
                                    {{ (c["first_name"] or "") ~ (" " if c["first_name"] and c["last_name"] else "") ~ (c["last_name"] or "") }}
                                {% else %}
                                    {{ c["name"] }}
                                {% endif %}
                            </a>
                            <div class="small text-muted mt-1">
                                {% if c["lead_type"] %}{{ c["lead_type"] }}{% endif %}
                                {% if c["lead_type"] and c["pipeline_stage"] %} · {% endif %}
                                {% if c["pipeline_stage"] %}{{ c["pipeline_stage"] }}{% endif %}
                            </div>
                        </div>
                        <div class="text-end small mt-2 mt-sm-0">
                            {% if c["priority"] %}
                                {% if c["priority"] == "Hot" %}
                                    <span class="badge bg-danger">Hot</span>
                                {% elif c["priority"] == "Warm" %}
                                    <span class="badge bg-warning text-dark">Warm</span>
                                {% elif c["priority"] == "Cold" %}
                                    <span class="badge bg-secondary">Cold</span>
                                {% else %}
                                    <span class="badge bg-secondary">{{ c["priority"] }}</span>
                                {% endif %}
                            {% endif %}
                            {% if c["next_follow_up"] %}
                                <div class="mt-1">
                                    <strong>Next:</strong>
                                    {{ c["next_follow_up"] }}
                                    {% if c["next_follow_up_time"] %}
                                        {{ c["next_follow_up_time"] }}
                                    {% endif %}
                                </div>
                            {% endif %}
                            {% if c["last_contacted"] %}
                                <div class="text-muted mt-1">
                                    Last: {{ c["last_contacted"] }}
                                </div>
                            {% endif %}
                        </div>
                    </div>

                    <!-- Middle rows: price, area, source -->
                    <div class="row small mt-2">
                        <div class="col-md-4 mb-1">
                            {% if c["price_min"] or c["price_max"] %}
                                <strong>Price:</strong>
                                {% if c["price_min"] %}${{ "{:,}".format(c["price_min"]) }}{% endif %}
                                {% if c["price_min"] and c["price_max"] %} – {% endif %}
                                {% if c["price_max"] %}${{ "{:,}".format(c["price_max"]) }}{% endif %}
                            {% endif %}
                        </div>
                        <div class="col-md-4 mb-1">
                            {% if c["target_area"] %}
                                <strong>Area:</strong> {{ c["target_area"] }}
                            {% endif %}
                        </div>
                        <div class="col-md-4 mb-1">
                            {% if c["source"] %}
                                <strong>Source:</strong> {{ c["source"] }}
                            {% endif %}
                        </div>
                    </div>

                    <!-- Addresses -->
                    <div class="row small mt-1">
                        <div class="col-md-6 mb-1">
                            {% if c["current_address"] or c["current_city"] or c["current_state"] or c["current_zip"] %}
                                <strong>Current:</strong>
                                {{ c["current_address"] or "" }}
                                {% if c["current_city"] %}, {{ c["current_city"] }}{% endif %}
                                {% if c["current_state"] %}, {{ c["current_state"] }}{% endif %}
                                {% if c["current_zip"] %} {{ c["current_zip"] }}{% endif %}
                            {% endif %}
                        </div>
                        <div class="col-md-6 mb-1">
                            {% if c["subject_address"] or c["subject_city"] or c["subject_state"] or c["subject_zip"] %}
                                <strong>Subject:</strong>
                                {{ c["subject_address"] or "" }}
                                {% if c["subject_city"] %}, {{ c["subject_city"] }}{% endif %}
                                {% if c["subject_state"] %}, {{ c["subject_state"] }}{% endif %}
                                {% if c["subject_zip"] %} {{ c["subject_zip"] }}{% endif %}
                            {% endif %}
                        </div>
                    </div>

                    <!-- Notes -->
                    {% if c["notes"] %}
                        <div class="small mt-2">
                            <strong>Notes:</strong> {{ c["notes"] }}
                        </div>
                    {% endif %}

                    <!-- Actions -->
                    <div class="mt-2 d-flex flex-wrap gap-1">
                    
                        {% if c["phone"] %}
                            <a href="tel:{{ c['phone'] }}"
                               class="btn btn-sm btn-outline-success">
                                Call
                            </a>
                    
                            <a href="sms:{{ c['phone'] }}"
                               class="btn btn-sm btn-outline-secondary">
                                Text
                            </a>
                        {% endif %}
                    
                        {% if c["email"] %}
                            <a href="mailto:{{ c['email'] }}"
                               class="btn btn-sm btn-outline-info">
                                Email
                            </a>
                        {% endif %}
                    
                        <a href="{{ url_for('edit_contact', contact_id=c['id']) }}"
                           class="btn btn-sm btn-outline-primary">
                            Edit
                        </a>

                        <a href="{{ url_for('buyer_profile', contact_id=c['id']) }}"
                           class="btn btn-sm {% if c['has_buyer_profile'] %}btn-primary fw-semibold{% else %}btn-outline-dark{% endif %}">
                            {% if c['has_buyer_profile'] %}
                                <i class="bi bi-person-check me-1"></i> Committed Buyer Sheet
                            {% else %}
                                Commit as Buyer
                            {% endif %}
                        </a>

                        <a href="{{ url_for('seller_profile', contact_id=c['id']) }}"
                           class="btn btn-sm {% if c['has_seller_profile'] %}btn-success fw-semibold{% else %}btn-outline-dark{% endif %}">
                            {% if c['has_seller_profile'] %}
                                <i class="bi bi-house-check me-1"></i> Committed Seller Sheet
                            {% else %}
                                Commit as Seller
                            {% endif %}
                        </a>
                                            
                        <a href="{{ url_for('delete_contact', contact_id=c['id']) }}"
                           class="btn btn-sm btn-outline-danger"
                           onclick="return confirm('Delete this contact?');">
                            Delete
                        </a>
                    </div>
                </div>
            {% else %}
                <div class="list-group-item text-center text-muted">
                    No contacts yet.
                </div>
            {% endfor %}
        </div>
    </div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

EDIT_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Ulysses CRM - Edit Contact</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet"
    >
    <style>
      body {
        background-color: #6eb8f9;
      }
      .card-edit {
        border-top: 4px solid #0d6efd;
      }
      .card-edit .card-header {
        background-color: rgba(13, 110, 253, 0.08);
        font-weight: 600;
      }
      .card-engagement .card-header {
        font-weight: 600;
      }
      @media (max-width: 576px) {
        .nav-pipe {
          display: none;
        }
      }

    </style>
</head>
<body>

<nav class="navbar navbar-expand-md navbar-light bg-white shadow-sm border-bottom sticky-top">
  <div class="container-fluid py-2" style="font-size: 0.9rem;">
    
    <!-- Logo -->
    <a href="{{ url_for('dashboard') }}" class="navbar-brand d-flex align-items-center text-dark">
      <img
        src="{{ url_for('static', filename='ulysses-logo.svg') }}"
        alt="Ulysses CRM"
        style="height: 50px;"
        class="me-2"
      >
    </a>

    <!-- Hamburger button -->
    <button class="navbar-toggler" type="button"
            data-bs-toggle="collapse"
            data-bs-target="#mainNav"
            aria-controls="mainNav"
            aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>

    <!-- Collapsible nav links -->
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-0 ms-md-2">

        <li class="nav-item">
          <a href="{{ url_for('dashboard') }}"
             class="nav-link {% if active_page == 'dashboard' %}fw-semibold{% endif %}">
            Dashboard
          </a>
        </li>

        <li class="nav-item">
          <a href="{{ url_for('contacts') }}"
             class="nav-link {% if active_page == 'contacts' %}fw-semibold{% endif %}">
            Contacts
          </a>
        </li>

        <li class="nav-item">
          <a href="{{ url_for('followups') }}"
             class="nav-link {% if active_page == 'followups' %}fw-semibold{% endif %}">
            Follow Up Dashboard
          </a>
        </li>

        <li class="nav-item">
          <a href="{{ url_for('followups_ics') }}"
             class="nav-link"
             target="_blank">
            Calendar Feed
          </a>
        </li>

      </ul>
    </div>
  </div>
</nav>

<div class="container py-4">

    <!-- Edit Contact card -->
    <div class="card card-edit mb-4">
        <div class="card-header">
            Edit Contact
        </div>
        <div class="card-body bg-white">
            <form method="post">
                <div class="row g-3">
                    <div class="col-md-3">
                        <label class="form-label">First Name *</label>
                        <input name="first_name" class="form-control" required value="{{ c['first_name'] or '' }}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Last Name</label>
                        <input name="last_name" class="form-control" value="{{ c['last_name'] or '' }}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Email</label>
                        <input name="email" type="email" class="form-control" value="{{ c['email'] or '' }}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Phone</label>
                        <input name="phone" class="form-control" value="{{ c['phone'] or '' }}">
                    </div>

                    <!-- Quick actions row -->
                    <div class="col-12 d-flex flex-wrap gap-2">
                        {% if c["phone"] %}
                            <a href="tel:{{ c['phone'] }}" class="btn btn-sm btn-outline-secondary">
                                Call
                            </a>
                            <a href="sms:{{ c['phone'] }}" class="btn btn-sm btn-outline-secondary">
                                Text
                            </a>
                        {% endif %}
                        {% if c["email"] %}
                            <a href="mailto:{{ c['email'] }}" class="btn btn-sm btn-outline-secondary">
                                Email
                            </a>
                        {% endif %}

                        <a href="{{ url_for('buyer_profile', contact_id=c['id']) }}"
                           class="btn btn-sm {% if c['has_buyer_profile'] %}btn-primary fw-semibold{% else %}btn-outline-dark{% endif %}">
                            {% if c['has_buyer_profile'] %}
                                <i class="bi bi-person-check me-1"></i> Committed Buyer Sheet
                            {% else %}
                                Commit as Buyer
                            {% endif %}
                        </a>

                        <a href="{{ url_for('seller_profile', contact_id=c['id']) }}"
                           class="btn btn-sm {% if c['has_seller_profile'] %}btn-success fw-semibold{% else %}btn-outline-dark{% endif %}">
                            {% if c['has_seller_profile'] %}
                                <i class="bi bi-house-check me-1"></i> Committed Seller Sheet
                            {% else %}
                                Commit as Seller
                            {% endif %}
                        </a>
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Lead Type</label>
                        <select name="lead_type" class="form-select">
                            <option value="">Select...</option>
                            {% for t in lead_types %}
                                <option value="{{ t }}" {% if c['lead_type'] == t %}selected{% endif %}>{{ t }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Pipeline Stage</label>
                        <select name="pipeline_stage" class="form-select">
                            <option value="">Select...</option>
                            {% for s in pipeline_stages %}
                                <option value="{{ s }}" {% if c['pipeline_stage'] == s %}selected{% endif %}>{{ s }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Priority</label>
                        <select name="priority" class="form-select">
                            <option value="">Select...</option>
                            {% for p in priorities %}
                                <option value="{{ p }}" {% if c['priority'] == p %}selected{% endif %}>{{ p }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Source</label>
                        <select name="source" class="form-select">
                            <option value="">Select...</option>
                            {% for s in sources %}
                                <option value="{{ s }}" {% if c['source'] == s %}selected{% endif %}>{{ s }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="col-12 mt-3">
                        <h6 class="fw-bold mb-2">Subject Property</h6>
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Street Address</label>
                        <input name="subject_address" class="form-control" value="{{ c['subject_address'] or '' }}">
                    </div>

                    <div class="col-md-2 col-6">
                        <label class="form-label">City</label>
                        <input name="subject_city" class="form-control" value="{{ c['subject_city'] or '' }}">
                    </div>
                    <div class="col-md-2 col-3">
                        <label class="form-label">State</label>
                        <input name="subject_state" class="form-control" value="{{ c['subject_state'] or '' }}">
                    </div>
                    <div class="col-md-2 col-3">
                        <label class="form-label">ZIP</label>
                        <input name="subject_zip" class="form-control" value="{{ c['subject_zip'] or '' }}">
                    </div>

                    <div class="col-12 mt-3">
                        <h6 class="fw-bold mb-2">Current Address</h6>
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Street Address</label>
                        <input name="current_address" class="form-control" value="{{ c['current_address'] or '' }}">
                    </div>

                    <div class="col-md-2 col-6">
                        <label class="form-label">City</label>
                        <input name="current_city" class="form-control" value="{{ c['current_city'] or '' }}">
                    </div>
                    <div class="col-md-2 col-3">
                        <label class="form-label">State</label>
                        <input name="current_state" class="form-control" value="{{ c['current_state'] or '' }}">
                    </div>
                    <div class="col-md-2 col-3">
                        <label class="form-label">ZIP</label>
                        <input name="current_zip" class="form-control" value="{{ c['current_zip'] or '' }}">
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Last Contacted</label>
                        <input name="last_contacted" type="date" class="form-control"
                               value="{{ c['last_contacted'] or '' }}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Next Follow Up (Date)</label>
                        <input name="next_follow_up" type="date" class="form-control"
                               value="{{ c['next_follow_up'] or '' }}">
                    </div>

                    <div class="col-md-2">
                        <label class="form-label">Follow Up Hour</label>
                        <select name="next_follow_up_hour" class="form-select">
                            <option value="">HH</option>
                            {% for h in range(1,13) %}
                                <option value="{{ h }}" {% if next_time_hour == h %}selected{% endif %}>{{ h }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Follow Up Minute</label>
                        <select name="next_follow_up_minute" class="form-select">
                            <option value="">MM</option>
                            {% for m in ["00", "15", "30", "45"] %}
                                <option value="{{ m }}" {% if next_time_minute == m %}selected{% endif %}>{{ m }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">AM / PM</label>
                        <select name="next_follow_up_ampm" class="form-select">
                            <option value="">AM / PM</option>
                            <option value="AM" {% if next_time_ampm == "AM" %}selected{% endif %}>AM</option>
                            <option value="PM" {% if next_time_ampm == "PM" %}selected{% endif %}>PM</option>
                        </select>
                    </div>

                    <div class="col-12">
                        <label class="form-label">Notes</label>
                        <textarea name="notes" class="form-control" rows="3">{{ c['notes'] or '' }}</textarea>
                    </div>
                </div>
                <button class="btn btn-primary mt-3" type="submit">Save Changes</button>
                <a href="{{ url_for('contacts') }}" class="btn btn-secondary mt-3">Cancel</a>
            </form>
        </div>
    </div>

    <!-- Engagement Log -->
    <div class="card card-engagement">
        <div class="card-header">
            Engagement Log
        </div>
        <div class="card-body bg-white">
            <form method="post" action="{{ url_for('add_interaction', contact_id=c['id']) }}">
                <div class="row g-3 align-items-end">
                    <div class="col-md-3">
                        <label class="form-label">Type</label>
                        <select name="kind" class="form-select" required>
                            <option value="Call">Phone Call</option>
                            <option value="Text">Text Message</option>
                            <option value="Email">Email</option>
                            <option value="Meeting">Meeting</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Date</label>
                        <input name="happened_at" type="date" class="form-control" value="{{ today }}">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Time (Optional)</label>
                        <select name="time_hour" class="form-select">
                            <option value="">Hour</option>
                            {% for h in range(1,13) %}
                                <option value="{{ h }}">{{ h }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">&nbsp;</label>
                        <select name="time_minute" class="form-select">
                            <option value="">Minute</option>
                            {% for m in ["00", "15", "30", "45"] %}
                                <option value="{{ m }}">{{ m }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">&nbsp;</label>
                        <select name="time_ampm" class="form-select">
                            <option value="">AM / PM</option>
                            <option value="AM">AM</option>
                            <option value="PM">PM</option>
                        </select>
                    </div>
                    <div class="col-12">
                        <label class="form-label">Notes</label>
                        <input name="notes" class="form-control" placeholder="Summary of the conversation or message">
                    </div>
                    <div class="col-12">
                        <button class="btn btn-outline-primary mt-2" type="submit">Save Interaction</button>
                    </div>
                </div>
            </form>
            
            {% if c['archived_at'] %}
              <div class="alert alert-warning d-flex justify-content-between align-items-center">
                <div>
                  <strong>This contact is archived.</strong>
                  It is excluded from dashboards, active lists, follow-ups, and task defaults.
                </div>
                <form method="post" action="{{ url_for('unarchive_contact', contact_id=c['id']) }}" class="mb-0">
                  <button type="submit" class="btn btn-sm btn-success">Unarchive</button>
                </form>
              </div>
            {% endif %}

            <hr>

            {% if interactions and interactions|length > 0 %}
                <div class="table-responsive">
                    <table class="table table-sm table-striped mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Date</th>
                                <th>Time</th>
                                <th>Type</th>
                                <th>Notes</th>
                                <th style="width: 80px;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                        {% for i in interactions %}
                            <tr>
                                <td>{{ i["happened_at"] or "" }}</td>
                                <td>{{ i["time_of_day"] or "" }}</td>
                                <td>{{ i["kind"] }}</td>
                                <td>{{ i["notes"] or "" }}</td>
                                <td>
                                    <a href="{{ url_for('delete_interaction', interaction_id=i['id']) }}"
                                       class="btn btn-sm btn-outline-danger"
                                       onclick="return confirm('Delete this interaction?');">
                                        Delete
                                    </a>
                                </td>
                            </tr>
                        {% endfor %}
                        </tbody>
                    </table>
                </div>
            {% else %}
                <p class="mb-0 text-muted">No interactions logged yet.</p>
            {% endif %}
        </div>
    </div>
    <!-- Associated Contacts -->
    <div class="card mt-4">
        <div class="card-header">
            Associated Contacts
        </div>
        <div class="card-body bg-white">

            <!-- Add associated contact form -->
            <form method="post" action="{{ url_for('add_related', contact_id=c['id']) }}">
                <div class="row g-3 align-items-end">
                    <div class="col-md-3">
                        <label class="form-label">Name *</label>
                        <input name="related_name" class="form-control" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Relationship</label>
                        <input name="relationship" class="form-control" placeholder="Spouse, brother, partner">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Email</label>
                        <input name="related_email" type="email" class="form-control">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Phone</label>
                        <input name="related_phone" class="form-control">
                    </div>
                    <div class="col-12">
                        <label class="form-label">Notes</label>
                        <input name="related_notes" class="form-control" placeholder="Any helpful context">
                    </div>
                    <div class="col-12">
                        <button class="btn btn-outline-primary mt-2" type="submit">
                            Add Associated Contact
                        </button>
                    </div>
                </div>
            </form>

            <hr>

            {% if related_contacts and related_contacts|length > 0 %}
                <div class="table-responsive">
                    <table class="table table-sm table-striped mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Name</th>
                                <th>Relationship</th>
                                <th>Email</th>
                                <th>Phone</th>
                                <th>Notes</th>
                                <th style="width: 80px;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                        {% for r in related_contacts %}
                            <tr>
                                <td>{{ r["related_name"] }}</td>
                                <td>{{ r["relationship"] or "" }}</td>
                                <td>{{ r["email"] or "" }}</td>
                                <td>{{ r["phone"] or "" }}</td>
                                <td>{{ r["notes"] or "" }}</td>
                                <td>
                                    <a href="{{ url_for('delete_related', related_id=r['id']) }}"
                                       class="btn btn-sm btn-outline-danger"
                                       onclick="return confirm('Delete this associated contact?');">
                                        Delete
                                    </a>
                                </td>
                            </tr>
                        {% endfor %}
                        </tbody>
                    </table>
                </div>
            {% else %}
                <p class="mb-0 text-muted">No associated contacts yet.</p>
            {% endif %}
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

BUYER_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Ulysses CRM - Buyer Profile</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet"
    >
    <style>
      body {
        background-color: #6eb8f9;
      }
      .card-edit {
        border-top: 4px solid #0d6efd;
      }
      .card-edit .card-header {
        background-color: rgba(13, 110, 253, 0.08);
        font-weight: 600;
      }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-md navbar-light bg-white shadow-sm border-bottom sticky-top">
  <div class="container-fluid py-2" style="font-size: 0.9rem;">
    <a href="{{ url_for('dashboard') }}" class="navbar-brand d-flex align-items-center text-dark">
      <img
        src="{{ url_for('static', filename='ulysses-logo.svg') }}"
        alt="Ulysses CRM"
        style="height: 50px;"
        class="me-2"
      >
    </a>

    <button class="navbar-toggler" type="button"
            data-bs-toggle="collapse"
            data-bs-target="#mainNav"
            aria-controls="mainNav"
            aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>

    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-0 ms-md-2">
        <li class="nav-item">
          <a href="{{ url_for('dashboard') }}"
             class="nav-link {% if active_page == 'dashboard' %}fw-semibold{% endif %}">
            Dashboard
          </a>
        </li>
        <li class="nav-item">
          <a href="{{ url_for('contacts') }}"
             class="nav-link {% if active_page == 'contacts' %}fw-semibold{% endif %}">
            Contacts
          </a>
        </li>
        <li class="nav-item">
          <a href="{{ url_for('followups') }}"
             class="nav-link {% if active_page == 'followups' %}fw-semibold{% endif %}">
            Follow Up Dashboard
          </a>
        </li>
        <li class="nav-item">
          <a href="{{ url_for('followups_ics') }}"
             class="nav-link"
             target="_blank">
            Calendar Feed
          </a>
        </li>
      </ul>
    </div>
  </div>
</nav>

<div class="container py-4">

    <div class="mb-3">
        <h2 class="mb-0">Buyer Profile</h2>
        <div class="text-muted">
            {{ contact_name }}
            {% if contact_email %} · {{ contact_email }}{% endif %}
            {% if contact_phone %} · {{ contact_phone }}{% endif %}
        </div>
    </div>

    <div class="card card-edit">
        <div class="card-header">
            Buyer Details
        </div>
        <div class="card-body bg-white">
            <form method="post">
                <div class="row g-3">

                    <div class="col-md-4">
                        <label class="form-label">Property Type</label>
                        <select name="property_type" class="form-select">
                            <option value="">Select...</option>
                            <option value="Residential"
                              {% if bp and bp['property_type'] == 'Residential' %}selected{% endif %}>
                              Residential
                            </option>
                            <option value="Commercial"
                              {% if bp and bp['property_type'] == 'Commercial' %}selected{% endif %}>
                              Commercial
                            </option>
                        </select>
                    </div>

                    <div class="col-md-4">
                        <label class="form-label">Timeframe</label>
                        <input name="timeframe" class="form-control"
                               placeholder="Next 3 months"
                               value="{{ bp['timeframe'] if bp else '' }}">
                    </div>

                    <div class="col-md-4">
                        <label class="form-label">Pre-Approval Status</label>
                        <input name="preapproval_status" class="form-control"
                               placeholder="Pre-approved, needs lender, etc."
                               value="{{ bp['preapproval_status'] if bp else '' }}">
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Min Price</label>
                        <input name="min_price" type="number" class="form-control"
                               value="{{ bp['min_price'] if bp and bp['min_price'] is not none else '' }}">
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Max Price</label>
                        <input name="max_price" type="number" class="form-control"
                               value="{{ bp['max_price'] if bp and bp['max_price'] is not none else '' }}">
                    </div>

                    <div class="col-12">
                        <label class="form-label">Preferred Areas</label>
                        <input name="areas" class="form-control"
                               placeholder="Keyport, Hazlet, Netflix zone"
                               value="{{ bp['areas'] if bp else '' }}">
                    </div>

                    <div class="col-12">
                        <label class="form-label">Property Types</label>
                        <input name="property_types" class="form-control"
                               placeholder="Single family, condo, mixed-use, etc."
                               value="{{ bp['property_types'] if bp else '' }}">
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Lender Name</label>
                        <input name="lender_name" class="form-control"
                               value="{{ bp['lender_name'] if bp else '' }}">
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Lender Email</label>
                        <input name="buyer_lender_email" class="form-control"
                               value="{{ bp['buyer_lender_email'] if bp else '' }}">
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Lender Phone</label>
                        <input name="buyer_lender_phone" class="form-control"
                               value="{{ bp['buyer_lender_phone'] if bp else '' }}">
                    </div>

                    <div class="col-12">
                        <div class="form-check">
                            <input class="form-check-input"
                                   type="checkbox"
                                   name="buyer_lender_referred"
                                   id="buyer_lender_referred"
                                   {% if bp and bp['buyer_lender_referred'] %}checked{% endif %}>
                            <label class="form-check-label" for="buyer_lender_referred">
                                Lender referred by me
                            </label>
                        </div>
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Referral Source</label>
                        <input name="referral_source" class="form-control"
                               placeholder="Who sent them to you?"
                               value="{{ bp['referral_source'] if bp else '' }}">
                    </div>

                    <div class="col-12">
                        <label class="form-label">Notes</label>
                        <textarea name="notes" class="form-control" rows="3"
                                  placeholder="Motivation, non-negotiables, etc.">{{ bp['notes'] if bp else '' }}</textarea>
                    </div>

                    <div class="col-12 mt-3">
                        <h6 class="fw-bold mb-2">Required Buyer Documents Checklist</h6>

                        <div class="form-check">
                            <input
                              class="form-check-input"
                              type="checkbox"
                              name="cis_signed"
                              id="cis_signed"
                              {% if bp and bp['cis_signed'] %}checked{% endif %}
                            >
                            <label class="form-check-label" for="cis_signed">
                                Consumer Information Statement signed?
                            </label>
                        </div>

                        <div class="form-check">
                            <input
                              class="form-check-input"
                              type="checkbox"
                              name="buyer_agreement_signed"
                              id="buyer_agreement_signed"
                              {% if bp and bp['buyer_agreement_signed'] %}checked{% endif %}
                            >
                            <label class="form-check-label" for="buyer_agreement_signed">
                                Buyer's Agency Agreement signed?
                            </label>
                        </div>

                        <div class="form-check">
                            <input
                              class="form-check-input"
                              type="checkbox"
                              name="wire_fraud_notice_signed"
                              id="wire_fraud_notice_signed"
                              {% if bp and bp['wire_fraud_notice_signed'] %}checked{% endif %}
                            >
                            <label class="form-check-label" for="wire_fraud_notice_signed">
                                Wire Fraud Notice signed?
                            </label>
                        </div>

                        <div class="form-check">
                            <input
                              class="form-check-input"
                              type="checkbox"
                              name="dual_agency_consent_signed"
                              id="dual_agency_consent_signed"
                              {% if bp and bp['dual_agency_consent_signed'] %}checked{% endif %}
                            >
                            <label class="form-check-label" for="dual_agency_consent_signed">
                                Informed Consent to Dual Agency signed?
                            </label>
                        </div>
                    </div>

                    <div class="col-12 mt-4">
                        <h6 class="fw-bold mb-2">Professionals</h6>
                    </div>

                    <div class="col-md-4">
                        <label class="form-label">Attorney Name</label>
                        <input name="buyer_attorney_name" class="form-control"
                               value="{{ bp['buyer_attorney_name'] if bp else '' }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Attorney Email</label>
                        <input name="buyer_attorney_email" class="form-control"
                               value="{{ bp['buyer_attorney_email'] if bp else '' }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Attorney Phone</label>
                        <input name="buyer_attorney_phone" class="form-control"
                               value="{{ bp['buyer_attorney_phone'] if bp else '' }}">
                    </div>
                    <div class="col-12">
                        <div class="form-check">
                            <input class="form-check-input"
                                   type="checkbox"
                                   name="buyer_attorney_referred"
                                   id="buyer_attorney_referred"
                                   {% if bp and bp['buyer_attorney_referred'] %}checked{% endif %}>
                            <label class="form-check-label" for="buyer_attorney_referred">
                                Attorney referred by me
                            </label>
                        </div>
                    </div>

                    <div class="col-md-4">
                        <label class="form-label">Home Inspector Name</label>
                        <input name="buyer_inspector_name" class="form-control"
                               value="{{ bp['buyer_inspector_name'] if bp else '' }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Home Inspector Email</label>
                        <input name="buyer_inspector_email" class="form-control"
                               value="{{ bp['buyer_inspector_email'] if bp else '' }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Home Inspector Phone</label>
                        <input name="buyer_inspector_phone" class="form-control"
                               value="{{ bp['buyer_inspector_phone'] if bp else '' }}">
                    </div>
                    <div class="col-12">
                        <div class="form-check">
                            <input class="form-check-input"
                                   type="checkbox"
                                   name="buyer_inspector_referred"
                                   id="buyer_inspector_referred"
                                   {% if bp and bp['buyer_inspector_referred'] %}checked{% endif %}>
                            <label class="form-check-label" for="buyer_inspector_referred">
                                Home inspector referred by me
                            </label>
                        </div>
                    </div>

                    <div class="col-12">
                        <label class="form-label">Other Professionals</label>
                        <textarea name="other_professionals"
                                  class="form-control"
                                  rows="2"
                                  placeholder="Title company, contractor, etc.">{{ bp['other_professionals'] if bp else '' }}</textarea>
                    </div>

                </div>
                <button class="btn btn-primary mt-3" type="submit">Save Buyer Profile</button>
                <a href="{{ url_for('edit_contact', contact_id=contact_id) }}" class="btn btn-secondary mt-3">
                    Back to Contact
                </a>
            </form>
        </div>
    </div>

</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

SELLER_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Ulysses CRM - Seller Profile</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet"
    >
    <style>
      body {
        background-color: #6eb8f9;
      }
      .card-edit {
        border-top: 4px solid #0d6efd;
      }
      .card-edit .card-header {
        background-color: rgba(13, 110, 253, 0.08);
        font-weight: 600;
      }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-md navbar-light bg-white shadow-sm border-bottom sticky-top">
  <div class="container-fluid py-2" style="font-size: 0.9rem;">
    <a href="{{ url_for('dashboard') }}" class="navbar-brand d-flex align-items-center text-dark">
      <img
        src="{{ url_for('static', filename='ulysses-logo.svg') }}"
        alt="Ulysses CRM"
        style="height: 50px;"
        class="me-2"
      >
    </a>

    <button class="navbar-toggler" type="button"
            data-bs-toggle="collapse"
            data-bs-target="#mainNav"
            aria-controls="mainNav"
            aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>

    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-0 ms-md-2">
        <li class="nav-item">
          <a href="{{ url_for('dashboard') }}"
             class="nav-link {% if active_page == 'dashboard' %}fw-semibold{% endif %}">
            Dashboard
          </a>
        </li>
        <li class="nav-item">
          <a href="{{ url_for('contacts') }}"
             class="nav-link {% if active_page == 'contacts' %}fw-semibold{% endif %}">
            Contacts
          </a>
        </li>
        <li class="nav-item">
          <a href="{{ url_for('followups') }}"
             class="nav-link {% if active_page == 'followups' %}fw-semibold{% endif %}">
            Follow Up Dashboard
          </a>
        </li>
        <li class="nav-item">
          <a href="{{ url_for('followups_ics') }}"
             class="nav-link"
             target="_blank">
            Calendar Feed
          </a>
        </li>
      </ul>
    </div>
  </div>
</nav>

<div class="container py-4">

    <div class="mb-3">
        <h2 class="mb-0">Seller Profile</h2>
        <div class="text-muted">
            {{ contact_name }}
            {% if contact_email %} · {{ contact_email }}{% endif %}
            {% if contact_phone %} · {{ contact_phone }}{% endif %}
        </div>
    </div>

    <div class="card card-edit">
        <div class="card-header">
            Seller Details
        </div>
        <div class="card-body bg-white">
            <form method="post">
                <div class="row g-3">

                    <div class="col-md-4">
                        <label class="form-label">Property Type</label>
                        <select name="property_type" class="form-select">
                            <option value="">Select...</option>
                            <option value="Residential"
                              {% if sp and sp['property_type'] == 'Residential' %}selected{% endif %}>
                              Residential
                            </option>
                            <option value="Commercial"
                              {% if sp and sp['property_type'] == 'Commercial' %}selected{% endif %}>
                              Commercial
                            </option>
                        </select>
                    </div>

                    <div class="col-md-4">
                        <label class="form-label">Timeframe</label>
                        <input name="timeframe" class="form-control"
                               placeholder="Next 3-6 months"
                               value="{{ sp['timeframe'] if sp else '' }}">
                    </div>

                    <div class="col-md-4">
                        <label class="form-label">Motivation</label>
                        <input name="motivation" class="form-control"
                               placeholder="Downsizing, relocating, estate, etc."
                               value="{{ sp['motivation'] if sp else '' }}">
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Estimated Price</label>
                        <input name="estimated_price" type="number" class="form-control"
                               value="{{ sp['estimated_price'] if sp and sp['estimated_price'] is not none else '' }}">
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Property Address</label>
                        <input name="property_address" class="form-control"
                               placeholder="123 Main St, Keyport NJ"
                               value="{{ sp['property_address'] if sp else '' }}">
                    </div>

                    <div class="col-12">
                        <label class="form-label">Condition / Notes</label>
                        <textarea name="condition_notes" class="form-control" rows="3"
                                  placeholder="Repairs, updates, known issues, etc.">{{ sp['condition_notes'] if sp else '' }}</textarea>
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Referral Source</label>
                        <input name="referral_source" class="form-control"
                               placeholder="Who sent them to you?"
                               value="{{ sp['referral_source'] if sp else '' }}">
                    </div>

                    <div class="col-12">
                        <label class="form-label">Additional Notes</label>
                        <textarea name="notes" class="form-control" rows="3">{{ sp['notes'] if sp else '' }}</textarea>
                    </div>

                    <div class="col-12 mt-4">
                        <h6 class="fw-bold mb-2">Professionals</h6>
                    </div>

                    <div class="col-md-4">
                        <label class="form-label">Attorney Name</label>
                        <input name="seller_attorney_name" class="form-control"
                               value="{{ sp['seller_attorney_name'] if sp else '' }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Attorney Email</label>
                        <input name="seller_attorney_email" class="form-control"
                               value="{{ sp['seller_attorney_email'] if sp else '' }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Attorney Phone</label>
                        <input name="seller_attorney_phone" class="form-control"
                               value="{{ sp['seller_attorney_phone'] if sp else '' }}">
                    </div>
                    <div class="col-12">
                        <div class="form-check">
                            <input class="form-check-input"
                                   type="checkbox"
                                   name="seller_attorney_referred"
                                   id="seller_attorney_referred"
                                   {% if sp and sp['seller_attorney_referred'] %}checked{% endif %}>
                            <label class="form-check-label" for="seller_attorney_referred">
                                Attorney referred by me
                            </label>
                        </div>
                    </div>

                    <div class="col-md-4">
                        <label class="form-label">Lender Name</label>
                        <input name="seller_lender_name" class="form-control"
                               value="{{ sp['seller_lender_name'] if sp else '' }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Lender Email</label>
                        <input name="seller_lender_email" class="form-control"
                               value="{{ sp['seller_lender_email'] if sp else '' }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Lender Phone</label>
                        <input name="seller_lender_phone" class="form-control"
                               value="{{ sp['seller_lender_phone'] if sp else '' }}">
                    </div>
                    <div class="col-12">
                        <div class="form-check">
                            <input class="form-check-input"
                                   type="checkbox"
                                   name="seller_lender_referred"
                                   id="seller_lender_referred"
                                   {% if sp and sp['seller_lender_referred'] %}checked{% endif %}>
                            <label class="form-check-label" for="seller_lender_referred">
                                Lender referred by me
                            </label>
                        </div>
                    </div>

                    <div class="col-md-4">
                        <label class="form-label">Home Inspector Name</label>
                        <input name="seller_inspector_name" class="form-control"
                               value="{{ sp['seller_inspector_name'] if sp else '' }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Home Inspector Email</label>
                        <input name="seller_inspector_email" class="form-control"
                               value="{{ sp['seller_inspector_email'] if sp else '' }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Home Inspector Phone</label>
                        <input name="seller_inspector_phone" class="form-control"
                               value="{{ sp['seller_inspector_phone'] if sp else '' }}">
                    </div>
                    <div class="col-12">
                        <div class="form-check">
                            <input class="form-check-input"
                                   type="checkbox"
                                   name="seller_inspector_referred"
                                   id="seller_inspector_referred"
                                   {% if sp and sp['seller_inspector_referred'] %}checked{% endif %}>
                            <label class="form-check-label" for="seller_inspector_referred">
                                Home inspector referred by me
                            </label>
                        </div>
                    </div>

                    <div class="col-12">
                        <label class="form-label">Other Professionals</label>
                        <textarea name="other_professionals"
                                  class="form-control"
                                  rows="2"
                                  placeholder="Title company, contractor, etc.">{{ sp['other_professionals'] if sp else '' }}</textarea>
                    </div>

                </div>
                <button class="btn btn-primary mt-3" type="submit">Save Seller Profile</button>
                <a href="{{ url_for('edit_contact', contact_id=contact_id) }}" class="btn btn-secondary mt-3">
                    Back to Contact
                </a>
            </form>
        </div>
    </div>

</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

FOLLOWUPS_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Ulysses CRM - Follow Ups</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet"
    >
    <style>
      body {
        background-color: #6eb8f9;
      }
      .card-followups .card-header {
        font-weight: 600;
      }
      @media (max-width: 576px) {
        .nav-pipe {
          display: none;
        }
      }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-md navbar-light bg-white shadow-sm border-bottom sticky-top">
  <div class="container-fluid py-2" style="font-size: 0.9rem;">
    
    <!-- Logo -->
    <a href="{{ url_for('dashboard') }}" class="navbar-brand d-flex align-items-center text-dark">
      <img
        src="{{ url_for('static', filename='ulysses-logo.svg') }}"
        alt="Ulysses CRM"
        style="height: 50px;"
        class="me-2"
      >
    </a>

    <!-- Hamburger button -->
    <button class="navbar-toggler" type="button"
            data-bs-toggle="collapse"
            data-bs-target="#mainNav"
            aria-controls="mainNav"
            aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>

    <!-- Collapsible nav links -->
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-0 ms-md-2">

        <li class="nav-item">
          <a href="{{ url_for('dashboard') }}"
             class="nav-link {% if active_page == 'dashboard' %}fw-semibold{% endif %}">
            Dashboard
          </a>
        </li>

        <li class="nav-item">
          <a href="{{ url_for('contacts') }}"
             class="nav-link {% if active_page == 'contacts' %}fw-semibold{% endif %}">
            Contacts
          </a>
        </li>

        <li class="nav-item">
          <a href="{{ url_for('followups') }}"
             class="nav-link {% if active_page == 'followups' %}fw-semibold{% endif %}">
            Follow Up Dashboard
          </a>
        </li>

        <li class="nav-item">
          <a href="{{ url_for('followups_ics') }}"
             class="nav-link"
             target="_blank">
            Calendar Feed
          </a>
        </li>

      </ul>
    </div>
  </div>
</nav>

<div class="container py-4">

    <h2 class="mb-1">Follow Up Dashboard</h2>
    <p class="text-muted">Today: {{ today }}</p>

    {% macro followup_table(rows) %}
        {% if rows and rows|length > 0 %}
            <div class="table-responsive">
                <table class="table table-sm table-striped mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Name</th>
                            <th>Date</th>
                            <th>Time</th>
                            <th>Stage</th>
                            <th>Priority</th>
                            <th>Area</th>
                            <th style="width: 140px;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                    {% for c in rows %}
                      <tr>
                        <td>
                          <a href="{{ url_for('edit_contact', contact_id=c['contact_id']) }}">
                            {% if c["first_name"] or c["last_name"] %}
                              {{ (c["first_name"] or "") ~ (" " if c["first_name"] and c["last_name"] else "") ~ (c["last_name"] or "") }}
                            {% else %}
                              {{ c["name"] or "Unnamed Contact" }}
                            {% endif %}
                          </a>
                        </td>
                      
                        <td>
                          {{ c["follow_up_due_at"] }}
                        </td>
                      
                        <td style="min-width: 320px;">
                          {% set ctx = c["notes"] or c["outcome"] or c["summary_clean"] %}
                          {% if ctx %}
                            <div class="small">{{ ctx }}</div>
                          {% else %}
                            <span class="text-muted small">No context yet</span>
                          {% endif %}
                        </td>
                      
                        <td>
                          <a href="{{ url_for('edit_engagement', engagement_id=c['engagement_id'], next=request.path) }}"
                             class="btn btn-sm btn-outline-primary">
                            Open
                          </a>
                        </td>
                      </tr>
                    {% endfor %}
                    </tbody>
                </table>
            </div>
        {% else %}
            <p class="mb-0 text-muted">Nothing here.</p>
        {% endif %}
    {% endmacro %}

    <!-- Overdue -->
    <div class="card card-followups mb-4">
        <div class="card-header bg-danger text-white">
            Overdue Follow Ups
        </div>
        <div class="card-body bg-white">
            {{ followup_table(overdue) }}
        </div>
    </div>

    <!-- Today -->
    <div class="card card-followups mb-4">
        <div class="card-header bg-warning">
            Today
        </div>
        <div class="card-body bg-white">
            {{ followup_table(today_list) }}
        </div>
    </div>

    <!-- Upcoming -->
    <div class="card card-followups mb-4">
        <div class="card-header bg-success text-white">
            Upcoming
        </div>
        <div class="card-body bg-white">
            {{ followup_table(upcoming) }}
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Ulysses CRM - Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet"
    >
    <style>
      body {
        background-color: #6eb8f9;
      }
      .card-followups .card-header {
        font-weight: 600;
      }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-md navbar-light bg-white shadow-sm border-bottom sticky-top">
  <div class="container-fluid py-2" style="font-size: 0.9rem;">
    
    <!-- Logo -->
    <a href="{{ url_for('dashboard') }}" class="navbar-brand d-flex align-items-center text-dark">
      <img
        src="{{ url_for('static', filename='ulysses-logo.svg') }}"
        alt="Ulysses CRM"
        style="height: 50px;"
        class="me-2"
      >
    </a>

    <!-- Hamburger button -->
    <button class="navbar-toggler" type="button"
            data-bs-toggle="collapse"
            data-bs-target="#mainNav"
            aria-controls="mainNav"
            aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>

    <!-- Collapsible nav links -->
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-0 ms-md-2">

        <li class="nav-item">
          <a href="{{ url_for('dashboard') }}"
             class="nav-link {% if active_page == 'dashboard' %}fw-semibold{% endif %}">
            Dashboard
          </a>
        </li>

        <li class="nav-item">
          <a href="{{ url_for('contacts') }}"
             class="nav-link {% if active_page == 'contacts' %}fw-semibold{% endif %}">
            Contacts
          </a>
        </li>

        <li class="nav-item">
          <a href="{{ url_for('followups') }}"
             class="nav-link {% if active_page == 'followups' %}fw-semibold{% endif %}">
            Follow Up Dashboard
          </a>
        </li>

        <li class="nav-item">
          <a href="{{ url_for('followups_ics') }}"
             class="nav-link"
             target="_blank">
            Calendar Feed
          </a>
        </li>

      </ul>
    </div>
  </div>
</nav>

<div class="container py-4">

    <h2 class="mb-1">Dashboard</h2>
    <p class="text-muted">Today: {{ today }}</p>

    <!-- Summary cards -->
    <div class="row g-3 mb-4">
        <div class="col-md-3 col-6">
            <div class="card text-center">
                <div class="card-body">
                    <div class="text-muted small">Overdue Follow Ups</div>
                    <div class="fs-4 fw-bold">{{ overdue|length }}</div>
                </div>
            </div>
        </div>
        <div class="col-md-3 col-6">
            <div class="card text-center">
                <div class="card-body">
                    <div class="text-muted small">Today</div>
                    <div class="fs-4 fw-bold">{{ today_list|length }}</div>
                </div>
            </div>
        </div>
        <div class="col-md-3 col-6">
            <div class="card text-center">
                <div class="card-body">
                    <div class="text-muted small">Upcoming</div>
                    <div class="fs-4 fw-bold">{{ upcoming|length }}</div>
                </div>
            </div>
        </div>
        <div class="col-md-3 col-6">
            <div class="card text-center">
                <div class="card-body">
                    <div class="text-muted small">Total Contacts</div>
                    <div class="fs-4 fw-bold">{{ total_contacts }}</div>
                </div>
            </div>
        </div>
    </div>

    {% macro followup_table(rows) %}
        {% if rows and rows|length > 0 %}
            <div class="table-responsive">
                <table class="table table-sm table-striped mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Name</th>
                            <th>Date</th>
                            <th>Time</th>
                            <th>Stage</th>
                            <th>Priority</th>
                            <th>Area</th>
                            <th style="width: 140px;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                    {% for c in rows %}
                        <tr>
                            <td>
                                <a href="{{ url_for('edit_contact', contact_id=c['id']) }}">
                                    {% if c["first_name"] or c["last_name"] %}
                                        {{ (c["first_name"] or "") ~ (" " if c["first_name"] and c["last_name"] else "") ~ (c["last_name"] or "") }}
                                    {% else %}
                                        {{ c["name"] }}
                                    {% endif %}
                                </a>
                            </td>
                            <td>{{ c["next_follow_up"] or "" }}</td>
                            <td>{{ c["next_follow_up_time"] or "" }}</td>
                            <td>{{ c["pipeline_stage"] or "" }}</td>
                            <td>{{ c["priority"] or "" }}</td>
                            <td>{{ c["target_area"] or "" }}</td>
                            <td>
                                <a href="{{ url_for('edit_contact', contact_id=c['id']) }}"
                                   class="btn btn-sm btn-outline-primary">
                                   Open
                                </a>
                            </td>
                        </tr>
                    {% endfor %}
                    </tbody>
                </table>
            </div>
        {% else %}
            <p class="mb-0 text-muted">Nothing here.</p>
        {% endif %}
    {% endmacro %}

    <!-- Overdue -->
    <div class="card card-followups mb-4">
        <div class="card-header bg-danger text-white">
            Overdue Follow Ups
        </div>
        <div class="card-body bg-white">
            {{ followup_table(overdue) }}
        </div>
    </div>

    <!-- Today -->
    <div class="card card-followups mb-4">
        <div class="card-header bg-warning">
            Today
        </div>
        <div class="card-body bg-white">
            {{ followup_table(today_list) }}
        </div>
    </div>

    <!-- Upcoming -->
    <div class="card card-followups mb-4">
        <div class="card-header bg-success text-white">
            Upcoming
        </div>
        <div class="card-body bg-white">
            {{ followup_table(upcoming) }}
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Ulysses CRM - Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet"
    >
    <style>
      body { background-color: #6eb8f9; }
      .login-card {
        max-width: 420px;
        margin: 80px auto;
      }
    </style>
</head>
<body>
<div class="container">
  <div class="card login-card shadow-sm">
    <div class="card-header fw-semibold">
      Ulysses CRM Login
    </div>
    <div class="card-body bg-white">
      {% if error %}
        <div class="alert alert-danger py-2">{{ error }}</div>
      {% endif %}
      <form method="post">
        <div class="mb-3">
          <label class="form-label">Username</label>
          <input name="username" class="form-control" autofocus>
        </div>
        <div class="mb-3">
          <label class="form-label">Password</label>
          <input name="password" type="password" class="form-control">
        </div>
        <button class="btn btn-primary w-100" type="submit">Sign In</button>
      </form>
    </div>
  </div>
</div>
</body>
</html>
"""

LISTING_CHECKLIST_DEFAULTS = [
    ("mls_listing_agreement_signed", "MLS Listing Agreement Signed", 0),
    ("addendum_to_listing_agreement", "Addendum to Listing Agreement", 0),
    ("sellers_disclosure_signed", "Sellers Disclosure Signed", 0),
    ("lead_paint_disclosure", "Lead Paint Signed Disclosure (if applicable)", 0),
    ("input_form_completed", "Input Form Completed", 1),
    ("home_warranty_decision", "Home Warranty (yes or no)", 1),

    ("lockbox", "Lockbox", 1),
    ("suprakey_set_up", "Suprakey Set Up", 1),
    ("sign_on_property", "Sign on Property", 2),

    ("property_brochure_prepared", "Property Brochure Prepared", 2),
    ("feature_sheet", "Feature Sheet", 2),
    ("town_information", "Town Information", 2),

    ("post_on_vbd", "Post on VBD", 2),
    ("social_media", "Social Media", 2),
    ("list_trac", "List Trac", 2),
    ("reverse_prospecting", "Reverse Prospecting", 3),
    ("active_pipe_ecard", "Active Pipe E-Card", 3),
    ("just_listed_postcard", "Just Listed Postcard", 4),

    ("broker_open_house_scheduled", "Broker Open House Scheduled", 5),
    ("public_open_house_1", "Public Open House 1", 7),
    ("public_open_house_2", "Public Open House 2", 14),
    ("public_open_house_3", "Public Open House 3", None),

    ("dash_form", "Dash Form", 8),
]


def ensure_listing_checklist_initialized(user_id: int, contact_id: int) -> None:
    conn = get_db()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT archived_at FROM contacts WHERE id = %s AND user_id = %s",
            (contact_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            return
        if row["archived_at"] is not None:
            return

        cur.execute(
            "SELECT 1 FROM listing_checklist_items WHERE contact_id = %s LIMIT 1",
            (contact_id,),
        )
        if cur.fetchone():
            return

        today = date.today()
        rows = []
        for item_key, label, offset in LISTING_CHECKLIST_DEFAULTS:
            due = today + timedelta(days=offset) if isinstance(offset, int) else None
            rows.append((contact_id, item_key, label, due))

        cur.executemany(
            """
            INSERT INTO listing_checklist_items (contact_id, item_key, label, due_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (contact_id, item_key) DO NOTHING
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()

def get_listing_checklist(contact_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, item_key, label, due_date, is_complete
        FROM listing_checklist_items
        WHERE contact_id = %s
        ORDER BY
          CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
          due_date ASC,
          label ASC
        """,
        (contact_id,)
    )
    rows = cur.fetchall()
    conn.close()
    total = len(rows)
    complete = sum(1 for r in rows if r["is_complete"])
    return rows, complete, total

def _ics_escape(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace("\r\n", "\\n").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")

def build_ics_event(title, description, start_dt, tzid="America/New_York", duration_minutes=15, uid=None):
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    dtstart = start_dt.strftime("%Y%m%dT%H%M%S")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Ulysses CRM//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{_ics_escape(uid)}",
        f"DTSTAMP:{dtstamp}",
        f"SUMMARY:{_ics_escape(title)}",
    ]

    if description:
        lines.append(f"DESCRIPTION:{_ics_escape(description)}")

    lines.append(f"DTSTART;TZID={tzid}:{dtstart}")
    lines.append(f"DURATION:PT{int(duration_minutes)}M")
    lines.append("STATUS:CONFIRMED")
    lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")

    return "\r\n".join(lines) + "\r\n"


def is_safe_url(target: str) -> bool:
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        email = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""

        conn = None
        try:
            conn = get_db()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT id, email, password_hash, first_name, last_name, role, is_active
                FROM users
                WHERE email = %s AND is_active = TRUE
                LIMIT 1;
                """,
                (email,),
            )
            row = cur.fetchone()

            if row and check_password_hash(row["password_hash"], password):
                login_user(User(row))

                cur.execute(
                    "UPDATE users SET last_login_at = NOW() WHERE id = %s;",
                    (row["id"],),
                )
                conn.commit()

                next_url = request.args.get("next")
                if not next_url or not is_safe_url(next_url):
                    next_url = url_for("dashboard")
                return redirect(next_url)

            error = "Invalid username or password"
        finally:
            if conn:
                conn.close()

    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    today = date.today()
    today_str = today.isoformat()

    ACTIVE_DAYS = 30
    UPCOMING_DAYS = 14

    # Dashboard paging (Phase 6c)
    DASH_PAGE_SIZE = 50

    def _safe_int(v, default=1):
        try:
            n = int(v)
            return n if n >= 1 else default
        except Exception:
            return default

    ac_page = _safe_int(request.args.get("ac_page"), 1)
    ac_offset = (ac_page - 1) * DASH_PAGE_SIZE

    def _nf_to_date(nf):
        if not nf:
            return None
        if isinstance(nf, date):
            return nf
        try:
            return date.fromisoformat(str(nf))
        except Exception:
            return None

    conn = get_db()
    cur = conn.cursor()

    # Initialize to avoid any accidental UnboundLocalError if code moves later
    followup_rows = []
    followups_overdue = []
    followups_upcoming = []
    snapshot_followups_today = []
    snapshot_followups_overdue = []
    snapshot_tasks_overdue = []
    snapshot_tasks_today = []

    def has_column(table_name, column_name):
        cur.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = %s
            LIMIT 1
            """,
            (table_name, column_name),
        )
        return cur.fetchone() is not None

    # Detect multi-user columns (Render is missing contacts.user_id right now)
    contacts_has_user = has_column("contacts", "user_id")
    engagements_has_user = has_column("engagements", "user_id")
    buyer_has_user = has_column("buyer_profiles", "user_id")
    seller_has_user = has_column("seller_profiles", "user_id")

    # Detect contact_state (older prod/local may not have it yet)
    contacts_has_state = has_column("contacts", "contact_state")

    # Total contacts count
    if contacts_has_user:
        cur.execute("SELECT COUNT(*) AS cnt FROM contacts WHERE user_id = %s", (current_user.id,))
    else:
        cur.execute("SELECT COUNT(*) AS cnt FROM contacts")
    total_contacts = cur.fetchone()["cnt"]

    # Build reusable WHERE fragments
    contacts_scope_sql = "c.user_id = %s" if contacts_has_user else "TRUE"
    engagements_scope_sql = "AND e.user_id = %s" if engagements_has_user else ""
    buyer_scope_sql = "AND bp.user_id = %s" if buyer_has_user else ""
    seller_scope_sql = "AND sp.user_id = %s" if seller_has_user else ""
    contacts_state_sql = "AND c.contact_state = 'active'" if contacts_has_state else ""

    # Params helpers
    contacts_scope_params = (current_user.id,) if contacts_has_user else tuple()
    engagements_scope_params = (current_user.id,) if engagements_has_user else tuple()
    buyer_scope_params = (current_user.id,) if buyer_has_user else tuple()
    seller_scope_params = (current_user.id,) if seller_has_user else tuple()

    # Active contacts
    active_sql = f"""
        SELECT
            c.id AS contact_id,
            c.name,
            c.first_name,
            c.last_name,
            c.next_follow_up,
            c.next_follow_up_time,
            c.pipeline_stage,
            c.priority,
            c.target_area,

            le.occurred_at AS last_engagement_at,
            le.engagement_type AS last_engagement_type,
            le.outcome AS last_engagement_outcome,
            le.summary_clean AS last_engagement_summary,

            EXISTS (
                SELECT 1
                FROM buyer_profiles bp
                WHERE bp.contact_id = c.id
                {buyer_scope_sql}
            ) AS has_buyer_profile,

            EXISTS (
                SELECT 1
                FROM seller_profiles sp
                WHERE sp.contact_id = c.id
                {seller_scope_sql}
            ) AS has_seller_profile

        FROM contacts c

        LEFT JOIN LATERAL (
            SELECT e.occurred_at, e.engagement_type, e.outcome, e.summary_clean
            FROM engagements e
            WHERE e.contact_id = c.id
            {engagements_scope_sql}
            ORDER BY e.occurred_at DESC NULLS LAST, e.id DESC
            LIMIT 1
        ) le ON TRUE

        WHERE {contacts_scope_sql}
          AND c.archived_at IS NULL
          {contacts_state_sql}
          AND (
              (le.occurred_at IS NOT NULL AND le.occurred_at >= (NOW() - INTERVAL %s))
              OR c.next_follow_up IS NOT NULL
              OR EXISTS (
                  SELECT 1 FROM buyer_profiles bp
                  WHERE bp.contact_id = c.id
                  {buyer_scope_sql}
              )
              OR EXISTS (
                  SELECT 1 FROM seller_profiles sp
                  WHERE sp.contact_id = c.id
                  {seller_scope_sql}
              )
          )

        ORDER BY
          (CASE WHEN c.next_follow_up IS NULL THEN 1 ELSE 0 END),
          c.next_follow_up ASC NULLS LAST,
          le.occurred_at DESC NULLS LAST,
          c.name ASC

        LIMIT %s OFFSET %s
    """

    interval_param = f"{ACTIVE_DAYS} days"

    active_params = []
    active_params += list(contacts_scope_params)

    # buyer exists scopes (first)
    active_params += list(buyer_scope_params)
    # seller exists scopes (first)
    active_params += list(seller_scope_params)

    # lateral engagement scope
    active_params += list(engagements_scope_params)

    # interval and later EXISTS scopes
    active_params += [interval_param]
    active_params += list(buyer_scope_params)
    active_params += list(seller_scope_params)

    active_params += [DASH_PAGE_SIZE + 1, ac_offset]

    cur.execute(active_sql, tuple(active_params))
    active_rows = cur.fetchall()

    # Simple paging flags
    has_prev_active = ac_page > 1
    has_more_active = len(active_rows) > DASH_PAGE_SIZE

    # Trim to the real page size
    active_rows = active_rows[:DASH_PAGE_SIZE]

    # Active reasons badges
    now_dt = datetime.now(get_user_tz())
    active_contacts = []
    for r in active_rows:
        row = dict(r)
        badges = []

        last_at = row.get("last_engagement_at")
        if last_at:
            try:
                delta_days = (now_dt - last_at).days
                if delta_days <= ACTIVE_DAYS:
                    badges.append(f"Engaged {delta_days}d")
            except Exception:
                badges.append("Recent engagement")

        nf_date = _nf_to_date(row.get("next_follow_up"))
        nf_time = (row.get("next_follow_up_time") or "").strip()  # expected "HH:MM" 24h

        if nf_date:
            now_ny = datetime.now(get_user_tz())

            if nf_date < today:
                badges.append("Follow-up overdue")
            elif nf_date == today:
                if nf_time and ":" in nf_time:
                    try:
                        hh, mm = nf_time.split(":")
                        due_dt = datetime(
                            nf_date.year, nf_date.month, nf_date.day,
                            int(hh), int(mm), 0,
                            tzinfo=NY
                        )
                        if due_dt < now_ny:
                            badges.append("Follow-up overdue")
                        else:
                            badges.append("Follow-up today")
                    except Exception:
                        badges.append("Follow-up today")
                else:
                    badges.append("Follow-up today")
            else:
                badges.append("Follow-up scheduled")

        row["active_reasons"] = badges
        active_contacts.append(row)

    # Past Clients
    PAST_CLIENT_LIMIT = 25
    past_clients_sql = f"""
        SELECT
            c.id AS contact_id,
            c.name,
            c.first_name,
            c.last_name,
            c.next_follow_up,
            c.next_follow_up_time,
            c.priority,
            c.target_area,

            le.occurred_at AS last_engagement_at,
            le.engagement_type AS last_engagement_type,
            le.outcome AS last_engagement_outcome,
            le.summary_clean AS last_engagement_summary

        FROM contacts c

        LEFT JOIN LATERAL (
            SELECT e.occurred_at, e.engagement_type, e.outcome, e.summary_clean
            FROM engagements e
            WHERE e.contact_id = c.id
            {engagements_scope_sql}
            ORDER BY e.occurred_at DESC NULLS LAST, e.id DESC
            LIMIT 1
        ) le ON TRUE

        WHERE {contacts_scope_sql}
          AND c.archived_at IS NULL
          {contacts_state_sql}
          AND c.pipeline_stage = %s

        ORDER BY
          (CASE WHEN c.next_follow_up IS NULL THEN 1 ELSE 0 END),
          c.next_follow_up ASC NULLS LAST,
          le.occurred_at DESC NULLS LAST,
          c.name ASC

        LIMIT %s
    """

    past_clients_params = []
    past_clients_params += list(contacts_scope_params)
    past_clients_params += list(engagements_scope_params)
    past_clients_params += ["Past Client / Relationship", PAST_CLIENT_LIMIT]

    cur.execute(past_clients_sql, tuple(past_clients_params))
    past_clients = cur.fetchall() or []

    # Recent engagements feed
    recent_sql = f"""
        SELECT *
        FROM (
            SELECT DISTINCT ON (e.contact_id)
                e.id,
                e.contact_id,
                COALESCE(
                    NULLIF(TRIM(c.name), ''),
                    NULLIF(TRIM(CONCAT_WS(' ', c.first_name, c.last_name)), ''),
                    '(Unnamed)'
                ) AS contact_name,
                c.pipeline_stage,
                e.engagement_type,
                e.occurred_at,
                e.outcome,
                e.summary_clean
            FROM engagements e
            JOIN contacts c ON c.id = e.contact_id
            WHERE {contacts_scope_sql}
              AND c.archived_at IS NULL
              {contacts_state_sql}
            {"AND e.user_id = %s" if engagements_has_user else ""}
            ORDER BY
                e.contact_id,
                e.occurred_at DESC NULLS LAST,
                e.id DESC
        ) t
        ORDER BY
            t.occurred_at DESC NULLS LAST,
            t.id DESC
        LIMIT 10
    """
    recent_params = []
    recent_params += list(contacts_scope_params)
    if engagements_has_user:
        recent_params += [current_user.id]

    cur.execute(recent_sql, tuple(recent_params))
    recent_engagements = cur.fetchall() or []

    # Follow-ups from engagements (source of truth)
    followups_sql = f"""
        SELECT
            e.id AS engagement_id,
            e.contact_id,
            COALESCE(
              NULLIF(TRIM(c.name), ''),
              NULLIF(TRIM(CONCAT_WS(' ', c.first_name, c.last_name)), ''),
              '(Unnamed)'
            ) AS contact_name,
            e.follow_up_due_at,

            le.occurred_at AS last_engagement_at,
            le.engagement_type AS last_engagement_type,
            le.outcome AS last_engagement_outcome,
            le.summary_clean AS last_engagement_summary

        FROM engagements e
        JOIN contacts c ON c.id = e.contact_id

        LEFT JOIN LATERAL (
            SELECT e2.occurred_at, e2.engagement_type, e2.outcome, e2.summary_clean
            FROM engagements e2
            WHERE e2.contact_id = c.id
              AND e2.user_id = %s
            ORDER BY e2.occurred_at DESC
            LIMIT 1
        ) le ON TRUE

        WHERE c.user_id = %s
          AND c.archived_at IS NULL
          {contacts_state_sql}
          AND e.user_id = %s
          AND e.requires_follow_up = TRUE
          AND e.follow_up_completed = FALSE
          AND e.follow_up_due_at IS NOT NULL

        ORDER BY e.follow_up_due_at ASC
    """
    cur.execute(followups_sql, (current_user.id, current_user.id, current_user.id))
    followup_rows = cur.fetchall() or []

    # Build follow-ups buckets
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=UPCOMING_DAYS)

    followups_overdue = []
    followups_upcoming = []

    for row in followup_rows:
        due = row.get("follow_up_due_at")
        if not due:
            continue
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)

        if due < now:
            followups_overdue.append(row)
        elif due <= cutoff:
            followups_upcoming.append(row)

    # Today's Snapshot: Follow-ups due today (NY date)
    today_ny = datetime.now(get_user_tz()).date()
    snapshot_followups_today = []

    for row in followup_rows:
        due = row.get("follow_up_due_at")
        if not due:
            continue
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        try:
            if due.astimezone(get_user_tz()).date() == today_ny:
                snapshot_followups_today.append(row)
        except Exception:
            pass

    def _clean_snippet(s, max_len=180):
        s = (s or "").strip()
        if not s:
            return ""
        s = " ".join(s.split())
        return s[:max_len] + ("…" if len(s) > max_len else "")
    
    def _followup_snippet(r):
        # Outcome first, then summary, then type
        return _clean_snippet(r.get("last_engagement_outcome")) or _clean_snippet(r.get("last_engagement_summary")) or _clean_snippet(r.get("last_engagement_type"))
    
    today_ny = datetime.now(get_user_tz()).date()
    
    def _overdue_days_from_due(due_dt):
        if not due_dt:
            return None
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)
        try:
            due_ny_date = due_dt.astimezone(get_user_tz()).date()
            return max(0, (today_ny - due_ny_date).days)
        except Exception:
            return None
    
    # Enrich snapshot followups (overdue + today)
    snapshot_followups_overdue_enriched = []
    for r in (followups_overdue or [])[:8]:
        rr = dict(r)
        rr["snap_status"] = "overdue"
        rr["overdue_days"] = _overdue_days_from_due(rr.get("follow_up_due_at"))
        rr["snippet"] = _followup_snippet(rr)
        snapshot_followups_overdue_enriched.append(rr)
    
    snapshot_followups_today_enriched = []
    for r in (snapshot_followups_today or [])[:8]:
        rr = dict(r)
        rr["snap_status"] = "today"
        rr["overdue_days"] = 0
        rr["snippet"] = _followup_snippet(rr)
        snapshot_followups_today_enriched.append(rr)
    
    snapshot_followups_overdue = snapshot_followups_overdue_enriched
    snapshot_followups_today = snapshot_followups_today_enriched

    # Today's Snapshot: Tasks (exact schema)
    cur.execute(
        """
        SELECT
          t.id AS task_id,
          t.title,
          t.status,
          COALESCE(t.due_at, (t.due_date::timestamp AT TIME ZONE 'America/New_York')) AS due_ts,
          t.due_at,
          t.due_date,
          t.snoozed_until,
          t.contact_id,
          t.description,
          COALESCE(
            NULLIF(TRIM(c.name), ''),
            NULLIF(TRIM(CONCAT_WS(' ', c.first_name, c.last_name)), ''),
            '(Unnamed)'
          ) AS contact_name
        FROM tasks t
        LEFT JOIN contacts c ON c.id = t.contact_id
        WHERE t.user_id = %s
          AND t.status NOT IN ('completed', 'canceled')
          AND (
            t.status <> 'snoozed'
            OR t.snoozed_until IS NULL
            OR t.snoozed_until <= NOW()
          )
          AND (t.due_at IS NOT NULL OR t.due_date IS NOT NULL)
          AND DATE(timezone('America/New_York', COALESCE(t.due_at, t.due_date::timestamp))) < %s
        ORDER BY due_ts ASC NULLS LAST
        LIMIT 8
        """,
        (current_user.id, today_ny),
    )
    snapshot_tasks_overdue = cur.fetchall() or []

    cur.execute(
        """
        SELECT
          t.id AS task_id,
          t.title,
          t.status,
          COALESCE(t.due_at, (t.due_date::timestamp AT TIME ZONE 'America/New_York')) AS due_ts,
          t.due_at,
          t.due_date,
          t.snoozed_until,
          t.contact_id,
          t.description,
          COALESCE(
            NULLIF(TRIM(c.name), ''),
            NULLIF(TRIM(CONCAT_WS(' ', c.first_name, c.last_name)), ''),
            '(Unnamed)'
          ) AS contact_name
        FROM tasks t
        LEFT JOIN contacts c ON c.id = t.contact_id
        WHERE t.user_id = %s
          AND t.status NOT IN ('completed', 'canceled')
          AND (
            t.status <> 'snoozed'
            OR t.snoozed_until IS NULL
            OR t.snoozed_until <= NOW()
          )
          AND (t.due_at IS NOT NULL OR t.due_date IS NOT NULL)
          AND DATE(timezone('America/New_York', COALESCE(t.due_at, t.due_date::timestamp))) = %s
        ORDER BY due_ts ASC NULLS LAST
        LIMIT 8
        """,
        (current_user.id, today_ny),
    )
    snapshot_tasks_today = cur.fetchall() or []
    def _task_snippet(t):
        # For now, use title as fallback snippet and keep it compact.
        # If you later add t.description to the SELECT, use that first.
        return _clean_snippet(t.get("description")) or _clean_snippet(t.get("title"))
    
    def _task_due_dt(t):
        # Use due_ts which you already SELECT
        return t.get("due_ts") or t.get("due_at")
    
    snapshot_tasks_overdue_enriched = []
    for t in (snapshot_tasks_overdue or [])[:8]:
        tt = dict(t)
        tt["snap_status"] = "overdue"
        tt["overdue_days"] = _overdue_days_from_due(_task_due_dt(tt))
        tt["snippet"] = _task_snippet(tt)
        snapshot_tasks_overdue_enriched.append(tt)
    
    snapshot_tasks_today_enriched = []
    for t in (snapshot_tasks_today or [])[:8]:
        tt = dict(t)
        tt["snap_status"] = "today"
        tt["overdue_days"] = 0
        tt["snippet"] = _task_snippet(tt)
        snapshot_tasks_today_enriched.append(tt)
    
    snapshot_tasks_overdue = snapshot_tasks_overdue_enriched
    snapshot_tasks_today = snapshot_tasks_today_enriched


    # Active Transactions (Phase 8)
    # Define "active" as non-draft, non-terminal statuses.
    tx_status_label = dict(TRANSACTION_STATUSES)
    tx_badge_class = {
        "coming_soon": "bg-info text-dark",
        "active": "bg-primary",
        "attorney_review": "bg-warning text-dark",
        "pending_uc": "bg-success",
        "temp_off_market": "bg-secondary",
        "closed": "bg-dark",
        "withdrawn": "bg-secondary",
        "canceled": "bg-secondary",
        "expired": "bg-secondary",
        "draft": "bg-secondary",
    }

    tx_type_badge_class = {
        "buy": "bg-success",
        "sell": "bg-primary",
        "lease": "bg-info text-dark",
        "rent": "bg-warning text-dark",
        "unknown": "bg-secondary",
    }
    
    tx_open_statuses = [
        s for (s, _label) in TRANSACTION_STATUSES
        if s not in ("draft", "closed", "withdrawn", "canceled", "expired")
    ]

    # Total count (for card subtitle)
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM transactions t
        WHERE t.user_id = %s
          AND t.status = ANY(%s)
        """,
        (current_user.id, tx_open_statuses),
    )
    active_transactions_total = cur.fetchone()["cnt"]

    # Dashboard: contact picker for "Add Transaction" modal (Phase 8)
    cur.execute(
        """
        SELECT id,
               COALESCE(
                 NULLIF(TRIM(CONCAT_WS(' ', first_name, last_name)), ''),
                 NULLIF(name, ''),
                 'Unnamed Contact'
               ) AS display_name
        FROM contacts
        WHERE user_id = %s
          AND contact_state != 'archived'
        ORDER BY updated_at DESC NULLS LAST, id DESC
        LIMIT 50
        """,
        (current_user.id,),
    )
    dashboard_contact_picker = cur.fetchall()

    # Compact list (limit 8)
    cur.execute(
        """
        SELECT
            t.id,
            t.status,
            t.transaction_type,
            t.address,
            to_char(t.expected_close_date, 'YYYY-MM-DD') AS expected_close_date,
            t.updated_at,
            c.id AS contact_id,
            COALESCE(
                NULLIF(TRIM(CONCAT_WS(' ', c.first_name, c.last_name)), ''),
                NULLIF(c.name, ''),
                'Unnamed Contact'
            ) AS contact_name
        FROM transactions t
        JOIN contacts c ON c.id = t.contact_id
        WHERE t.user_id = %s
          AND t.status = ANY(%s)
        ORDER BY
            t.expected_close_date ASC NULLS LAST,
            t.updated_at DESC NULLS LAST,
            t.id DESC
        LIMIT 8
        """,
        (current_user.id, tx_open_statuses),
    )
    active_transactions = cur.fetchall()
    
    for t in active_transactions:
        raw_type = (t.get("transaction_type") or "").strip().lower()
    
        if raw_type in ("buy", "sell", "lease", "rent"):
            t["transaction_type_key"] = raw_type
            t["transaction_type_label"] = raw_type.title()
        else:
            t["transaction_type_key"] = "unknown"
            t["transaction_type_label"] = "Unknown"

    conn.close()

    return render_template(
        "dashboard.html",
        active_contacts=active_contacts,
        past_clients=past_clients,
        recent_engagements=recent_engagements,
        followups_overdue=followups_overdue,
        followups_upcoming=followups_upcoming,
        today=today_str,
        total_contacts=total_contacts,
        upcoming_days=UPCOMING_DAYS,
        active_days=ACTIVE_DAYS,
        active_page="dashboard",
        ac_page=ac_page,
        has_more_active=has_more_active,
        has_prev_active=has_prev_active,
        snapshot_followups_overdue=snapshot_followups_overdue,
        snapshot_followups_today=snapshot_followups_today,
        snapshot_tasks_overdue=snapshot_tasks_overdue,
        snapshot_tasks_today=snapshot_tasks_today,
        active_transactions=active_transactions,
        active_transactions_total=active_transactions_total,
        tx_status_label=tx_status_label,
        tx_badge_class=tx_badge_class,
        dashboard_contact_picker=dashboard_contact_picker,
        tx_type_badge_class = {
            "buy": "bg-success-subtle text-success-emphasis",
            "sell": "bg-primary-subtle text-primary-emphasis",
            "lease": "bg-info-subtle text-info-emphasis",
            "rent": "bg-warning-subtle text-warning-emphasis",
            "unknown": "bg-secondary-subtle text-secondary-emphasis",
        }
    )

@app.route("/admin/invites/new", methods=["GET", "POST"])
@login_required
@owner_required
def admin_new_invite():
    if request.method == "POST":
        invited_email = (request.form.get("invited_email") or "").strip().lower()
        role = (request.form.get("role") or "user").strip().lower()
        note = (request.form.get("note") or "").strip() or None

        if not invited_email:
            flash("Email is required.", "danger")
            return render_template("auth/admin_invite_new.html", active_page="admin")

        if role not in ("owner", "user"):
            flash("Role must be owner or user.", "danger")
            return render_template("auth/admin_invite_new.html", active_page="admin")

        # Fail loudly if misconfigured in production
        if not app.config.get("PUBLIC_BASE_URL"):
            raise RuntimeError(
                "PUBLIC_BASE_URL is not set. Set it to https://ulyssescrmpro.com in production."
            )

        conn = None
        try:
            conn = get_db()
            invite = create_user_invite(
                conn,
                invited_email=invited_email,
                role=role,
                invited_by_user_id=current_user.id,
                note=note,
            )

            invite_link = build_link(app.config["PUBLIC_BASE_URL"], "/accept-invite", invite["raw_token"])
            return render_template(
                "auth/admin_invite_created.html",
                invited_email=invite["invited_email"],
                role=invite["role"],
                expires_at=invite["expires_at"],
                invite_link=invite_link,
                active_page="admin",
            )

        except Exception as e:
            flash(f"Error creating invite: {e}", "danger")
            return render_template("auth/admin_invite_new.html", active_page="admin")

        finally:
            if conn:
                conn.close()

    return render_template("auth/admin_invite_new.html", active_page="admin")

@app.route("/accept-invite", methods=["GET", "POST"])
def accept_invite():
    token = (request.args.get("token") or request.form.get("token") or "").strip()
    if not token:
        flash("Invite token is missing.", "danger")
        return render_template("auth/accept_invite.html", token="")

    conn = None
    try:
        conn = get_db()
        invite = get_valid_invite_by_raw_token(conn, token)
        if not invite:
            flash("This invite link is invalid, expired, revoked, or already used.", "danger")
            return render_template("auth/accept_invite.html", token=token, invite=None)

        if request.method == "POST":
            pw1 = (request.form.get("password") or "").strip()
            pw2 = (request.form.get("password_confirm") or "").strip()
            first_name = (request.form.get("first_name") or "").strip()
            last_name = (request.form.get("last_name") or "").strip()

            # Agent branding
            agent_website = normalize_url(request.form.get("agent_website"))
            agent_phone = (request.form.get("agent_phone") or "").strip() or None
            title = (request.form.get("title") or "").strip() or None

            # Brokerage
            brokerage_name = (request.form.get("brokerage_name") or "").strip() or None

            # Accept either single address field OR split fields
            brokerage_address1 = (
                (request.form.get("brokerage_address1") or "").strip()
                or (request.form.get("brokerage_address") or "").strip()
                or None
            )
            brokerage_address2 = (request.form.get("brokerage_address2") or "").strip() or None

            brokerage_city = (request.form.get("brokerage_city") or "").strip() or None
            brokerage_state = (request.form.get("brokerage_state") or "").strip() or None
            brokerage_zip = (request.form.get("brokerage_zip") or "").strip() or None
            brokerage_phone = (request.form.get("brokerage_phone") or "").strip() or None
            brokerage_website = normalize_url(request.form.get("brokerage_website"))
            office_license_number = (request.form.get("office_license_number") or "").strip() or None

            if not pw1 or len(pw1) < 10:
                flash("Password must be at least 10 characters.", "danger")
                return render_template("auth/accept_invite.html", token=token, invite=invite)

            if pw1 != pw2:
                flash("Passwords do not match.", "danger")
                return render_template("auth/accept_invite.html", token=token, invite=invite)

            # If you want these required at account creation, enforce it here.
            # (Leaving as optional except brokerage_name because your form marks it required.)
            if not brokerage_name:
                flash("Brokerage Name is required.", "danger")
                return render_template("auth/accept_invite.html", token=token, invite=invite)

            email = invite["invited_email"]
            role = invite["role"]
            password_hash = generate_password_hash(pw1, method="pbkdf2:sha256")

            try:
                with conn.cursor() as cur:
                    # Ensure email is not already in use
                    cur.execute("SELECT id FROM users WHERE email = %s LIMIT 1;", (email,))
                    existing = cur.fetchone()
                    if existing:
                        flash("A user with this email already exists. Use password reset instead.", "danger")
                        return redirect(url_for("request_password_reset") + f"?email={email}")

                    # 1) Create user (includes new profile fields)
                    cur.execute(
                        """
                        INSERT INTO users (
                            email, password_hash,
                            first_name, last_name,
                            role, is_active, created_at,
                            title, agent_phone, agent_website
                        )
                        VALUES (%s, %s, %s, %s, %s, TRUE, NOW(), %s, %s, %s)
                        RETURNING id;
                        """,
                        (
                            email,
                            password_hash,
                            first_name or None,
                            last_name or None,
                            role,
                            title,
                            agent_phone,
                            agent_website,
                        ),
                    )
                    row = cur.fetchone()
                    if not row or "id" not in row:
                        raise RuntimeError("User insert failed: no id returned")
                    new_user_id = row["id"]

                    # 2) Upsert brokerage row (keyed by user_id)
                    has_any_brokerage = any(
                        [
                            brokerage_name,
                            brokerage_address1,
                            brokerage_address2,
                            brokerage_city,
                            brokerage_state,
                            brokerage_zip,
                            brokerage_phone,
                            brokerage_website,
                            office_license_number,
                        ]
                    )

                    if has_any_brokerage:
                        cur.execute(
                            """
                            INSERT INTO brokerages (
                                user_id,
                                brokerage_name,
                                address1,
                                address2,
                                city,
                                state,
                                zip,
                                brokerage_phone,
                                brokerage_website,
                                office_license_number,
                                created_at,
                                updated_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                            ON CONFLICT (user_id)
                            DO UPDATE SET
                                brokerage_name        = EXCLUDED.brokerage_name,
                                address1              = EXCLUDED.address1,
                                address2              = EXCLUDED.address2,
                                city                  = EXCLUDED.city,
                                state                 = EXCLUDED.state,
                                zip                   = EXCLUDED.zip,
                                brokerage_phone       = EXCLUDED.brokerage_phone,
                                brokerage_website     = EXCLUDED.brokerage_website,
                                office_license_number = EXCLUDED.office_license_number,
                                updated_at            = NOW();
                            """,
                            (
                                new_user_id,
                                brokerage_name,
                                brokerage_address1,
                                brokerage_address2,
                                brokerage_city,
                                brokerage_state,
                                brokerage_zip,
                                brokerage_phone,
                                brokerage_website,
                                office_license_number,
                            ),
                        )

                # 3) Consume invite (same transaction)
                consumed = consume_invite(conn, invite["id"], used_by_user_id=new_user_id)
                if not consumed:
                    raise RuntimeError("Invite could not be consumed")

                # Commit once after everything succeeded
                conn.commit()

            except Exception:
                # Ensure we don't leave a half-written user if something fails
                conn.rollback()
                raise

            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))

        # GET: show invite details and form
        return render_template("auth/accept_invite.html", token=token, invite=invite)

    finally:
        if conn:
            conn.close()

@app.route("/admin/invites")
@login_required
@owner_required
def admin_invites_list():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    invited_email,
                    role,
                    created_at,
                    expires_at
                FROM user_invites
                WHERE used_at IS NULL
                  AND revoked_at IS NULL
                  AND expires_at > NOW()
                ORDER BY created_at DESC;
                """
            )
            invites = cur.fetchall()

        return render_template(
            "auth/admin_invites_list.html",
            invites=invites,
            active_page="admin",
        )

    finally:
        if conn:
            conn.close()
            
@app.route("/admin/invites/<uuid:invite_id>/revoke", methods=["POST"])
@login_required
@owner_required
def admin_revoke_invite(invite_id):
    conn = None
    try:
        conn = get_db()
        revoked = revoke_invite(conn, invite_id)
        if revoked:
            flash("Invite revoked.", "success")
        else:
            flash("Invite could not be revoked.", "warning")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("admin_invites_list"))
    
@app.route("/admin/users")
@login_required
@owner_required
def admin_users_list():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    email,
                    first_name,
                    last_name,
                    role,
                    is_active,
                    created_at,
                    last_login_at
                FROM users
                ORDER BY created_at DESC;
                """
            )
            users = cur.fetchall()

        return render_template(
            "auth/admin_users_list.html",
            users=users,
            active_page="admin",
        )
    finally:
        if conn:
            conn.close()

@app.route("/admin")
@login_required
@owner_required
def admin_home():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM user_invites
                WHERE used_at IS NULL
                  AND revoked_at IS NULL
                  AND expires_at > NOW();
                """
            )
            invites_row = cur.fetchone()

            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM users
                WHERE is_active = TRUE;
                """
            )
            users_row = cur.fetchone()

        active_invites_count = int(invites_row["cnt"]) if invites_row else 0
        active_users_count = int(users_row["cnt"]) if users_row else 0

        return render_template(
            "auth/admin_home.html",
            active_invites_count=active_invites_count,
            active_users_count=active_users_count,
            active_page="admin",
        )
    finally:
        if conn:
            conn.close()
            
@app.route("/admin/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@owner_required
def admin_toggle_user_active(user_id):
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT id, is_active FROM users WHERE id = %s LIMIT 1;", (user_id,))
            row = cur.fetchone()

        if not row:
            flash("User not found.", "warning")
            return redirect(url_for("admin_users_list"))

        # Prevent owner from deactivating themselves (safety)
        if user_id == current_user.id:
            flash("You cannot deactivate your own account.", "warning")
            return redirect(url_for("admin_users_list"))

        new_state = not bool(row["is_active"])

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_active = %s WHERE id = %s;",
                (new_state, user_id),
            )

        conn.commit()

        flash("User status updated.", "success")
        return redirect(url_for("admin_users_list"))

    finally:
        if conn:
            conn.close()

@app.route("/password-reset/request", methods=["GET", "POST"])
def request_password_reset():
    preset_email = (request.args.get("email") or "").strip().lower()

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if not email:
            flash("Email is required.", "danger")
            return render_template("auth/password_reset_request.html", preset_email=preset_email)

        conn = None
        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE email = %s AND is_active = TRUE LIMIT 1;", (email,))
                row = cur.fetchone()

            # Do not reveal whether email exists (basic security hygiene)
            if not row:
                flash("If an account exists for that email, a reset link has been generated.", "success")
                return render_template("auth/password_reset_sent.html", reset_link=None)

            user_id = row["id"]
            request_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            request_user_agent = request.headers.get("User-Agent")

            # Optional but recommended: revoke prior outstanding resets
            revoke_all_password_resets_for_user(conn, user_id)

            reset = create_password_reset(
                conn,
                user_id=user_id,
                request_ip=request_ip,
                request_user_agent=request_user_agent,
            )
            reset_link  = build_link(app.config["PUBLIC_BASE_URL"], "/password-reset", reset["raw_token"], param_name="token")

            flash("If an account exists for that email, a reset link has been generated.", "success")
            return render_template("auth/password_reset_sent.html", reset_link=reset_link)

        finally:
            if conn:
                conn.close()

    return render_template("auth/password_reset_request.html", preset_email=preset_email)

@app.route("/password-reset", methods=["GET", "POST"])
def password_reset():
    token = (request.args.get("token") or request.form.get("token") or "").strip()
    if not token:
        flash("Reset token is missing.", "danger")
        return render_template("auth/password_reset.html", token="", valid=False, active_page=None)

    conn = None
    try:
        conn = get_db()

        reset = get_valid_password_reset_by_raw_token(conn, token)
        if not reset:
            flash("This reset link is invalid, expired, revoked, or already used.", "danger")
            return render_template("auth/password_reset.html", token=token, valid=False, active_page=None)

        if request.method == "POST":
            pw1 = (request.form.get("password") or "").strip()
            pw2 = (request.form.get("password_confirm") or "").strip()

            if not pw1 or len(pw1) < 10:
                flash("Password must be at least 10 characters.", "danger")
                return render_template("auth/password_reset.html", token=token, valid=True, active_page=None)

            if pw1 != pw2:
                flash("Passwords do not match.", "danger")
                return render_template("auth/password_reset.html", token=token, valid=True, active_page=None)

            password_hash = generate_password_hash(pw1, method="pbkdf2:sha256")

            try:
                with conn.cursor() as cur:
                    # 1) Update the user's password
                    cur.execute(
                        "UPDATE users SET password_hash = %s WHERE id = %s;",
                        (password_hash, reset["user_id"]),
                    )

                # 2) Consume this token (must succeed)
                consumed = consume_password_reset(conn, reset["id"])
                if not consumed:
                    conn.rollback()
                    flash("Reset token could not be consumed. Please request a new reset link.", "danger")
                    return redirect(url_for("request_password_reset"))

                # 3) Revoke any other outstanding reset tokens for this user
                revoke_all_password_resets_for_user(conn, reset["user_id"])

                conn.commit()

            except Exception:
                conn.rollback()
                app.logger.exception("Password reset failed")
                flash("Could not reset password. Please request a new reset link.", "danger")
                return redirect(url_for("request_password_reset"))

            flash("Password updated. Please log in.", "success")
            return redirect(url_for("login"))

        return render_template("auth/password_reset.html", token=token, valid=True, active_page=None)

    finally:
        if conn:
            conn.close()

@app.route("/contacts")
@login_required
def contacts():
    conn = get_db()
    cur = conn.cursor()

    # Lookup lists for Add Contact form
    lead_types = LEAD_TYPES
    pipeline_stages = PIPELINE_STAGES
    priorities = PRIORITIES
    sources = SOURCES
    today = date.today().isoformat()

    # Query params
    tab = (request.args.get("tab") or "all").lower()
    search = (request.args.get("q") or "").strip()
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    PAGE_SIZE = 10
    offset = (page - 1) * PAGE_SIZE

    show_archived = request.args.get("show_archived", "").strip() in ("1", "true", "yes", "on")

    # Query params
    tab = (request.args.get("tab") or "all").lower()
    search = (request.args.get("q") or "").strip()
    show_archived = request.args.get("show_archived", "").strip() in ("1", "true", "yes", "on")
    
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    
    PAGE_SIZE = 10
    offset = (page - 1) * PAGE_SIZE
    
    # Build WHERE clause parts
    where_clauses = []
    params = []
    
    # Always scope by user
    where_clauses.append("user_id = %s")
    params.append(current_user.id)
    
    # Phase 6a default: exclude archived contacts unless explicitly requested
    if not show_archived:
        where_clauses.append("archived_at IS NULL")
    
    # Tabs mapped to your existing schema
    if tab == "buyers":
        where_clauses.append("lead_type = %s")
        params.append("Buyer")
    elif tab == "sellers":
        where_clauses.append("lead_type = %s")
        params.append("Seller")
    elif tab == "leads":
        lead_stages = [
            "New lead",
            "Nurture",
            "Active",
            "Under contract",
            "Closed",
            "Lost",
        ]
        placeholders = ", ".join(["%s"] * len(lead_stages))
        where_clauses.append(f"pipeline_stage IN ({placeholders})")
        params.extend(lead_stages)
    elif tab == "past_clients":
        where_clauses.append("pipeline_stage = %s")
        params.append("Past Client / Relationship")
    elif tab == "imported":
        where_clauses.append("contact_state = %s")
        params.append("imported")
    
    # Search filter
    if search:
        where_clauses.append("""
            (
                COALESCE(name, '') ILIKE %s
                OR COALESCE(first_name, '') ILIKE %s
                OR COALESCE(last_name, '') ILIKE %s
                OR COALESCE(email, '') ILIKE %s
                OR COALESCE(phone, '') ILIKE %s
                OR COALESCE(notes, '') ILIKE %s
            )
        """)
        like_value = f"%{search}%"
        params.extend([like_value] * 6)

    # Default: hide imported contacts unless explicitly viewing the Imported tab
    if tab != "imported":
        where_clauses.append("contact_state <> 'imported'")

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
    else:
        where_sql = ""

    # Count total for pagination
    count_sql = f"SELECT COUNT(*) AS total FROM contacts {where_sql}"
    cur.execute(count_sql, tuple(params))
    row = cur.fetchone()
    total_rows = row["total"] if row and row["total"] is not None else 0
    total_pages = max(1, ceil(total_rows / PAGE_SIZE))

    # Clamp page if requested page is too high
    if page > total_pages:
        page = total_pages
        offset = (page - 1) * PAGE_SIZE

    # Main query for current page
    data_sql = f"""
        SELECT
            id,
            name,
            first_name,
            last_name,
            email,
            phone,
            lead_type,
            pipeline_stage,
            notes,
            archived_at,
            contact_state            
        FROM contacts
        {where_sql}
        ORDER BY last_name NULLS LAST, first_name NULLS LAST, id ASC
        LIMIT %s OFFSET %s
    """
    data_params = params + [PAGE_SIZE, offset]
    cur.execute(data_sql, tuple(data_params))
    contacts = cur.fetchall()
    conn.close()

    return render_template(
        "contacts.html",
        contacts=contacts,
        active_tab=tab,
        search_query=search,
        page=page,
        total_pages=total_pages,
        page_size=PAGE_SIZE,
        total_rows=total_rows,
        lead_types=lead_types,
        pipeline_stages=pipeline_stages,
        priorities=priorities,
        sources=sources,
        show_archived=show_archived,
        today=today,
    )

def parse_follow_up_time_from_form():
    hour24, minute = parse_12h_time_to_24h(
        request.form.get("next_follow_up_hour"),
        request.form.get("next_follow_up_minute"),
        request.form.get("next_follow_up_ampm"),
        default_hour=None,
        default_minute=None,
    )

    if hour24 is None or minute is None:
        return None

    return time(hour24, minute)

@app.route("/add", methods=["POST"])
@login_required
def add_contact():
    first_name = (request.form.get("first_name") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()

    full_name = f"{first_name} {last_name}".strip()

    next_follow_up_date = request.form.get("next_follow_up") or None
    next_follow_up_time = parse_follow_up_time_from_form()

    data = {
        "name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "email": (request.form.get("email") or "").strip(),
        "phone": normalize_phone(request.form.get("phone")),
        "lead_type": (request.form.get("lead_type") or "").strip(),
        "pipeline_stage": (request.form.get("pipeline_stage") or "").strip(),
        "priority": (request.form.get("priority") or "").strip(),
        "source": (request.form.get("source") or "").strip(),
        "price_min": parse_int_or_none(request.form.get("price_min")),
        "price_max": parse_int_or_none(request.form.get("price_max")),
        "target_area": (request.form.get("target_area") or "").strip(),
        "current_address": (request.form.get("current_address") or "").strip(),
        "current_city": (request.form.get("current_city") or "").strip(),
        "current_state": (request.form.get("current_state") or "").strip(),
        "current_zip": (request.form.get("current_zip") or "").strip(),
        "subject_address": (request.form.get("subject_address") or "").strip(),
        "subject_city": (request.form.get("subject_city") or "").strip(),
        "subject_state": (request.form.get("subject_state") or "").strip(),
        "subject_zip": (request.form.get("subject_zip") or "").strip(),
        "last_contacted": request.form.get("last_contacted") or None,
        "next_follow_up": next_follow_up_date,
        "next_follow_up_time": next_follow_up_time,
        "notes": (request.form.get("notes") or "").strip(),
    }

    if not data["name"]:
        return redirect(url_for("contacts"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO contacts (
            user_id,
            name, email, phone, lead_type, pipeline_stage, price_min, price_max,
            target_area, source, priority, last_contacted, next_follow_up, next_follow_up_time, notes,
            first_name, last_name,
            current_address, current_city, current_state, current_zip,
            subject_address, subject_city, subject_state, subject_zip
        )
        VALUES (%s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s)
        RETURNING id
        """,
        (
            current_user.id,
            data["name"],
            data["email"],
            data["phone"],
            data["lead_type"],
            data["pipeline_stage"],
            data["price_min"],
            data["price_max"],
            data["target_area"],
            data["source"],
            data["priority"],
            data["last_contacted"],
            data["next_follow_up"],
            data["next_follow_up_time"],
            data["notes"],
            data["first_name"],
            data["last_name"],
            data["current_address"],
            data["current_city"],
            data["current_state"],
            data["current_zip"],
            data["subject_address"],
            data["subject_city"],
            data["subject_state"],
            data["subject_zip"],
        ),
    )

    new_contact = cur.fetchone()
    new_id = new_contact["id"]

    conn.commit()
    conn.close()

    flash("Contact added.", "success")
    return redirect(url_for("edit_contact", contact_id=new_id))
  
@app.route("/edit/<int:contact_id>", methods=["GET", "POST"])
@login_required
def edit_contact(contact_id):
    conn = get_db()
    cur = conn.cursor()

    # -------------------------
    # POST: update contact
    # -------------------------
    if request.method == "POST":
        first_name = (request.form.get("first_name") or "").strip()
        last_name = (request.form.get("last_name") or "").strip()
        full_name = f"{first_name} {last_name}".strip()

        next_follow_up_date = request.form.get("next_follow_up") or None
        next_follow_up_time = parse_follow_up_time_from_form()

        data = {
            "name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "email": (request.form.get("email") or "").strip(),
            "phone": normalize_phone(request.form.get("phone")),
            "lead_type": (request.form.get("lead_type") or "").strip(),
            "pipeline_stage": (request.form.get("pipeline_stage") or "").strip(),
            "priority": (request.form.get("priority") or "").strip(),
            "source": (request.form.get("source") or "").strip(),
            "price_min": parse_int_or_none(request.form.get("price_min")),
            "price_max": parse_int_or_none(request.form.get("price_max")),
            "target_area": (request.form.get("target_area") or "").strip(),
            "current_address": (request.form.get("current_address") or "").strip(),
            "current_city": (request.form.get("current_city") or "").strip(),
            "current_state": (request.form.get("current_state") or "").strip(),
            "current_zip": (request.form.get("current_zip") or "").strip(),
            "subject_address": (request.form.get("subject_address") or "").strip(),
            "subject_city": (request.form.get("subject_city") or "").strip(),
            "subject_state": (request.form.get("subject_state") or "").strip(),
            "subject_zip": (request.form.get("subject_zip") or "").strip(),
            "last_contacted": request.form.get("last_contacted") or None,
            "next_follow_up": next_follow_up_date,
            "next_follow_up_time": next_follow_up_time,
            "notes": (request.form.get("notes") or "").strip(),
        }

        if not data["name"]:
            conn.close()
            return redirect(url_for("contacts"))

        cur.execute(
            """
            UPDATE contacts
            SET name = %s, email = %s, phone = %s, lead_type = %s, pipeline_stage = %s,
                price_min = %s, price_max = %s, target_area = %s, source = %s, priority = %s,
                last_contacted = %s, next_follow_up = %s, next_follow_up_time = %s, notes = %s,
                first_name = %s, last_name = %s,
                current_address = %s, current_city = %s, current_state = %s, current_zip = %s,
                subject_address = %s, subject_city = %s, subject_state = %s, subject_zip = %s
            WHERE id = %s AND user_id = %s
            """,
            (
                data["name"],
                data["email"],
                data["phone"],
                data["lead_type"],
                data["pipeline_stage"],
                data["price_min"],
                data["price_max"],
                data["target_area"],
                data["source"],
                data["priority"],
                data["last_contacted"],
                data["next_follow_up"],
                data["next_follow_up_time"],
                data["notes"],
                data["first_name"],
                data["last_name"],
                data["current_address"],
                data["current_city"],
                data["current_state"],
                data["current_zip"],
                data["subject_address"],
                data["subject_city"],
                data["subject_state"],
                data["subject_zip"],
                contact_id,
                current_user.id,
            ),
        )

        conn.commit()
        conn.close()
        return redirect(url_for("edit_contact", contact_id=contact_id, saved=1))

    # -------------------------
    # GET: load contact page
    # -------------------------
    cur.execute(
        """
        SELECT
          id,
          first_name,
          last_name,
          name,
          email,
          phone,
          lead_type,
          pipeline_stage,
          priority,
          source,
          current_address,
          current_city,
          current_state,
          current_zip,
          last_contacted,
          next_follow_up,
          next_follow_up_time,
          notes,
          archived_at,
          contact_state
        FROM contacts
        WHERE id = %s AND user_id = %s
        """,
        (contact_id, current_user.id),
    )
    contact = cur.fetchone()

    if not contact:
        conn.close()
        return "Contact not found", 404

    # Flags to indicate if this contact has buyer/seller profiles
    cur.execute(
        "SELECT id FROM buyer_profiles WHERE contact_id = %s LIMIT 1",
        (contact_id,),
    )
    has_buyer_profile = cur.fetchone() is not None
    
    cur.execute(
        "SELECT id FROM seller_profiles WHERE contact_id = %s LIMIT 1",
        (contact_id,),
    )
    has_seller_profile = cur.fetchone() is not None

    try:
        eng_page = int(request.args.get("eng_page", 1))
        if eng_page < 1:
            eng_page = 1
    except ValueError:
        eng_page = 1
    
    ENG_PAGE_SIZE = 10
    eng_offset = (eng_page - 1) * ENG_PAGE_SIZE

    # Engagements pagination (for Engagements tab)
    cur.execute(
        "SELECT COUNT(*) AS total FROM engagements WHERE contact_id = %s AND user_id = %s",
        (contact_id, current_user.id),
    )
    row = cur.fetchone()
    eng_total_rows = row["total"] if row and row.get("total") is not None else 0
    eng_total_pages = max(1, ceil(eng_total_rows / ENG_PAGE_SIZE))
    
    # Clamp page
    if eng_page > eng_total_pages:
        eng_page = eng_total_pages
        eng_offset = (eng_page - 1) * ENG_PAGE_SIZE
    
    # Fetch current page
    engagements = list_engagements_for_contact(
        conn,
        current_user.id,
        contact_id,
        limit=ENG_PAGE_SIZE,
        offset=eng_offset,
    )

    # Followups for this contact (from engagements)
    cur.execute(
        """
        SELECT
          e.id,
          e.engagement_type,
          e.follow_up_due_at,
          e.follow_up_completed,
          e.outcome,
          e.notes,
          e.summary_clean
        FROM engagements e
        JOIN contacts c ON c.id = e.contact_id
        WHERE e.user_id = %s
          AND e.contact_id = %s
          AND c.user_id = %s
          AND e.requires_follow_up = TRUE
          AND e.follow_up_completed = FALSE
        ORDER BY e.follow_up_due_at NULLS LAST, e.id ASC
        """,
        (current_user.id, contact_id, current_user.id),
    )
    followups_for_contact = cur.fetchall() or []
    
    def _parse_due_dt(val):
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, date):
            return datetime(val.year, val.month, val.day, 9, 0, 0)
    
        s = str(val).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s, fmt)
                # if date-only parses to midnight, leave for now
                return dt
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None
    
    now = datetime.now(get_user_tz())
    today = now.date()
    
    for f in followups_for_contact:
        due_dt = _parse_due_dt(f.get("follow_up_due_at"))
    
        if due_dt and due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=now.tzinfo)
    
        f["_due_dt"] = due_dt
    
        if not due_dt:
            status = "none"
        else:
            due_date = due_dt.date()
            if due_dt < now:
                status = "overdue"
            elif due_date == today:
                status = "today"
            elif (due_date - today).days <= 7:
                status = "soon"
            else:
                status = "later"
    
        f["_due_status"] = status

    # Pre-fill follow-up time selects if we have a stored time
    next_time_hour = None
    next_time_minute = None
    next_time_ampm = None
    t_str = contact.get("next_follow_up_time") if contact else None
    if t_str:
        try:
            hh, mm = t_str.split(":")
            hh24 = int(hh)
            if hh24 == 0:
                next_time_hour = 12
                next_time_ampm = "AM"
            elif 1 <= hh24 < 12:
                next_time_hour = hh24
                next_time_ampm = "AM"
            elif hh24 == 12:
                next_time_hour = 12
                next_time_ampm = "PM"
            else:
                next_time_hour = hh24 - 12
                next_time_ampm = "PM"
            next_time_minute = mm
        except Exception:
            next_time_hour = None
            next_time_minute = None
            next_time_ampm = None

    # Transactions (top 5)
    cur.execute(
        """
        SELECT
            id,
            status,
            transaction_type,
            address,
            list_price,
            offer_price,
            accepted_price,
            closed_price,
            expected_close_date,
            attorney_review_end_date,
            inspection_deadline,
            financing_contingency_date,
            appraisal_deadline,
            mortgage_commitment_date,
            updated_at
        FROM transactions
        WHERE contact_id = %s AND user_id = %s
        ORDER BY COALESCE(expected_close_date, updated_at) DESC, id DESC
        LIMIT 5
        """,
        (contact_id, current_user.id),
    )
    transactions = cur.fetchall()

    tx_id = request.args.get("tx_id", type=int)
    selected_tx = None
    if transactions:
        if tx_id:
            for t in transactions:
                if t["id"] == tx_id:
                    selected_tx = t
                    break
        if not selected_tx:
            selected_tx = transactions[0]

    # Next milestones (top 2)
    next_deadlines = []
    if selected_tx:
        cur.execute(
            """
            SELECT name, due_date
            FROM transaction_deadlines
            WHERE user_id = %s
              AND transaction_id = %s
              AND due_date IS NOT NULL
              AND is_done = FALSE
            ORDER BY due_date ASC
            """,
            (current_user.id, selected_tx["id"]),
        )
        db_deadlines = cur.fetchall() or []

        derived = []
        field_map = [
            ("Attorney review end", "attorney_review_end_date"),
            ("Inspection deadline", "inspection_deadline"),
            ("Financing contingency", "financing_contingency_date"),
            ("Appraisal deadline", "appraisal_deadline"),
            ("Mortgage commitment", "mortgage_commitment_date"),
            ("Expected close", "expected_close_date"),
        ]
        for label, field in field_map:
            dt = selected_tx.get(field)
            if dt:
                derived.append({"name": label, "due_date": dt})

        merged = db_deadlines + derived
        merged.sort(key=lambda x: x["due_date"] or date.max)
        next_deadlines = merged[:2]

    # Interactions split
    cur.execute(
        """
        SELECT *
        FROM interactions
        WHERE user_id = %s
          AND contact_id = %s
          AND is_completed = FALSE
        ORDER BY happened_at DESC NULLS LAST, id DESC
        """,
        (current_user.id, contact_id),
    )
    open_interactions = cur.fetchall()

    cur.execute(
        """
        SELECT *
        FROM interactions
        WHERE user_id = %s
          AND contact_id = %s
          AND is_completed = TRUE
        ORDER BY completed_at DESC NULLS LAST,
                 happened_at DESC NULLS LAST,
                 id DESC
        """,
        (current_user.id, contact_id),
    )
    completed_interactions = cur.fetchall()

    # Special dates
    cur.execute(
        """
        SELECT id, label, special_date, is_recurring, notes
        FROM contact_special_dates
        WHERE contact_id = %s
        ORDER BY special_date ASC, label ASC
        """,
        (contact_id,),
    )
    special_dates = cur.fetchall()

    associations = get_contact_associations(conn, current_user.id, contact_id)

    conn.close()

    return render_template(
        "edit_contact.html",
        c=contact,
        associations=associations,
        engagements=engagements,
        eng_page=eng_page,
        eng_total_pages=eng_total_pages,
        eng_total_rows=eng_total_rows,
        eng_page_size=ENG_PAGE_SIZE,
        followups_for_contact=followups_for_contact,
        special_dates=special_dates,
        open_interactions=open_interactions,
        completed_interactions=completed_interactions,
        lead_types=LEAD_TYPES,
        pipeline_stages=PIPELINE_STAGES,
        priorities=PRIORITIES,
        sources=SOURCES,
        today=date.today().isoformat(),
        next_time_hour=next_time_hour,
        next_time_minute=next_time_minute,
        next_time_ampm=next_time_ampm,
        active_page="contacts",
        has_buyer_profile=has_buyer_profile,
        has_seller_profile=has_seller_profile,
        selected_tx=selected_tx,
        transactions=transactions,
        transaction_statuses=TRANSACTION_STATUSES,
        next_deadlines=next_deadlines,
    )


@app.route("/contacts/search")
@login_required
def contacts_search():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])

    conn = get_db()
    try:
        cur = conn.cursor()
        like = f"%{q}%"
        cur.execute(
            """
            SELECT
              id,
              COALESCE(
                NULLIF(TRIM(name), ''),
                NULLIF(TRIM(CONCAT_WS(' ', first_name, last_name)), ''),
                '(Unnamed)'
              ) AS name,
              email,
              phone
            FROM contacts
            WHERE user_id = %s
              AND (
                name ILIKE %s OR
                CONCAT_WS(' ', first_name, last_name) ILIKE %s OR
                email ILIKE %s OR
                phone ILIKE %s
              )
            ORDER BY name ASC
            LIMIT 10
            """,
            (current_user.id, like, like, like, like),
        )
        return jsonify(cur.fetchall() or [])
    finally:
        conn.close()

@app.route("/contacts/<int:contact_id>/associations/add", methods=["POST"])
@login_required
def add_contact_association(contact_id):
    related_contact_id = int(request.form.get("related_contact_id") or 0)
    relationship_type = (request.form.get("relationship_type") or "").strip() or None
    next_url = request.form.get("next") or url_for("edit_contact", contact_id=contact_id)

    conn = get_db()
    cur = conn.cursor()

    # Validate ownership for parent
    cur.execute("SELECT id FROM contacts WHERE id = %s AND user_id = %s", (contact_id, current_user.id))
    if not cur.fetchone():
        conn.close()
        return "Contact not found", 404

    # Validate ownership for related
    cur.execute("SELECT id FROM contacts WHERE id = %s AND user_id = %s", (related_contact_id, current_user.id))
    if not cur.fetchone():
        conn.close()
        return "Related contact not found", 404

    try:
        create_contact_association(conn, current_user.id, contact_id, related_contact_id, relationship_type)
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return str(e), 400

    conn.close()
    return redirect(next_url)

@app.route("/contacts/<int:contact_id>/associations/create", methods=["POST"])
@login_required
def create_and_associate_contact(contact_id):

    first_name = (request.form.get("first_name") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()
    full_name = f"{first_name} {last_name}".strip()
    email = (request.form.get("email") or "").strip()
    phone = normalize_phone(request.form.get("phone") or request.form.get("related_phone"))
    relationship_type = (request.form.get("relationship_type") or "").strip() or None
    next_url = request.form.get("next") or url_for("edit_contact", contact_id=contact_id)

    if not full_name:
        return redirect(next_url)

    conn = get_db()
    cur = conn.cursor()

    # Validate parent ownership
    cur.execute("SELECT id FROM contacts WHERE id = %s AND user_id = %s", (contact_id, current_user.id))
    if not cur.fetchone():
        conn.close()
        return "Contact not found", 404

    try:

        cur.execute(
            """
            INSERT INTO contacts (user_id, name, first_name, last_name, email, phone)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (current_user.id, full_name, first_name, last_name, email, phone),
        )

        row = cur.fetchone()
        if not row or not row.get("id"):
            raise Exception("Failed to create contact")

        new_id = row["id"]

        create_contact_association(
            conn,
            current_user.id,
            contact_id,
            new_id,
            relationship_type,
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return redirect(next_url)

@app.route("/contacts/<int:contact_id>/associations/<int:assoc_id>/edit", methods=["POST"])
@login_required
def edit_contact_association(contact_id, assoc_id):
    next_post = (request.form.get("next") or "").strip() or url_for("edit_contact", contact_id=contact_id) + "#associations"

    relationship_type = (request.form.get("relationship_type") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    conn = get_db()
    try:
        ok = update_contact_association(
            conn,
            current_user.id,
            assoc_id,
            contact_id,
            relationship_type=relationship_type,
            notes=notes,
        )
        conn.commit()

        if ok:
            flash("Association updated.", "success")
        else:
            flash("Association not updated.", "warning")

    except Exception as e:
        conn.rollback()
        flash(f"Could not update association: {e}", "danger")
    finally:
        conn.close()

    return redirect(next_post)

@app.route("/contacts/<int:contact_id>/associations/<int:assoc_id>/update", methods=["POST"])
@login_required
def update_contact_association_route(contact_id, assoc_id):
    next_post = (request.form.get("next") or "").strip() or url_for("edit_contact", contact_id=contact_id) + "#associations"

    relationship_type = (request.form.get("relationship_type") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    conn = get_db()
    try:
        ok = update_contact_association(conn, current_user.id, assoc_id, relationship_type, notes)
        conn.commit()
        flash("Association updated.", "success" if ok else "warning")
    except Exception as e:
        conn.rollback()
        flash(f"Could not update association: {e}", "danger")
    finally:
        conn.close()

    return redirect(next_post)

@app.route("/contacts/<int:contact_id>/associations/<int:association_id>/edit")
@login_required
def contact_association_edit(contact_id, association_id):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verify master contact ownership
        cur.execute("SELECT id FROM contacts WHERE id = %s AND user_id = %s", (contact_id, current_user.id))
        if not cur.fetchone():
            abort(404)

        # Load association (must belong to this master contact)
        cur.execute(
            """
            SELECT
              ca.id,
              ca.contact_id_primary,
              ca.contact_id_related,
              ca.relationship,
              ca.notes,
              COALESCE(
                NULLIF(TRIM(c.name), ''),
                NULLIF(TRIM(CONCAT_WS(' ', c.first_name, c.last_name)), ''),
                '(Unnamed)'
              ) AS related_name
            FROM contact_associations ca
            JOIN contacts c ON c.id = ca.contact_id_related
            WHERE ca.id = %s
              AND ca.contact_id_primary = %s
              AND c.user_id = %s
            """,
            (association_id, contact_id, current_user.id),
        )
        assoc = cur.fetchone()
        if not assoc:
            abort(404)

        return render_template(
            "contacts/association_edit_modal.html",
            c_id=contact_id,
            assoc=assoc,
        )
    finally:
        conn.close()


@app.route("/contacts/<int:contact_id>/associations/<int:association_id>/update", methods=["POST"])
@login_required
def contact_association_update(contact_id, association_id):
    # Accept either field name (so you do not get stuck if templates differ)
    relationship_type = (
        (request.form.get("relationship_type") or "").strip()
        or (request.form.get("relationship") or "").strip()
        or None
    )
    notes = (request.form.get("notes") or "").strip() or None

    next_url = (
        (request.form.get("next") or "").strip()
        or (url_for("edit_contact", contact_id=contact_id) + "#associations")
    )

    conn = get_db()
    try:
        cur = conn.cursor()

        # Verify master contact ownership
        cur.execute(
            "SELECT id FROM contacts WHERE id = %s AND user_id = %s",
            (contact_id, current_user.id),
        )
        if not cur.fetchone():
            abort(404)

        # Update the association row (works regardless of which side is primary)
        cur.execute(
            """
            UPDATE contact_associations
            SET relationship_type = %s,
                notes = %s,
                updated_at = NOW()
            WHERE id = %s
              AND user_id = %s
              AND (contact_id_primary = %s OR contact_id_related = %s)
            """,
            (relationship_type or None, notes or None, assoc_id, current_user.id, contact_id, contact_id),
        )

        if cur.rowcount != 1:
            conn.rollback()
            abort(404)

        conn.commit()
        flash("Association updated.", "success")
        return redirect(next_url)

    except Exception as e:
        conn.rollback()
        flash(f"Could not update association: {e}", "danger")
        return redirect(next_url)
    finally:
        conn.close()

@app.route("/contacts/<int:contact_id>/associations/<int:assoc_id>/delete", methods=["POST"])
@login_required
def delete_contact_association(contact_id, assoc_id):
    next_url = request.form.get("next") or url_for("edit_contact", contact_id=contact_id)

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM contact_associations
        WHERE id = %s
          AND user_id = %s
          AND (contact_id_primary = %s OR contact_id_related = %s)
        """,
        (assoc_id, current_user.id, contact_id, contact_id),
    )

    conn.commit()
    conn.close()
    return redirect(next_url)

@app.route("/contacts/<int:contact_id>/set_state", methods=["POST"])
@login_required
def contact_set_state(contact_id):
    state = (request.form.get("contact_state") or "").strip()

    if state not in ("active", "inactive"):
        flash("Invalid contact state.", "warning")
        return redirect(url_for("contacts", tab="imported"))

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE contacts
            SET contact_state = %s,
                updated_at = NOW()
            WHERE id = %s
              AND user_id = %s
              AND archived_at IS NULL
            """,
            (state, contact_id, current_user.id),
        )
        conn.commit()
    finally:
        conn.close()

    flash("Contact updated.", "success")

    next_url = (request.form.get("next") or "").strip()
    if next_url:
        return redirect(next_url)

    return redirect(url_for("contacts", tab="imported"))

@app.route("/engagements/search")
@login_required
def engagements_search():
    q = (request.args.get("q") or "").strip()
    contact_id_raw = (request.args.get("contact_id") or "").strip()

    # Contact required for this UX
    if not contact_id_raw:
        return jsonify([])

    try:
        contact_id = int(contact_id_raw)
    except ValueError:
        return jsonify([])

    # Match the contact/transaction search behavior
    if len(q) < 2:
        return jsonify([])

    like = f"%{q}%"

    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # NOTE:
        # This assumes common columns: engagements.id, engagements.user_id, engagements.contact_id,
        # plus occurred_at, engagement_type, summary/notes.
        #
        # If your column names differ, tell me what they are and I’ll adjust in one pass.
        cur.execute(
            """
            SELECT
                id,
                occurred_at,
                engagement_type,
                summary_clean,
                notes
            FROM engagements
            WHERE user_id = %s
              AND contact_id = %s
              AND (
                engagement_type ILIKE %s
                OR COALESCE(summary_clean, '') ILIKE %s
                OR COALESCE(notes, '') ILIKE %s
              )
            ORDER BY occurred_at DESC, id DESC
            LIMIT 10
            """,
            (current_user.id, contact_id, like, like, like),
        )

        rows = cur.fetchall() or []
        out = []
        for r in rows:
            occurred = r.get("occurred_at")
        
            summary = (r.get("summary_clean") or "").strip()
            if not summary:
                summary = (r.get("notes") or "").strip()
        
            out.append(
                {
                    "id": r["id"],
                    "occurred_at": occurred.date().isoformat() if occurred else "",
                    "type_label": (r.get("engagement_type") or "").replace("_", " ").title(),
                    "summary": summary,
                }
            )

        return jsonify(out)

    finally:
        conn.close()

@app.route("/transactions/search")
@login_required
def transactions_search():
    q = (request.args.get("q") or "").strip()
    contact_id_raw = (request.args.get("contact_id") or "").strip()

    # For this UX, contact is required
    if not contact_id_raw:
        return jsonify([])

    try:
        contact_id = int(contact_id_raw)
    except ValueError:
        return jsonify([])

    # Match the Contact search behavior
    if len(q) < 2:
        return jsonify([])

    status_labels = dict(TRANSACTION_STATUSES)
    like = f"%{q}%"

    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT
                id,
                status,
                transaction_type,
                address,
                expected_close_date,
                updated_at
            FROM transactions
            WHERE contact_id = %s
              AND user_id = %s
              AND (
                address ILIKE %s
                OR status ILIKE %s
                OR transaction_type ILIKE %s
              )
            ORDER BY COALESCE(expected_close_date, updated_at) DESC, id DESC
            LIMIT 10
            """,
            (contact_id, current_user.id, like, like, like),
        )

        rows = cur.fetchall() or []
        out = []
        for r in rows:
            out.append(
                {
                    "id": r["id"],
                    "address": r.get("address") or "",
                    "status_label": status_labels.get(r.get("status") or "", r.get("status") or ""),
                    "transaction_type": r.get("transaction_type") or "",
                    "expected_close_date": (
                        r["expected_close_date"].isoformat()
                        if r.get("expected_close_date")
                        else ""
                    ),
                }
            )

        return jsonify(out)

    finally:
        conn.close()

@app.route("/transactions")
@login_required
def transactions():
    # Temporary placeholder until list UI is built
    return render_template(
        "transactions/index.html",
        active_page="transactions",
    )

@app.route("/contacts/<int:contact_id>/engagements/add", methods=["POST"])
@login_required
def add_engagement(contact_id):
    conn = get_db()

    engagement_type = (request.form.get("engagement_type") or "call").strip()
    outcome = (request.form.get("outcome") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None
    transcript_raw = (request.form.get("transcript_raw") or "").strip() or None
    summary_clean = (request.form.get("summary_clean") or "").strip() or None

    occurred_date = (request.form.get("occurred_date") or "").strip()
    time_hour = (request.form.get("time_hour") or "").strip()
    time_minute = (request.form.get("time_minute") or "").strip()
    time_ampm = (request.form.get("time_ampm") or "").strip()

    if occurred_date:
        dt = datetime.strptime(occurred_date, "%Y-%m-%d")

        if time_hour and time_minute and time_ampm:
            h = int(time_hour)
            m = int(time_minute)

            if time_ampm.upper() == "PM" and h != 12:
                h += 12
            if time_ampm.upper() == "AM" and h == 12:
                h = 0

            occurred_at = dt.replace(hour=h, minute=m)
        else:
            occurred_at = dt
    else:
        occurred_at = datetime.now()

    # Follow-up parsing (from split fields)
    requires_follow_up = (request.form.get("requires_follow_up") == "on")

    follow_up_due_at = None
    if requires_follow_up:
        fu_date = (request.form.get("follow_up_due_date") or "").strip()
        fu_hour = (request.form.get("follow_up_due_hour") or "").strip()
        fu_min = (request.form.get("follow_up_due_minute") or "").strip()
        fu_ampm = (request.form.get("follow_up_due_ampm") or "").strip().upper()

        if fu_date:
            if fu_hour and fu_min and fu_ampm:
                h = int(fu_hour)
                m = int(fu_min)

                if fu_ampm == "PM" and h != 12:
                    h += 12
                if fu_ampm == "AM" and h == 12:
                    h = 0

                follow_up_due_at = datetime.fromisoformat(fu_date).replace(
                    hour=h, minute=m, second=0, microsecond=0
                )
            else:
                # date provided but no time: store as midnight
                follow_up_due_at = datetime.fromisoformat(fu_date).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
        else:
            # checkbox checked but no date: treat as not a follow-up
            requires_follow_up = False
            follow_up_due_at = None

    insert_engagement(
        conn=conn,
        user_id=current_user.id,
        contact_id=contact_id,
        engagement_type=engagement_type,
        occurred_at=occurred_at,
        outcome=outcome,
        notes=notes,
        transcript_raw=transcript_raw,
        summary_clean=summary_clean,
        requires_follow_up=requires_follow_up,
        follow_up_due_at=follow_up_due_at,
    )

    conn.close()
    flash("Engagement added.", "success")
    return redirect(url_for("edit_contact", contact_id=contact_id, saved=1) + "#engagements")

@app.route("/engagements/<int:engagement_id>/delete", methods=["POST"])
@login_required
def remove_engagement(engagement_id):
    conn = get_db()
    deleted = delete_engagement(conn, current_user.id, engagement_id)

    if deleted:
        flash("Engagement deleted.", "success")
    else:
        flash("Engagement not found.", "warning")

    next_url = request.form.get("next") or url_for("contacts")
    return redirect(next_url)

@app.route("/engagements/<int:engagement_id>/followup/done", methods=["POST"])
@login_required
def engagement_followup_done(engagement_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE engagements
            SET
              follow_up_completed = true,
              follow_up_completed_at = now(),
              updated_at = now()
            WHERE id = %s AND user_id = %s
            """,
            (engagement_id, current_user.id),
        )

        if cur.rowcount == 0:
            conn.rollback()
            flash("Follow-up not found.", "warning")
        else:
            conn.commit()
            flash("Follow-up marked done.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Could not mark follow-up done: {e}", "danger")
    finally:
        conn.close()

    next_url = (request.form.get("next") or "").strip() or url_for("contacts")
    return redirect(next_url)

@app.route("/engagements/<int:engagement_id>/edit", methods=["GET", "POST"])
@login_required
def edit_engagement(engagement_id):
    conn = get_db()
    cur = conn.cursor()

    # Load engagement (must belong to current user)
    cur.execute(
        """
        SELECT
          id,
          user_id,
          contact_id,
          engagement_type,
          occurred_at,
          outcome,
          notes,
          transcript_raw,
          summary_clean,
          requires_follow_up,
          follow_up_due_at,
          follow_up_completed,
          follow_up_completed_at
        FROM engagements
        WHERE id = %s AND user_id = %s
        """,
        (engagement_id, current_user.id),
    )
    e = cur.fetchone()
    if not e:
        conn.close()
        flash("Engagement not found.", "danger")
        return redirect(url_for("contacts"))

    # Where to go after save or cancel
    next_param = (request.values.get("next") or "").strip()
    
    # Default to Engagements tab on the contact page
    default_next = url_for("edit_contact", contact_id=e["contact_id"]) + "#engagements"
    next_url = next_param or default_next

    # Return/next handling
    # next_url: a normal URL to go back to (e.g., /followups or /edit/123)
    # return_to: allows forcing the return destination (e.g., "contact")
    # return_tab: allows forcing a hash tab (e.g., "engagements")
    next_url = (request.args.get("next") or request.form.get("next") or "").strip()
    return_to = (request.args.get("return_to") or request.form.get("return_to") or "").strip()
    return_tab = (request.args.get("return_tab") or request.form.get("return_tab") or "").strip()

    if request.method == "POST":
        # Basic fields
        engagement_type = (request.form.get("engagement_type") or "call").strip()
        outcome = (request.form.get("outcome") or "").strip() or None
        notes = (request.form.get("notes") or "").strip() or None
        transcript_raw = (request.form.get("transcript_raw") or "").strip() or None
        summary_clean = (request.form.get("summary_clean") or "").strip() or None

        # Occurred_at parsing (datetime-local input is naive local time)
        occurred_raw = (request.form.get("occurred_at") or "").strip()
        
        if occurred_raw:
            try:
                occurred_at = datetime.fromisoformat(occurred_raw)
                # Keep naive wall-clock time (NY). Do not attach tzinfo.
                if occurred_at.tzinfo is not None:
                    occurred_at = occurred_at.replace(tzinfo=None)
            except ValueError:
                flash("Invalid engagement date/time.", "warning")
                occurred_at = e["occurred_at"]
        else:
            occurred_at = e["occurred_at"]
        
        # Follow-up parsing (datetime-local is naive local time)
        requires_follow_up = (request.form.get("requires_follow_up") == "on")
        follow_up_completed = (request.form.get("follow_up_completed") == "on")
        
        follow_up_due_at = None
        follow_up_completed_at = None
        
        if requires_follow_up:
            fu_raw = (request.form.get("follow_up_due_at") or "").strip()
        
            if fu_raw:
                try:
                    fu_dt = datetime.fromisoformat(fu_raw)
                    if fu_dt.tzinfo is not None:
                        fu_dt = fu_dt.replace(tzinfo=None)
                    follow_up_due_at = fu_dt
                except ValueError:
                    flash("Invalid follow-up date/time.", "warning")
                    requires_follow_up = False
                    follow_up_due_at = None
            else:
                requires_follow_up = False
                follow_up_due_at = None
        
            if follow_up_completed:
                # store naive NY wall-clock now
                follow_up_completed_at = datetime.now(NY).replace(tzinfo=None)
        else:
            follow_up_due_at = None
            follow_up_completed = False
            follow_up_completed_at = None

        # Persist
        cur.execute(
            """
            UPDATE engagements
            SET
              engagement_type = %s,
              occurred_at = %s,
              outcome = %s,
              notes = %s,
              transcript_raw = %s,
              summary_clean = %s,
              requires_follow_up = %s,
              follow_up_due_at = %s,
              follow_up_completed = %s,
              follow_up_completed_at = %s,
              updated_at = now()
            WHERE id = %s AND user_id = %s
            """,
            (
                engagement_type,
                occurred_at,
                outcome,
                notes,
                transcript_raw,
                summary_clean,
                requires_follow_up,
                follow_up_due_at,
                follow_up_completed,
                follow_up_completed_at,
                engagement_id,
                current_user.id,
            ),
        )
        conn.commit()
        conn.close()

        flash("Engagement updated.", "success")

        # Return logic (POST)
        # 1) If caller explicitly wants to go back to a specific contact tab
        if return_to == "contact":
            tab = (return_tab or "engagements").lstrip("#")  # allow "followups" or "#followups"
            return redirect(url_for("edit_contact", contact_id=e["contact_id"]) + f"#{tab}")

        # 2) If next_url was provided, honor it, and optionally enforce a tab hash
        if next_url:
            if return_tab:
                tab = return_tab.lstrip("#")
                if f"#{tab}" not in next_url:
                    return redirect(next_url + f"#{tab}")
            return redirect(next_url)

        # 3) Safe fallback
        return redirect(url_for("edit_contact", contact_id=e["contact_id"]) + "#engagements")

    # GET: render edit form
    conn.close()
    return render_template(
        "edit_engagement.html",
        e=e,
        next=next_url,
        next_url=next_url,
        return_to=return_to,
        return_tab=return_tab,
        active_page="contacts",
    )

# =========================================================
# Phase 5 (v0.11.0): Tasks
# Authoritative spec: Ulysses_CRM_Phase_5_Design_and_Scope_v2.md
# Local-first
# =========================================================


@app.route("/tasks")
@login_required
def tasks_list():
    raw_status = (request.args.get("status") or "").strip().lower()

    # Default behavior: /tasks shows OPEN tasks
    if raw_status == "":
        status = "open"
    # Explicit "all" means no status filter
    elif raw_status == "all":
        status = None
    else:
        status = raw_status

    if status and status not in TASK_STATUSES:
        flash("Invalid task status filter.", "warning")
        return redirect(url_for("tasks_list"))

    conn = get_db()
    try:
        cur = conn.cursor()
        tasks = list_tasks_for_user(cur, current_user.id, status=status)

        # Build contact_id -> display_name map for UI polish
        contact_ids = [t.get("contact_id") for t in tasks if t.get("contact_id")]
        contact_map = {}

        if contact_ids:
            contact_ids = sorted(set(contact_ids))
            cur.execute(
                """
                SELECT
                  id,
                  COALESCE(
                    NULLIF(TRIM(name), ''),
                    NULLIF(TRIM(CONCAT_WS(' ', first_name, last_name)), ''),
                    '(Unnamed)'
                  ) AS display_name
                FROM contacts
                WHERE user_id = %s
                  AND id = ANY(%s::int[])
                """,
                (current_user.id, contact_ids),
            )
            rows = cur.fetchall() or []
            contact_map = {r["id"]: r["display_name"] for r in rows}

        # Build professional_id -> name map for UI polish (multi-tenant safe)
        professional_map = {}
        professional_ids = [t.get("professional_id") for t in tasks if t.get("professional_id")]

        if professional_ids:
            professional_ids = sorted(set(professional_ids))
            cur.execute(
                """
                SELECT id, name
                FROM professionals
                WHERE user_id = %s
                  AND id = ANY(%s::int[])
                """,
                (current_user.id, professional_ids),
            )
            rows = cur.fetchall() or []
            professional_map = {r["id"]: r["name"] for r in rows}

        return render_template(
            "tasks/list.html",
            tasks=tasks,
            status=(status or "all"),
            statuses=TASK_STATUSES,
            contact_map=contact_map,
            professional_map=professional_map,
        )
    finally:
        conn.close()

@app.route("/tasks/new", methods=["GET", "POST"])
@login_required
def tasks_new():
    conn = get_db()
    cur = conn.cursor()

    # Prefill from querystring (coming from contact page button)
    prefill_contact_id = request.args.get("contact_id", type=int)
    next_url = (request.args.get("next") or "").strip() or None

    prefill_contact_name = ""
    if prefill_contact_id:
        cur.execute(
            """
            SELECT
              COALESCE(
                NULLIF(TRIM(name), ''),
                NULLIF(TRIM(CONCAT_WS(' ', first_name, last_name)), ''),
                '(Unnamed)'
              ) AS display_name
            FROM contacts
            WHERE user_id = %s AND id = %s
            """,
            (current_user.id, prefill_contact_id),
        )
        row = cur.fetchone()
        prefill_contact_name = (row["display_name"] if row else "") or ""

    if request.method == "POST":
        next_post = (request.form.get("next") or "").strip() or url_for("tasks_list")

        data = {
            "title": (request.form.get("title") or "").strip(),
            "description": (request.form.get("description") or "").strip() or None,
            "task_type": (request.form.get("task_type") or "").strip() or None,
            "priority": (request.form.get("priority") or "").strip() or None,
            "status": (request.form.get("status") or "open").strip(),
            "contact_id": request.form.get("contact_id", type=int),
            "transaction_id": request.form.get("transaction_id", type=int),
            "engagement_id": request.form.get("engagement_id", type=int),
            "professional_id": request.form.get("professional_id", type=int),
            "due_date": (request.form.get("due_date") or "").strip() or None,
            "due_at": (request.form.get("due_at") or "").strip() or None,
        }

        # Guardrails
        if not data["title"]:
            flash("Title is required.", "warning")
            return redirect(request.full_path)

        try:
            task_id = create_task(cur, current_user.id, data)
            conn.commit()
            flash("Task created.", "success")
            return redirect(next_post or url_for("tasks_view", task_id=task_id))
        except Exception as e:
            conn.rollback()
            flash(f"Could not create task: {e}", "danger")
        finally:
            conn.close()

    # GET
    modal = (request.args.get("modal") == "1") or (request.headers.get("X-Requested-With") == "XMLHttpRequest")

    transactions = []
    engagements = []

    if prefill_contact_id:
        # Recent transactions for this contact (limit 5)
        cur.execute(
            """
            SELECT
              id,
              COALESCE(
                NULLIF(TRIM(address), ''),
                NULLIF(TRIM(address_line), ''),
                ''
              ) AS address,
              transaction_type,
              status,
              expected_close_date
            FROM transactions
            WHERE user_id = %s AND contact_id = %s
            ORDER BY COALESCE(expected_close_date, updated_at) DESC, id DESC
            LIMIT 5
            """,
            (current_user.id, prefill_contact_id),
        )
        transactions = cur.fetchall()

        # Recent engagements for this contact (limit 15)
        cur.execute(
            """
            SELECT
              id,
              engagement_type,
              occurred_at,
              COALESCE(
                NULLIF(TRIM(summary_clean), ''),
                NULLIF(TRIM(notes), ''),
                ''
              ) AS summary_display
            FROM engagements
            WHERE user_id = %s AND contact_id = %s
            ORDER BY occurred_at DESC, id DESC
            LIMIT 15
            """,
            (current_user.id, prefill_contact_id),
        )
        engagements = cur.fetchall()

    conn.close()

    return render_template(
        "tasks/form_modal.html" if modal else "tasks/form.html",
        mode="new",
        task=None,
        statuses=TASK_STATUSES,
        next_url=next_url,
        prefill_contact_id=prefill_contact_id,
        prefill_contact_name=prefill_contact_name,
        transactions=transactions,
        engagements=engagements,
    )

@app.route("/tasks/modal/new")
@login_required
def tasks_modal_new():
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        prefill_contact_id = request.args.get("contact_id", type=int)
        next_url = (request.args.get("next") or "").strip() or None

        prefill_contact_name = ""
        if prefill_contact_id:
            cur.execute(
                """
                SELECT
                  COALESCE(
                    NULLIF(TRIM(name), ''),
                    NULLIF(TRIM(CONCAT_WS(' ', first_name, last_name)), ''),
                    '(Unnamed)'
                  ) AS display_name
                FROM contacts
                WHERE user_id = %s AND id = %s
                """,
                (current_user.id, prefill_contact_id),
            )
            row = cur.fetchone()
            prefill_contact_name = (row["display_name"] if row else "") or ""

        transactions = []
        engagements = []

        if prefill_contact_id:
            cur.execute(
                """
                SELECT
                    id,
                    status,
                    transaction_type,
                    address,
                    expected_close_date,
                    updated_at
                FROM transactions
                WHERE user_id = %s AND contact_id = %s
                ORDER BY COALESCE(expected_close_date, updated_at) DESC, id DESC
                LIMIT 25
                """,
                (current_user.id, prefill_contact_id),
            )
            transactions = cur.fetchall() or []

            cur.execute(
                """
                SELECT
                    id,
                    engagement_type,
                    occurred_at,
                    summary_clean,
                    notes
                FROM engagements
                WHERE user_id = %s AND contact_id = %s
                ORDER BY occurred_at DESC, id DESC
                LIMIT 25
                """,
                (current_user.id, prefill_contact_id),
            )
            engagements = cur.fetchall() or []

            for e in engagements:
                s = (e.get("summary_clean") or "").strip()
                if not s:
                    s = (e.get("notes") or "").strip()
                e["summary_display"] = (s[:80] + "...") if len(s) > 80 else s

        return render_template(
            "tasks/form_modal.html",
            mode="new",
            task=None,
            statuses=TASK_STATUSES,
            next_url=next_url,
            prefill_contact_id=prefill_contact_id,
            prefill_contact_name=prefill_contact_name,
            form_action=url_for("tasks_new"),
            transactions=transactions,
            engagements=engagements,
        )
    finally:
        conn.close()

@app.route("/tasks/<int:task_id>")
@login_required
def tasks_view(task_id):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        task = get_task(cur, current_user.id, task_id)
        if not task:
            abort(404)

        # Contact display name (existing)
        contact_name = None
        if task.get("contact_id"):
            cur.execute(
                """
                SELECT
                  COALESCE(
                    NULLIF(TRIM(name), ''),
                    NULLIF(TRIM(CONCAT_WS(' ', first_name, last_name)), ''),
                    '(Unnamed)'
                  ) AS display_name
                FROM contacts
                WHERE user_id = %s AND id = %s
                """,
                (current_user.id, task["contact_id"]),
            )
            row = cur.fetchone()
            contact_name = row["display_name"] if row else None

        # Contextual wildcard display data
        transaction = None
        transactions = []

        engagement = None
        engagements = []

        professional = None
        professionals = []
        # Professionals: always resolve selected professional (scoped)
        if task.get("professional_id"):
            cur.execute(
                """
                SELECT id, name, category, company
                FROM professionals
                WHERE id = %s AND user_id = %s
                """,
                (task["professional_id"], current_user.id),
            )
            professional = cur.fetchone()
        
        # Do not load a professionals list on the view page
        professionals = []

        # Transactions: if selected show 1, else show recent for contact
        if task.get("transaction_id"):
            cur.execute(
                """
                SELECT
                    id,
                    status,
                    transaction_type,
                    address,
                    expected_close_date,
                    updated_at
                FROM transactions
                WHERE id = %s AND user_id = %s
                """,
                (task["transaction_id"], current_user.id),
            )
            transaction = cur.fetchone()

        elif task.get("contact_id"):
            cur.execute(
                """
                SELECT
                    id,
                    status,
                    transaction_type,
                    address,
                    expected_close_date,
                    updated_at
                FROM transactions
                WHERE contact_id = %s AND user_id = %s
                ORDER BY COALESCE(expected_close_date, updated_at) DESC, id DESC
                LIMIT 10
                """,
                (task["contact_id"], current_user.id),
            )
            transactions = cur.fetchall() or []

        # Engagements: if selected show 1, else show recent for contact
        if task.get("engagement_id"):
            cur.execute(
                """
                SELECT
                    id,
                    engagement_type,
                    occurred_at,
                    summary_clean,
                    notes
                FROM engagements
                WHERE id = %s AND user_id = %s
                """,
                (task["engagement_id"], current_user.id),
            )
            engagement = cur.fetchone()
            if engagement:
                summary = (engagement.get("summary_clean") or "").strip()
                if not summary:
                    summary = (engagement.get("notes") or "").strip()
                engagement["summary_display"] = summary

        elif task.get("contact_id"):
            cur.execute(
                """
                SELECT
                    id,
                    engagement_type,
                    occurred_at,
                    summary_clean,
                    notes
                FROM engagements
                WHERE contact_id = %s AND user_id = %s
                ORDER BY occurred_at DESC, id DESC
                LIMIT 10
                """,
                (task["contact_id"], current_user.id),
            )
            engagements = cur.fetchall() or []
            for e in engagements:
                summary = (e.get("summary_clean") or "").strip()
                if not summary:
                    summary = (e.get("notes") or "").strip()
                e["summary_display"] = summary

        # Professionals: show selected only (no global list on task view)
        professional = None
        professionals = []
        
        if task.get("professional_id"):
            cur.execute(
                """
                SELECT id, name, category, company
                FROM professionals
                WHERE id = %s AND user_id = %s
                """,
                (task["professional_id"], current_user.id),
            )
            professional = cur.fetchone()
        
        # Never load a global professionals list on the task view page
        professionals = []

        return render_template(
            "tasks/view.html",
            task=task,
            contact_name=contact_name,
            transaction=transaction,
            transactions=transactions,
            engagement=engagement,
            engagements=engagements,
            professional=professional,
            professionals=professionals,
        )
    finally:
        conn.close()

@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def tasks_edit(task_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        task = get_task(cur, current_user.id, task_id)
        if not task:
            abort(404)

        # Contact display name for UI (avoid "Contact #X")
        contact_name = None
        if task.get("contact_id"):
            cur.execute(
                """
                SELECT
                  COALESCE(
                    NULLIF(TRIM(name), ''),
                    NULLIF(TRIM(CONCAT_WS(' ', first_name, last_name)), ''),
                    '(Unnamed)'
                  ) AS display_name
                FROM contacts
                WHERE user_id = %s AND id = %s
                """,
                (current_user.id, task["contact_id"]),
            )
            row = cur.fetchone()
            contact_name = row["display_name"] if row else None

        if request.method == "POST":
            form = request.form
            data = {
                "title": form.get("title"),
                "description": form.get("description") or None,
                "task_type": form.get("task_type") or None,
                "priority": form.get("priority") or None,
                "status": form.get("status") or "open",
                "contact_id": form.get("contact_id") or None,
                "transaction_id": form.get("transaction_id") or None,
                "engagement_id": form.get("engagement_id") or None,
                "professional_id": form.get("professional_id") or None,
                "due_date": form.get("due_date") or None,
                "due_at": form.get("due_at") or None,
            }

            try:
                update_task(cur, current_user.id, task_id, data)
                conn.commit()
                flash("Task updated.", "success")
                next_post = (request.form.get("next") or "").strip() or url_for("tasks_list")
                return redirect(next_post)

            except Exception as e:
                conn.rollback()
                flash(f"Could not update task: {e}", "danger")
        # Professional display name for UI (avoid "Professional #X")
        professional_name = None
        if task.get("professional_id"):
            cur.execute(
                """
                SELECT name
                FROM professionals
                WHERE user_id = %s AND id = %s
                """,
                (current_user.id, task["professional_id"]),
            )
            prow = cur.fetchone()
            professional_name = (prow["name"] if prow else None)

        return render_template(
            "tasks/form.html",
            mode="edit",
            task=task,
            statuses=TASK_STATUSES,
            contact_name=contact_name,
            professional_name=professional_name,
                        
        )
    finally:
        conn.close()

@app.route("/tasks/modal/<int:task_id>/edit")
@login_required
def tasks_modal_edit(task_id):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        task = get_task(cur, current_user.id, task_id)
        if not task:
            abort(404)

        transactions = []
        engagements = []

        contact_id = task.get("contact_id")
        contact_name = None
        if contact_id:
            cur.execute(
                """
                SELECT
                  COALESCE(
                    NULLIF(TRIM(name), ''),
                    NULLIF(TRIM(CONCAT_WS(' ', first_name, last_name)), ''),
                    '(Unnamed)'
                  ) AS display_name
                FROM contacts
                WHERE user_id = %s AND id = %s
                """,
                (current_user.id, contact_id),
            )
            row = cur.fetchone()
            contact_name = row["display_name"] if row else None

        if contact_id:
            cur.execute(
                """
                SELECT
                    id,
                    status,
                    transaction_type,
                    address,
                    expected_close_date,
                    updated_at
                FROM transactions
                WHERE user_id = %s AND contact_id = %s
                ORDER BY COALESCE(expected_close_date, updated_at) DESC, id DESC
                LIMIT 25
                """,
                (current_user.id, contact_id),
            )
            transactions = cur.fetchall() or []

            cur.execute(
                """
                SELECT
                    id,
                    engagement_type,
                    occurred_at,
                    summary_clean,
                    notes
                FROM engagements
                WHERE user_id = %s AND contact_id = %s
                ORDER BY occurred_at DESC, id DESC
                LIMIT 25
                """,
                (current_user.id, contact_id),
            )
            engagements = cur.fetchall() or []

            for e in engagements:
                s = (e.get("summary_clean") or "").strip()
                if not s:
                    s = (e.get("notes") or "").strip()
                e["summary_display"] = (s[:80] + "...") if len(s) > 80 else s
        # Professional display name for UI (avoid "Professional #X")
        professional_name = None
        if task.get("professional_id"):
            cur.execute(
                """
                SELECT name
                FROM professionals
                WHERE user_id = %s AND id = %s
                """,
                (current_user.id, task["professional_id"]),
            )
            prow = cur.fetchone()
            professional_name = (prow["name"] if prow else None)

        return render_template(
            "tasks/form_modal.html",
            mode="edit",
            task=task,
            statuses=TASK_STATUSES,
            next_url=(request.args.get("next") or "").strip() or None,
            prefill_contact_id=None,
            prefill_contact_name=contact_name or "",
            contact_name=contact_name,
            professional_name=professional_name,
            form_action=url_for("tasks_edit", task_id=task_id),
            transactions=transactions,
            engagements=engagements,
        )
    finally:
        conn.close()

# -------------------------
# Task actions (POST only)
# -------------------------

@app.route("/tasks/options")
@login_required
def tasks_options():
    contact_id = request.args.get("contact_id", type=int)
    if not contact_id:
        return jsonify({"transactions": [], "engagements": []})

    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT id, status, transaction_type, address, expected_close_date, updated_at
            FROM transactions
            WHERE user_id = %s AND contact_id = %s
            ORDER BY COALESCE(expected_close_date, updated_at) DESC, id DESC
            LIMIT 25
            """,
            (current_user.id, contact_id),
        )
        transactions = cur.fetchall() or []

        cur.execute(
            """
            SELECT id, engagement_type, occurred_at, summary_clean, notes
            FROM engagements
            WHERE user_id = %s AND contact_id = %s
            ORDER BY occurred_at DESC, id DESC
            LIMIT 25
            """,
            (current_user.id, contact_id),
        )
        engagements = cur.fetchall() or []

        out_eng = []
        for e in engagements:
            s = (e.get("summary_clean") or "").strip() or (e.get("notes") or "").strip()
            if len(s) > 80:
                s = s[:80] + "..."
            out_eng.append(
                {
                    "id": e["id"],
                    "engagement_type": e.get("engagement_type") or "",
                    "occurred_at": (e["occurred_at"].date().isoformat() if e.get("occurred_at") else ""),
                    "summary": s,
                }
            )

        out_tx = []
        for tx in transactions:
            out_tx.append(
                {
                    "id": tx["id"],
                    "address": tx.get("address") or "",
                    "transaction_type": tx.get("transaction_type") or "",
                    "status": tx.get("status") or "",
                    "expected_close_date": (tx["expected_close_date"].isoformat() if tx.get("expected_close_date") else ""),
                }
            )

        return jsonify({"transactions": out_tx, "engagements": out_eng})
    finally:
        conn.close()

@app.route("/tasks/<int:task_id>/complete", methods=["POST"])
@login_required
def tasks_complete(task_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        # verify ownership first
        task = get_task(cur, current_user.id, task_id)
        if not task:
            abort(404)

        complete_task(cur, current_user.id, task_id)
        conn.commit()
        flash("Task marked completed.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Could not complete task: {e}", "danger")
    finally:
        conn.close()

    return redirect(request.referrer or url_for("tasks_view", task_id=task_id))


@app.route("/tasks/<int:task_id>/snooze", methods=["POST"])
@login_required
def tasks_snooze(task_id):
    snoozed_until_str = (request.form.get("snoozed_until") or "").strip()
    if not snoozed_until_str:
        flash("Please provide a snooze date/time.", "warning")
        return redirect(request.referrer or url_for("tasks_view", task_id=task_id))

    # Accept HTML datetime-local like: 2025-12-30T18:30
    # We'll parse as naive local time and store as timestamptz; Postgres will interpret with server TZ.
    try:
        snoozed_until = datetime.fromisoformat(snoozed_until_str)
    except ValueError:
        flash("Invalid snooze date/time format.", "warning")
        return redirect(request.referrer or url_for("tasks_view", task_id=task_id))

    conn = get_db()
    try:
        cur = conn.cursor()
        task = get_task(cur, current_user.id, task_id)
        if not task:
            abort(404)

        snooze_task(cur, current_user.id, task_id, snoozed_until)
        conn.commit()
        flash("Task snoozed.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Could not snooze task: {e}", "danger")
    finally:
        conn.close()

    return redirect(request.referrer or url_for("tasks_view", task_id=task_id))


@app.route("/tasks/<int:task_id>/reopen", methods=["POST"])
@login_required
def tasks_reopen(task_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        reopen_task(cur, current_user.id, task_id)
        conn.commit()

        flash("Task reopened. Update details as needed.", "info")
        return redirect(url_for("tasks_edit", task_id=task_id))

    except Exception:
        conn.rollback()
        app.logger.exception("Task reopen failed")
        flash("Could not reopen task.", "danger")
        return redirect(url_for("tasks_view", task_id=task_id))

    finally:
        conn.close()

@app.route("/tasks/<int:task_id>/cancel", methods=["POST"])
@login_required
def tasks_cancel(task_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        task = get_task(cur, current_user.id, task_id)
        if not task:
            abort(404)

        cancel_task(cur, current_user.id, task_id)
        conn.commit()
        flash("Task canceled.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Could not cancel task: {e}", "danger")
    finally:
        conn.close()

    return redirect(request.referrer or url_for("tasks_view", task_id=task_id))

@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def tasks_delete(task_id):
    next_post = (request.form.get("next") or "").strip() or url_for("tasks_list")

    conn = get_db()
    try:
        cur = conn.cursor()

        # verify ownership first
        task = get_task(cur, current_user.id, task_id)
        if not task:
            abort(404)

        ok = delete_task(cur, current_user.id, task_id)
        conn.commit()

        if ok:
            flash("Task deleted.", "success")
        else:
            flash("Task not deleted.", "warning")

    except Exception as e:
        conn.rollback()
        flash(f"Could not delete task: {e}", "danger")
    finally:
        conn.close()

    return redirect(next_post)

@app.route("/add_interaction/<int:contact_id>", methods=["POST"])
@login_required
def add_interaction(contact_id):
    kind = (request.form.get("kind") or "").strip()
    happened_at = request.form.get("happened_at") or None
    notes = (request.form.get("notes") or "").strip()

    time_hour = (request.form.get("time_hour") or "").strip()
    time_minute = (request.form.get("time_minute") or "").strip()
    time_ampm = (request.form.get("time_ampm") or "").strip()

    time_of_day = None
    if time_hour and time_minute and time_ampm:
        time_of_day = f"{time_hour}:{time_minute} {time_ampm}"

    if not kind:
        return redirect(url_for("edit_contact", contact_id=contact_id))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO interactions (user_id, contact_id, kind, happened_at, time_of_day, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (current_user.id, contact_id, kind, happened_at, time_of_day, notes),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("edit_contact", contact_id=contact_id))


@app.route("/delete_interaction/<int:interaction_id>")
@login_required
def delete_interaction(interaction_id):
    conn = get_db()
    cur = conn.cursor()
    # Find which contact this interaction belongs to
    cur.execute(
        "SELECT contact_id FROM interactions WHERE id = %s AND user_id = %s",
        (interaction_id, current_user.id),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return redirect(url_for("contacts"))

    contact_id = row["contact_id"]

    # Delete the interaction
    cur.execute("DELETE FROM interactions WHERE id = %s", (interaction_id,))
    conn.commit()
    conn.close()

    # Go back to that contact's edit page
    return redirect(url_for("edit_contact", contact_id=contact_id))

@app.route("/add_related/<int:contact_id>", methods=["POST"])
@login_required
def add_related(contact_id):
    related_name = (request.form.get("related_name") or "").strip()
    relationship = (request.form.get("relationship") or "").strip()
    email = (request.form.get("related_email") or "").strip()
    phone = normalize_phone(request.form.get("phone") or request.form.get("related_phone"))
    notes = (request.form.get("related_notes") or "").strip()

    if not related_name:
        return redirect(url_for("edit_contact", contact_id=contact_id))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO related_contacts (contact_id, related_name, relationship, email, phone, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (contact_id, related_name, relationship, email, phone, notes),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("edit_contact", contact_id=contact_id))


@app.route("/delete_related/<int:related_id>")
@login_required
def delete_related(related_id):
    conn = get_db()
    cur = conn.cursor()

    # Find parent contact
    cur.execute(
        "SELECT contact_id FROM related_contacts WHERE id = %s",
        (related_id,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return redirect(url_for("contacts"))

    contact_id = row["contact_id"]

    # Delete associated-contact row
    cur.execute("DELETE FROM related_contacts WHERE id = %s", (related_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("edit_contact", contact_id=contact_id))

@app.route("/buyer/<int:contact_id>", methods=["GET", "POST"])
@login_required
def buyer_profile(contact_id):
    conn = get_db()
    cur = conn.cursor()

    # Load contact
    cur.execute("SELECT * FROM contacts WHERE id = %s AND user_id = %s", (contact_id, current_user.id))
    contact = cur.fetchone()
    if not contact:
        conn.close()
        return "Contact not found", 404

    # Load existing buyer profile (if any)
    cur.execute(
        """
        SELECT *
        FROM buyer_profiles
        WHERE contact_id = %s
        """,
        (contact_id,),
    )
    buyer_profile = cur.fetchone()

    # Phase 3.3: Transactions (buyer sheet)
    cur.execute(
        """
        SELECT
            id,
            status,
            transaction_type,
            address,
            list_price,
            offer_price,
            expected_close_date,
            updated_at
        FROM transactions
        WHERE contact_id = %s
          AND user_id = %s
          AND transaction_type = 'buy'
        ORDER BY COALESCE(expected_close_date, updated_at) DESC, id DESC
        LIMIT 10
        """,
        (contact_id, current_user.id),
    )
    buyer_transactions = cur.fetchall()

    # Handle form submissions
    if request.method == "POST":
        form_action = (request.form.get("form_action") or "").strip()

        # Branch 1: adding a subject property with Offer? status
        if form_action == "add_property":
            # Ensure a buyer_profile exists for this contact
            if not buyer_profile:
                cur.execute(
                    """
                    INSERT INTO buyer_profiles (contact_id)
                    VALUES (%s)
                    RETURNING *
                    """,
                    (contact_id,),
                )
                buyer_profile = cur.fetchone()

            address_line = (request.form.get("address_line") or "").strip()
            city = (request.form.get("city") or "").strip()
            state = (request.form.get("state") or "").strip()
            postal_code = (request.form.get("postal_code") or "").strip()
            offer_status = (request.form.get("offer_status") or "").strip()

            if address_line:
                cur.execute(
                    """
                    INSERT INTO buyer_properties (
                        buyer_profile_id,
                        address_line,
                        city,
                        state,
                        postal_code,
                        offer_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        buyer_profile["id"],
                        address_line,
                        city,
                        state,
                        postal_code,
                        offer_status,
                    ),
                )

            conn.commit()
            return redirect(url_for("buyer_profile", contact_id=contact_id))

        # Branch 2: saving the main buyer profile
        else:
            # Existing fields
            property_type = (request.form.get("property_type") or "").strip() or None
            timeframe = (request.form.get("timeframe") or "").strip() or None
            preapproval_status = (request.form.get("preapproval_status") or "").strip() or None
            lender_name = (request.form.get("lender_name") or "").strip() or None
            areas = (request.form.get("areas") or "").strip() or None
            property_types = (request.form.get("property_types") or "").strip() or None
            referral_source = (request.form.get("referral_source") or "").strip() or None
            notes = (request.form.get("notes") or "").strip() or None

            min_price = parse_int_or_none(request.form.get("min_price"))
            max_price = parse_int_or_none(request.form.get("max_price"))

            # Professionals fields (template fields)
            buyer_attorney_name = (request.form.get("buyer_attorney_name") or "").strip() or None
            buyer_attorney_email = (request.form.get("buyer_attorney_email") or "").strip() or None
            buyer_attorney_phone = (request.form.get("buyer_attorney_phone") or "").strip() or None
            buyer_attorney_referred = truthy_checkbox(request.form.get("buyer_attorney_referred"))

            buyer_lender_email = (request.form.get("buyer_lender_email") or "").strip() or None
            buyer_lender_phone = (request.form.get("buyer_lender_phone") or "").strip() or None
            buyer_lender_referred = truthy_checkbox(request.form.get("buyer_lender_referred"))

            buyer_inspector_name = (request.form.get("buyer_inspector_name") or "").strip() or None
            buyer_inspector_email = (request.form.get("buyer_inspector_email") or "").strip() or None
            buyer_inspector_phone = (request.form.get("buyer_inspector_phone") or "").strip() or None
            buyer_inspector_referred = truthy_checkbox(request.form.get("buyer_inspector_referred"))

            other_professionals = (request.form.get("other_professionals") or "").strip() or None

            # Checklist booleans
            cis_signed = truthy_checkbox(request.form.get("cis_signed"))
            buyer_agreement_signed = truthy_checkbox(request.form.get("buyer_agreement_signed"))
            wire_fraud_notice_signed = truthy_checkbox(request.form.get("wire_fraud_notice_signed"))
            dual_agency_consent_signed = truthy_checkbox(request.form.get("dual_agency_consent_signed"))

            # Additional checklist items you added
            preapproval_letter_received = truthy_checkbox(request.form.get("preapproval_letter_received"))
            proof_of_funds_received = truthy_checkbox(request.form.get("proof_of_funds_received"))
            photo_id_received = truthy_checkbox(request.form.get("photo_id_received"))

            if buyer_profile:
                # Update existing buyer profile
                cur.execute(
                    """
                    UPDATE buyer_profiles
                    SET
                      timeframe = %s,
                      min_price = %s,
                      max_price = %s,
                      areas = %s,
                      property_types = %s,
                      property_type = %s,
                      preapproval_status = %s,
                      lender_name = %s,
                      referral_source = %s,
                      notes = %s,

                      cis_signed = %s,
                      buyer_agreement_signed = %s,
                      wire_fraud_notice_signed = %s,
                      dual_agency_consent_signed = %s,

                      preapproval_letter_received = %s,
                      proof_of_funds_received = %s,
                      photo_id_received = %s,

                      buyer_attorney_name = %s,
                      buyer_attorney_email = %s,
                      buyer_attorney_phone = %s,
                      buyer_attorney_referred = %s,

                      buyer_lender_email = %s,
                      buyer_lender_phone = %s,
                      buyer_lender_referred = %s,

                      buyer_inspector_name = %s,
                      buyer_inspector_email = %s,
                      buyer_inspector_phone = %s,
                      buyer_inspector_referred = %s,

                      other_professionals = %s
                    WHERE id = %s
                    """,
                    (
                        timeframe,
                        min_price,
                        max_price,
                        areas,
                        property_types,
                        property_type,
                        preapproval_status,
                        lender_name,
                        referral_source,
                        notes,

                        cis_signed,
                        buyer_agreement_signed,
                        wire_fraud_notice_signed,
                        dual_agency_consent_signed,

                        preapproval_letter_received,
                        proof_of_funds_received,
                        photo_id_received,

                        buyer_attorney_name,
                        buyer_attorney_email,
                        buyer_attorney_phone,
                        buyer_attorney_referred,

                        buyer_lender_email,
                        buyer_lender_phone,
                        buyer_lender_referred,

                        buyer_inspector_name,
                        buyer_inspector_email,
                        buyer_inspector_phone,
                        buyer_inspector_referred,

                        other_professionals,
                        buyer_profile["id"],
                    ),
                )
            else:
                # Create new buyer profile
                cur.execute(
                    """
                    INSERT INTO buyer_profiles (
                      contact_id,
                      timeframe,
                      min_price,
                      max_price,
                      areas,
                      property_types,
                      property_type,
                      preapproval_status,
                      lender_name,
                      referral_source,
                      notes,

                      cis_signed,
                      buyer_agreement_signed,
                      wire_fraud_notice_signed,
                      dual_agency_consent_signed,

                      preapproval_letter_received,
                      proof_of_funds_received,
                      photo_id_received,

                      buyer_attorney_name,
                      buyer_attorney_email,
                      buyer_attorney_phone,
                      buyer_attorney_referred,

                      buyer_lender_email,
                      buyer_lender_phone,
                      buyer_lender_referred,

                      buyer_inspector_name,
                      buyer_inspector_email,
                      buyer_inspector_phone,
                      buyer_inspector_referred,

                      other_professionals
                    )
                    VALUES (
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s,
                      %s, %s, %s,
                      %s, %s, %s, %s,
                      %s, %s, %s,
                      %s, %s, %s, %s,
                      %s
                    )
                    RETURNING *
                    """,
                    (
                        contact_id,
                        timeframe,
                        min_price,
                        max_price,
                        areas,
                        property_types,
                        property_type,
                        preapproval_status,
                        lender_name,
                        referral_source,
                        notes,

                        cis_signed,
                        buyer_agreement_signed,
                        wire_fraud_notice_signed,
                        dual_agency_consent_signed,

                        preapproval_letter_received,
                        proof_of_funds_received,
                        photo_id_received,

                        buyer_attorney_name,
                        buyer_attorney_email,
                        buyer_attorney_phone,
                        buyer_attorney_referred,

                        buyer_lender_email,
                        buyer_lender_phone,
                        buyer_lender_referred,

                        buyer_inspector_name,
                        buyer_inspector_email,
                        buyer_inspector_phone,
                        buyer_inspector_referred,

                        other_professionals,
                    ),
                )
                buyer_profile = cur.fetchone()

            conn.commit()
            return redirect(url_for("buyer_profile", contact_id=contact_id))
  
    # After any POST handling: load subject properties for display
    if buyer_profile:
        cur.execute(
            """
            SELECT id, address_line, city, state, postal_code, offer_status
            FROM buyer_properties
            WHERE buyer_profile_id = %s
            ORDER BY created_at DESC
            """,
            (buyer_profile["id"],),
        )
        subject_properties = cur.fetchall()
    else:
        subject_properties = []

    # Build contact display fields for the template
    contact_name = f"{contact['first_name']} {contact['last_name']}".strip()
    contact_email = contact.get("email")
    contact_phone = contact.get("phone")

    # For now, keep professional lists empty unless you already have queries elsewhere
    pros_attorneys = []
    pros_lenders = []
    pros_inspectors = []

    return render_template(
        "buyer_profile.html",
        # contact object + convenience display fields
        contact=contact,
        c=contact,
        contact_name=contact_name,
        contact_email=contact_email,
        contact_phone=contact_phone,

        # buyer profile object under the name the template uses
        bp=buyer_profile,
        buyer_profile=buyer_profile,
        buyer=buyer_profile,

        # subject properties and other context
        subject_properties=subject_properties,
        contact_id=contact_id,
        pros_attorneys = get_professionals_for_dropdown(current_user.id, category="Attorney"),
        pros_lenders = get_professionals_for_dropdown(current_user.id, category="Lender"),
        pros_inspectors = get_professionals_for_dropdown(current_user.id, category="Inspector"),
        
        #transactions
        transactions=buyer_transactions,
        transaction_statuses=TRANSACTION_STATUSES,
    )

@app.route("/buyer/property/<int:property_id>/edit", methods=["GET", "POST"])
@login_required
def edit_buyer_property(property_id):
    conn = get_db()
    cur = conn.cursor()

    # Load the property along with its contact info
    cur.execute(
        """
        SELECT
            bp.id,
            bp.buyer_profile_id,
            bp.address_line,
            bp.city,
            bp.state,
            bp.postal_code,
            bp.offer_status,
            c.id AS contact_id,
            c.first_name,
            c.last_name
        FROM buyer_properties bp
        JOIN buyer_profiles b ON bp.buyer_profile_id = b.id
        JOIN contacts c ON b.contact_id = c.id
        WHERE bp.id = %s
        """,
        (property_id,),
    )
    prop = cur.fetchone()

    if not prop:
        conn.close()
        return "Subject property not found", 404

    contact_name = f"{prop['first_name']} {prop['last_name']}".strip()
    contact_id = prop["contact_id"]

    if request.method == "POST":
        address_line = (request.form.get("address_line") or "").strip()
        city = (request.form.get("city") or "").strip()
        state = (request.form.get("state") or "").strip()
        postal_code = (request.form.get("postal_code") or "").strip()
        offer_status = (request.form.get("offer_status") or "").strip()

        cur.execute(
            """
            UPDATE buyer_properties
            SET address_line = %s,
                city = %s,
                state = %s,
                postal_code = %s,
                offer_status = %s
            WHERE id = %s
            """,
            (address_line, city, state, postal_code, offer_status, property_id),
        )

        conn.commit()
        conn.close()
        return redirect(url_for("buyer_profile", contact_id=contact_id))

    conn.close()
    return render_template(
        "edit_buyer_property.html",
        prop=prop,
        contact_name=contact_name,
        contact_id=contact_id,
    )

@app.route("/professionals", methods=["GET", "POST"])
@login_required
def professionals():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == "POST":
        name = request.form.get("name")
        company = request.form.get("company")
        phone = normalize_phone(request.form.get("phone") or request.form.get("related_phone"))
        email = request.form.get("email")
        category = request.form.get("category")
        grade = request.form.get("grade")
        notes = request.form.get("notes")

        if not name or not grade:
            flash("Name and grade are required.", "danger")
        else:
            cur.execute(
                """
                INSERT INTO professionals
                    (user_id, name, company, phone, email, category, grade, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (current_user.id, name, company, phone, email, category, grade, notes),
            )
            conn.commit()
            flash("Professional saved.", "success")

        return redirect(url_for("professionals"))

    professionals_list = get_professionals_for_dropdown(current_user.id)
    return render_template(
        "professionals.html",
        professionals=professionals_list,
        active_page="professionals"
    )
    
@app.route("/professionals/<int:prof_id>/edit", methods=["GET", "POST"])
@login_required
def edit_professional(prof_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == "POST":
        name = request.form.get("name")
        company = request.form.get("company")
        phone = normalize_phone(request.form.get("phone") or request.form.get("related_phone"))
        email = request.form.get("email")
        category = request.form.get("category")
        grade = request.form.get("grade")
        notes = request.form.get("notes")

        cur.execute(
            """
            UPDATE professionals
            SET name = %s,
                company = %s,
                phone = %s,
                email = %s,
                category = %s,
                grade = %s,
                notes = %s
            WHERE id = %s
            """,
            (name, company, phone, email, category, grade, notes, prof_id),
        )
        conn.commit()
        flash("Professional updated.", "success")
        return redirect(url_for("professionals"))

    cur.execute(
        "SELECT * FROM professionals WHERE id = %s AND user_id = %s",
        (prof_id, current_user.id),
    )
    professional = cur.fetchone()
    if not professional:
        abort(404)

    return render_template(
        "edit_professional.html",
        professional=professional,
        active_page="professionals"
    )

@app.route("/professionals/search")
@login_required
def professionals_search():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])

    like = f"%{q}%"
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT id, name, company, category
            FROM professionals
            WHERE user_id = %s
              AND (
                    name ILIKE %s
                 OR COALESCE(company, '') ILIKE %s
                 OR COALESCE(category, '') ILIKE %s
              )
            ORDER BY name ASC, id DESC
            LIMIT 10
            """,
            (current_user.id, like, like, like),
        )
        rows = cur.fetchall() or []
        return jsonify([
            {
                "id": r["id"],
                "name": r.get("name") or "",
                "category": r.get("category") or "",
                "company": r.get("company") or "",
            }
            for r in rows
        ])
    finally:
        conn.close()

@app.route("/professionals/<int:prof_id>/delete", methods=["POST"])
@login_required
def delete_professional(prof_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM professionals WHERE id = %s AND user_id = %s",
        (prof_id, current_user.id),
    )

    if cur.rowcount == 0:
        abort(404)

    conn.commit()
    flash("Professional deleted.", "info")
    return redirect(url_for("professionals"))

@app.route("/seller/<int:contact_id>", methods=["GET", "POST"])
@login_required
def seller_profile(contact_id):
    conn = get_db()
    cur = conn.cursor()
    
    seller_transactions = []
    
    # Phase 3.3: Transactions (seller sheet)
    cur.execute(
        """
        SELECT
            id,
            status,
            transaction_type,
            address,
            list_price,
            offer_price,
            expected_close_date,
            updated_at
        FROM transactions
        WHERE contact_id = %s
          AND user_id = %s
          AND transaction_type = 'sell'
        ORDER BY COALESCE(expected_close_date, updated_at) DESC, id DESC
        LIMIT 10
        """,
        (contact_id, current_user.id),
    )
    seller_transactions = cur.fetchall()

    # Load contact (scoped to current user)
    cur.execute(
        "SELECT * FROM contacts WHERE id = %s AND user_id = %s",
        (contact_id, current_user.id),
    )
    contact = cur.fetchone()
    if not contact:
        conn.close()
        return "Contact not found", 404

    if request.method == "POST":
        # Basic seller info
        property_type = (request.form.get("property_type") or "").strip()
        timeframe = (request.form.get("timeframe") or "").strip()
        motivation = (request.form.get("motivation") or "").strip()
        condition_notes = (request.form.get("condition_notes") or "").strip()
        property_address = (request.form.get("property_address") or "").strip()

        # Estimated price: allow blank and commas
        estimated_price_raw = (request.form.get("estimated_price") or "").replace(",", "").strip()
        estimated_price = None
        if estimated_price_raw:
            try:
                estimated_price = int(estimated_price_raw)
            except ValueError:
                estimated_price = None

        referral_source = (request.form.get("referral_source") or "").strip()
        notes = (request.form.get("notes") or "").strip()

        # Professionals - Attorney
        seller_attorney_name = (request.form.get("seller_attorney_name") or "").strip()
        seller_attorney_email = (request.form.get("seller_attorney_email") or "").strip()
        seller_attorney_phone = normalize_phone(request.form.get("phone") or request.form.get("related_phone"))
        seller_attorney_referred = bool(request.form.get("seller_attorney_referred"))

        # Professionals - Lender
        seller_lender_name = (request.form.get("seller_lender_name") or "").strip()
        seller_lender_email = (request.form.get("seller_lender_email") or "").strip()
        seller_lender_phone = normalize_phone(request.form.get("phone") or request.form.get("related_phone"))
        seller_lender_referred = bool(request.form.get("seller_lender_referred"))

        # Professionals - Home Inspector
        seller_inspector_name = (request.form.get("seller_inspector_name") or "").strip()
        seller_inspector_email = (request.form.get("seller_inspector_email") or "").strip()
        seller_inspector_phone = normalize_phone(request.form.get("phone") or request.form.get("related_phone"))
        seller_inspector_referred = bool(request.form.get("seller_inspector_referred"))

        # Other professionals
        other_professionals = (request.form.get("other_professionals") or "").strip()

        # Does a row already exist? (scoped to current user via contacts)
        cur.execute(
            """
            SELECT sp.id
            FROM seller_profiles sp
            JOIN contacts c ON c.id = sp.contact_id
            WHERE sp.contact_id = %s
              AND c.user_id = %s
            """,
            (contact_id, current_user.id),
        )
        existing = cur.fetchone()

        if existing:
            # UPDATE existing row
            cur.execute(
                """
                UPDATE seller_profiles
                SET property_type = %s,
                    timeframe = %s,
                    motivation = %s,
                    estimated_price = %s,
                    property_address = %s,
                    condition_notes = %s,
                    referral_source = %s,
                    notes = %s,
                    seller_attorney_name = %s,
                    seller_attorney_email = %s,
                    seller_attorney_phone = %s,
                    seller_attorney_referred = %s,
                    seller_lender_name = %s,
                    seller_lender_email = %s,
                    seller_lender_phone = %s,
                    seller_lender_referred = %s,
                    seller_inspector_name = %s,
                    seller_inspector_email = %s,
                    seller_inspector_phone = %s,
                    seller_inspector_referred = %s,
                    other_professionals = %s
                WHERE contact_id = %s
                """,
                (
                    property_type,
                    timeframe,
                    motivation,
                    estimated_price,
                    property_address,
                    condition_notes,
                    referral_source,
                    notes,
                    seller_attorney_name,
                    seller_attorney_email,
                    seller_attorney_phone,
                    seller_attorney_referred,
                    seller_lender_name,
                    seller_lender_email,
                    seller_lender_phone,
                    seller_lender_referred,
                    seller_inspector_name,
                    seller_inspector_email,
                    seller_inspector_phone,
                    seller_inspector_referred,
                    other_professionals,
                    contact_id,
                ),
            )
        else:
            # INSERT new row
            cur.execute(
                """
                INSERT INTO seller_profiles (
                    contact_id,
                    property_type,
                    timeframe,
                    motivation,
                    estimated_price,
                    property_address,
                    condition_notes,
                    referral_source,
                    notes,
                    seller_attorney_name,
                    seller_attorney_email,
                    seller_attorney_phone,
                    seller_attorney_referred,
                    seller_lender_name,
                    seller_lender_email,
                    seller_lender_phone,
                    seller_lender_referred,
                    seller_inspector_name,
                    seller_inspector_email,
                    seller_inspector_phone,
                    seller_inspector_referred,
                    other_professionals
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s
                )
                """,
                (
                    contact_id,
                    property_type,
                    timeframe,
                    motivation,
                    estimated_price,
                    property_address,
                    condition_notes,
                    referral_source,
                    notes,
                    seller_attorney_name,
                    seller_attorney_email,
                    seller_attorney_phone,
                    seller_attorney_referred,
                    seller_lender_name,
                    seller_lender_email,
                    seller_lender_phone,
                    seller_lender_referred,
                    seller_inspector_name,
                    seller_inspector_email,
                    seller_inspector_phone,
                    seller_inspector_referred,
                    other_professionals,
                ),
            )

        conn.commit()
        conn.close()
        return redirect(url_for("seller_profile", contact_id=contact_id))

    # GET – load existing seller profile (if any)
    cur.execute(
        "SELECT * FROM seller_profiles WHERE contact_id = %s",
        (contact_id,),
    )
    sp = cur.fetchone()
    conn.close()

    contact_name = (contact.get("first_name") or "") + (
        " " if contact.get("first_name") and contact.get("last_name") else ""
    ) + (contact.get("last_name") or "")
    contact_name = contact_name.strip() or contact["name"]
    pros_attorneys = get_professionals_for_dropdown(current_user.id, category="Attorney")
    pros_lenders = get_professionals_for_dropdown(current_user.id, category="Lender")
    pros_inspectors = get_professionals_for_dropdown(current_user.id, category="Inspector")

    ensure_listing_checklist_initialized(current_user.id, contact_id)
    checklist_items, checklist_complete, checklist_total = get_listing_checklist(contact_id)
    
    return render_template(
        "seller_profile.html",
        c=contact,
        contact_name=contact_name,
        contact_email=contact.get("email"),
        contact_phone=contact.get("phone"),
        sp=sp,
        profile=sp,
        contact_id=contact_id,
        today=date.today(),
        active_page="contacts",
        pros_attorneys=pros_attorneys,
        pros_lenders=pros_lenders,
        pros_inspectors=pros_inspectors,
    
        checklist_items=checklist_items,
        checklist_complete=checklist_complete,
        checklist_total=checklist_total,
        
        #Transactions
        transactions=seller_transactions,
        transaction_statuses=TRANSACTION_STATUSES,
    )

@app.route("/followups")
@login_required
def followups():
    today = date.today()

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            e.id AS engagement_id,
            e.contact_id,
            e.engagement_type,
            e.follow_up_due_at,
            e.outcome,
            e.notes,
            e.summary_clean,
    
            c.id AS contact_id,
            c.name,
            c.first_name,
            c.last_name,
            c.pipeline_stage,
            c.priority,
            c.target_area
    
        FROM engagements e
        JOIN contacts c ON c.id = e.contact_id
        WHERE e.user_id = %s
          AND c.user_id = %s
          AND c.archived_at IS NULL
          AND e.requires_follow_up = TRUE
          AND e.follow_up_completed = FALSE
          AND e.follow_up_due_at IS NOT NULL
        ORDER BY e.follow_up_due_at ASC, c.name ASC, e.id ASC
        """,
        (current_user.id, current_user.id),
    )
    rows = cur.fetchall()
    conn.close()

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    overdue = []
    today_list = []
    upcoming = []
    
    for row in rows:
        due = row.get("follow_up_due_at")
        if not due:
            continue
    
        # Safety: normalize naive timestamps
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
    
        if due < now:
            overdue.append(row)
        elif today_start <= due < today_end:
            today_list.append(row)
        else:
            upcoming.append(row)

    return render_template(
        "followups.html",
        overdue=overdue,
        today_list=today_list,
        upcoming=upcoming,
        today=today.isoformat(),
        active_page="followups",
    )

@app.route("/followups/<int:engagement_id>/clear", methods=["POST"])
@login_required
def followup_clear(engagement_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE engagements
            SET follow_up_completed = TRUE,
                follow_up_due_at = NULL
            WHERE user_id = %s
              AND id = %s
            """,
            (current_user.id, engagement_id),
        )
        conn.commit()
        flash("Follow-up cleared.", "success")
        return redirect(url_for("dashboard") + "#followups")
    except Exception:
        conn.rollback()
        app.logger.exception("Failed to clear follow-up")
        flash("Could not clear follow-up.", "danger")
        return redirect(url_for("dashboard") + "#followups")
    finally:
        conn.close()

@app.route("/engagements/<int:engagement_id>/followup.ics")
@login_required
def followup_calendar_ics(engagement_id):
    conn = get_db()
    try:
        cur = conn.cursor()

        # Pull from the same join you already use for followups_for_contact:
        # Must return: contact name, follow_up_due_at (or NULL), notes/summary
        cur.execute("""
            SELECT
              e.id,
              e.follow_up_due_at,
              COALESCE(NULLIF(TRIM(e.notes), ''), '') AS notes,
              COALESCE(NULLIF(TRIM(e.summary_clean), ''), '') AS summary_clean,
              c.id AS contact_id,
              COALESCE(
                NULLIF(TRIM(c.name), ''),
                NULLIF(TRIM(CONCAT_WS(' ', c.first_name, c.last_name)), ''),
                '(Unnamed)'
              ) AS contact_name
            FROM engagements e
            JOIN contacts c ON c.id = e.contact_id
            WHERE e.id = %s
              AND e.user_id = %s
              AND c.user_id = %s
              AND e.requires_follow_up = TRUE
            LIMIT 1
        """, (engagement_id, current_user.id, current_user.id))

        row = cur.fetchone()
        if not row:
            abort(404)

        eid = row["id"]
        follow_up_due_at = row["follow_up_due_at"]
        notes = row.get("notes") or ""
        summary_clean = row.get("summary_clean") or ""
        contact_id = row["contact_id"]
        contact_name = row.get("contact_name") or "(Unnamed)"
        
        # Normalize follow_up_due_at to a datetime
        start_dt = None
        
        if follow_up_due_at is None or str(follow_up_due_at).strip() == "":
            now_local = datetime.now()
            start_dt = datetime(now_local.year, now_local.month, now_local.day, 9, 0, 0)
        
        elif isinstance(follow_up_due_at, datetime):
            start_dt = follow_up_due_at
        
        elif isinstance(follow_up_due_at, date):
            start_dt = datetime(follow_up_due_at.year, follow_up_due_at.month, follow_up_due_at.day, 9, 0, 0)
        
        else:
            # It's a string. Try common formats.
            s = str(follow_up_due_at).strip()
        
            parsed = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    parsed = datetime.strptime(s, fmt)
                    break
                except ValueError:
                    pass
        
            if parsed is None:
                # Last resort: if it's ISO-ish, try fromisoformat
                try:
                    parsed = datetime.fromisoformat(s)
                except Exception:
                    parsed = None
        
            if parsed is None:
                abort(400, description="Could not parse follow-up due date/time for calendar export.")
        
            start_dt = parsed
        
        # If time was effectively empty in UI and stored as midnight, bump to 9:00 AM
        if start_dt.hour == 0 and start_dt.minute == 0:
            start_dt = start_dt.replace(hour=9, minute=0, second=0)

        description_parts = []
        if notes:
            description_parts.append(notes)
        if summary_clean:
            description_parts.append(f"Summary: {summary_clean}")
        description = "\n\n".join(description_parts).strip()

        ics = build_ics_event(
            title=f"{contact_name} Followup",
            description=description,
            start_dt=start_dt,
            tzid="America/New_York",
            duration_minutes=15,
            uid=f"ulysses-followup-{eid}-{contact_id}@ulyssescrm"
        )

        filename = f"{contact_name}-followup.ics".replace(" ", "_").replace("/", "-")
        return Response(
            ics,
            mimetype="text/calendar; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    finally:
        conn.close()

@app.route("/contacts/<int:contact_id>/followup/clear", methods=["POST"])
@login_required
def contact_followup_clear(contact_id):
    next_url = request.form.get("next")
    if not is_safe_url(next_url):
        next_url = url_for("edit_contact", contact_id=contact_id) + "#pane-followups"

    conn = get_db()
    cur = conn.cursor()

    # Tenant safety: scope by user_id
    cur.execute(
        """
        UPDATE contacts
        SET next_follow_up = NULL,
            next_follow_up_time = NULL
        WHERE id = %s AND user_id = %s
        """,
        (contact_id, current_user.id),
    )
    conn.commit()
    conn.close()

    flash("Contact follow-up cleared.", "success")
    return redirect(next_url)

@app.route("/interaction/<int:interaction_id>/complete", methods=["POST"])
@login_required
def complete_interaction(interaction_id):
    conn = get_db()
    cur = conn.cursor()

    # Get the contact_id so we know where to send you back
    cur.execute(
        "SELECT contact_id FROM interactions WHERE id = %s AND user_id = %s",
        (interaction_id, current_user.id),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return "Interaction not found", 404

    contact_id = row["contact_id"]

    cur.execute(
        """
        UPDATE interactions
        SET is_completed = TRUE,
            completed_at = NOW()
        WHERE user_id = %s
          AND id = %s
        """,
        (current_user.id, interaction_id),
    )
    if cur.rowcount == 0:
        conn.close()
        return "Interaction not found", 404

    conn.commit()
    conn.close()

    # Back to the edit page for that contact
    return redirect(url_for("edit_contact", contact_id=contact_id))

@app.route("/interaction/<int:interaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit_interaction(interaction_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM interactions WHERE id = %s AND user_id = %s",
        (interaction_id, current_user.id),
    )
    interaction = cur.fetchone()

    if not interaction:
        conn.close()
        return "Interaction not found", 404

    contact_id = interaction["contact_id"]

    if request.method == "POST":
        happened_at = request.form.get("happened_at") or None
        kind = (request.form.get("kind") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        time_of_day = (request.form.get("time_of_day") or "").strip()
        is_completed = bool(request.form.get("is_completed"))

        cur.execute(
            """
            UPDATE interactions
            SET happened_at = %s,
                kind = %s,
                notes = %s,
                time_of_day = %s,
                is_completed = %s
            WHERE user_id = %s
              AND id = %s
            """,
            (happened_at, kind, notes, time_of_day, is_completed, current_user.id, interaction_id),
        )
        if cur.rowcount == 0:
            conn.close()
            return "Interaction not found", 404

        conn.commit()
        conn.close()
        return redirect(url_for("edit_contact", contact_id=contact_id))

    conn.close()
    return render_template("edit_interaction.html", interaction=interaction)

@app.route("/contacts/<int:contact_id>/transactions/new", methods=["GET", "POST"])
@login_required
def new_transaction(contact_id):
    conn = get_db()
    cur = conn.cursor()

    # 1) Resolve next_url safely for BOTH GET and POST
    next_url = request.args.get("next")
    if not is_safe_url(next_url):
        next_url = None
    next_url = next_url or url_for("edit_contact", contact_id=contact_id)

    default_tx_type = (request.args.get("transaction_type") or "").strip().lower()
    if default_tx_type not in ("buy", "sell"):
        default_tx_type = ""

    cur.execute(
        "SELECT id FROM contacts WHERE id = %s AND user_id = %s",
        (contact_id, current_user.id),
    )
    if not cur.fetchone():
        conn.close()
        return "Contact not found", 404

    if request.method == "POST":
        status = (request.form.get("status") or "draft").strip()
        transaction_type = (request.form.get("transaction_type") or default_tx_type or "sell").strip().lower()

        address = (request.form.get("address") or "").strip() or None
        list_price = (request.form.get("list_price") or "").strip() or None
        offer_price = (request.form.get("offer_price") or "").strip() or None
        expected_close_date = (request.form.get("expected_close_date") or "").strip() or None
        actual_close_date = (request.form.get("actual_close_date") or "").strip() or None

        attorney_review_end_date = (request.form.get("attorney_review_end_date") or "").strip() or None
        inspection_deadline = (request.form.get("inspection_deadline") or "").strip() or None
        financing_contingency_date = (request.form.get("financing_contingency_date") or "").strip() or None
        appraisal_deadline = (request.form.get("appraisal_deadline") or "").strip() or None
        mortgage_commitment_date = (request.form.get("mortgage_commitment_date") or "").strip() or None

        sql = """
            INSERT INTO transactions (
                user_id,
                contact_id,
                status,
                transaction_type,
                address,
                listing_status,
                offer_status,
                list_price,
                offer_price,
                expected_close_date,
                actual_close_date,
                attorney_review_end_date,
                inspection_deadline,
                financing_contingency_date,
                appraisal_deadline,
                mortgage_commitment_date
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s
            )
            RETURNING id
        """

        params = (
            current_user.id,
            contact_id,
            status,
            transaction_type,
            address,
            "draft",
            "draft",
            list_price,
            offer_price,
            expected_close_date,
            actual_close_date,
            attorney_review_end_date,
            inspection_deadline,
            financing_contingency_date,
            appraisal_deadline,
            mortgage_commitment_date,
        )

        cur.execute(sql, params)
        row = cur.fetchone()
        if not row or "id" not in row:
            conn.rollback()
            conn.close()
            return "Insert failed", 500

        conn.commit()
        conn.close()
        return redirect(next_url)

    conn.close()
    return render_template(
        "transactions/transaction_form.html",
        mode="new",
        tx=None,
        transaction_statuses=TRANSACTION_STATUSES,
        listing_statuses=LISTING_STATUSES,
        offer_statuses=OFFER_STATUSES,
        next_url=next_url,
        deadlines=[],
        default_tx_type=default_tx_type,
        
    )

@app.route("/transactions/new", methods=["GET"])
@login_required
def new_transaction_no_contact():
    # Preserve your existing next pattern
    next_url = request.args.get("next")
    if not is_safe_url(next_url):
        next_url = None
    next_url = next_url or url_for("dashboard")

    flash("Select a contact first, then use + New Transaction on that contact.", "info")
    return redirect(url_for("contacts", next=next_url))

@app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id):
    conn = get_db()
    cur = conn.cursor()

    # Fetch transaction
    cur.execute(
        """
        SELECT *
        FROM transactions
        WHERE id = %s AND user_id = %s
        """,
        (transaction_id, current_user.id),
    )
    tx = cur.fetchone()

    if not tx:
        conn.close()
        return "Transaction not found", 404

    # Fetch contact
    cur.execute(
        """
        SELECT first_name, last_name, email, phone
        FROM contacts
        WHERE id = %s AND user_id = %s
        """,
        (tx["contact_id"], current_user.id),
    )
    contact = cur.fetchone()

    if not contact:
        conn.close()
        return "Contact not found", 404

    # Deadlines (read-only list here)
    cur.execute(
        """
        SELECT
            id,
            name,
            due_date,
            is_done,
            notes
        FROM transaction_deadlines
        WHERE transaction_id = %s
          AND user_id = %s
        ORDER BY due_date ASC NULLS LAST, id ASC
        """,
        (transaction_id, current_user.id),
    )
    deadlines = cur.fetchall()

    if request.method == "POST":
        status = request.form.get("status", tx["status"])
        transaction_type = request.form.get("transaction_type", tx["transaction_type"])

        listing_status = (request.form.get("listing_status") or tx.get("listing_status") or "draft").strip()
        offer_status = (request.form.get("offer_status") or tx.get("offer_status") or "draft").strip()

        # Guardrails
        if listing_status not in LISTING_STATUS_VALUES:
            listing_status = tx.get("listing_status") or "draft"
        if offer_status not in OFFER_STATUS_VALUES:
            offer_status = tx.get("offer_status") or "draft"

        address = (request.form.get("address") or "").strip() or None
        list_price = (request.form.get("list_price") or "").strip() or None
        offer_price = (request.form.get("offer_price") or "").strip() or None
        expected_close_date = (request.form.get("expected_close_date") or "").strip() or None
        actual_close_date = (request.form.get("actual_close_date") or "").strip() or None

        attorney_review_end_date = (request.form.get("attorney_review_end_date") or "").strip() or None
        inspection_deadline = (request.form.get("inspection_deadline") or "").strip() or None
        financing_contingency_date = (request.form.get("financing_contingency_date") or "").strip() or None
        appraisal_deadline = (request.form.get("appraisal_deadline") or "").strip() or None
        mortgage_commitment_date = (request.form.get("mortgage_commitment_date") or "").strip() or None

        cur.execute(
            """
            UPDATE transactions
            SET status = %s,
                transaction_type = %s,
                address = %s,
                listing_status = %s,
                offer_status = %s,
                list_price = %s,
                offer_price = %s,
                expected_close_date = %s,
                actual_close_date = %s,
                attorney_review_end_date = %s,
                inspection_deadline = %s,
                financing_contingency_date = %s,
                appraisal_deadline = %s,
                mortgage_commitment_date = %s,
                updated_at = NOW()
            WHERE id = %s AND user_id = %s
            """,
            (
                status,
                transaction_type,
                address,
                listing_status,
                offer_status,
                list_price,
                offer_price,
                expected_close_date,
                actual_close_date,
                attorney_review_end_date,
                inspection_deadline,
                financing_contingency_date,
                appraisal_deadline,
                mortgage_commitment_date,
                transaction_id,
                current_user.id,
            ),
        )

        conn.commit()
        next_url = request.form.get("next") or url_for("edit_contact", contact_id=tx["contact_id"])
        conn.close()
        return redirect(next_url)

    next_url = request.args.get("next") or url_for("edit_contact", contact_id=tx["contact_id"])
    conn.close()
    return render_template(
        "transactions/transaction_form.html",
        mode="edit",
        tx=tx,
        contact=contact,
        transaction_statuses=TRANSACTION_STATUSES,
        listing_statuses=LISTING_STATUSES,
        offer_statuses=OFFER_STATUSES,
        next_url=next_url,
        deadlines=deadlines,
    )
    
@app.route("/transactions/<int:transaction_id>/deadlines/add", methods=["POST"])
@login_required
def add_transaction_deadline(transaction_id):
    conn = get_db()
    cur = conn.cursor()

    # Confirm transaction belongs to user
    cur.execute(
        "SELECT id FROM transactions WHERE id = %s AND user_id = %s",
        (transaction_id, current_user.id),
    )
    tx = cur.fetchone()
    if not tx:
        conn.close()
        return "Transaction not found", 404

    name = (request.form.get("name") or "").strip()
    due_date = (request.form.get("due_date") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    if not name:
        conn.close()
        return "Deadline name is required", 400

    cur.execute(
        """
        INSERT INTO transaction_deadlines (user_id, transaction_id, name, due_date, is_done, notes)
        VALUES (%s, %s, %s, %s, false, %s)
        """,
        (current_user.id, transaction_id, name, due_date, notes),
    )

    conn.commit()
    next_url = request.form.get("next") or url_for("edit_transaction", transaction_id=transaction_id)
    conn.close()
    return redirect(next_url)


@app.route("/deadlines/<int:deadline_id>/toggle", methods=["POST"])
@login_required
def toggle_transaction_deadline(deadline_id):
    conn = get_db()
    cur = conn.cursor()

    # Fetch deadline and confirm ownership
    cur.execute(
        """
        SELECT id, transaction_id, is_done
        FROM transaction_deadlines
        WHERE id = %s AND user_id = %s
        """,
        (deadline_id, current_user.id),
    )
    d = cur.fetchone()
    if not d:
        conn.close()
        return "Deadline not found", 404

    cur.execute(
        """
        UPDATE transaction_deadlines
        SET is_done = %s,
            updated_at = NOW()
        WHERE id = %s AND user_id = %s
        """,
        (not d["is_done"], deadline_id, current_user.id),
    )

    conn.commit()
    next_url = request.form.get("next") or url_for("edit_transaction", transaction_id=d["transaction_id"])
    conn.close()
    return redirect(next_url)


@app.route("/deadlines/<int:deadline_id>/edit", methods=["POST"])
@login_required
def edit_transaction_deadline(deadline_id):
    conn = get_db()
    cur = conn.cursor()

    # Fetch deadline and confirm ownership
    cur.execute(
        """
        SELECT id, transaction_id
        FROM transaction_deadlines
        WHERE id = %s AND user_id = %s
        """,
        (deadline_id, current_user.id),
    )
    d = cur.fetchone()
    if not d:
        conn.close()
        return "Deadline not found", 404

    name = (request.form.get("name") or "").strip()
    due_date = (request.form.get("due_date") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    if not name:
        conn.close()
        return "Deadline name is required", 400

    cur.execute(
        """
        UPDATE transaction_deadlines
        SET name = %s,
            due_date = %s,
            notes = %s,
            updated_at = NOW()
        WHERE id = %s AND user_id = %s
        """,
        (name, due_date, notes, deadline_id, current_user.id),
    )

    conn.commit()
    next_url = request.form.get("next") or url_for("edit_transaction", transaction_id=d["transaction_id"])
    conn.close()
    return redirect(next_url)


@app.route("/deadlines/<int:deadline_id>/delete", methods=["POST"])
@login_required
def delete_transaction_deadline(deadline_id):
    conn = get_db()
    cur = conn.cursor()

    # Get transaction_id for redirect and confirm ownership
    cur.execute(
        """
        SELECT id, transaction_id
        FROM transaction_deadlines
        WHERE id = %s AND user_id = %s
        """,
        (deadline_id, current_user.id),
    )
    d = cur.fetchone()
    if not d:
        conn.close()
        return "Deadline not found", 404

    cur.execute(
        "DELETE FROM transaction_deadlines WHERE id = %s AND user_id = %s",
        (deadline_id, current_user.id),
    )

    conn.commit()
    next_url = request.form.get("next") or url_for("edit_transaction", transaction_id=d["transaction_id"])
    conn.close()
    return redirect(next_url)


@app.route("/openhouses")
@login_required
def openhouse_list():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        """
        SELECT
            id,
            address_line1,
            city,
            state,
            zip,
            start_datetime,
            end_datetime,
            public_token
        FROM open_houses
        WHERE created_by_user_id = %s
        ORDER BY start_datetime DESC
        """,
        (current_user.id,),
    )
    rows = cur.fetchall()
    conn.close()
    
    return render_template("openhouses/list.html", openhouses=rows)


@app.route("/openhouses/new", methods=["GET", "POST"])
@login_required
def openhouse_new():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == "POST":
        address_line1 = (request.form.get("address_line1") or "").strip()
        city = (request.form.get("city") or "").strip()
        state = (request.form.get("state") or "NJ").strip()
        zip_code = (request.form.get("zip") or "").strip()

        start_dt = request.form.get("start_datetime")
        end_dt = request.form.get("end_datetime")

        house_photo_url = (request.form.get("house_photo_url") or "").strip() or None
        notes = (request.form.get("notes") or "").strip() or None

        if not (address_line1 and city and state and zip_code and start_dt and end_dt):
            flash("Please fill out address, date/time, and required fields.", "danger")
            conn.close()
            return render_template("openhouses/new.html")

        token = generate_public_token()

        cur.execute(
            """
            INSERT INTO open_houses
              (created_by_user_id, address_line1, city, state, zip, start_datetime, end_datetime, public_token, house_photo_url, notes)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                current_user.id,
                address_line1,
                city,
                state,
                zip_code,
                start_dt,
                end_dt,
                token,
                house_photo_url,
                notes,
            ),
        )

        row = cur.fetchone()
        if not row or "id" not in row:
            conn.close()
            abort(500)

        open_house_id = row["id"]

        conn.commit()

        flash("Open house created.", "success")
        conn.close()
        return redirect(url_for("openhouse_detail", open_house_id=open_house_id))

    conn.close()
    return render_template("openhouses/new.html")

@app.route("/openhouses/<int:open_house_id>")
@login_required
def openhouse_detail(open_house_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        cur.execute(
            """
            SELECT id, address_line1, city, state, zip, start_datetime, end_datetime,
                   public_token, house_photo_url, notes
            FROM open_houses
            WHERE id = %s AND created_by_user_id = %s
            """,
            (open_house_id, current_user.id),
        )
        oh = cur.fetchone()
        if not oh:
            abort(404)

        cur.execute(
            """
            SELECT id, first_name, last_name, email, phone, working_with_agent, agent_name, submitted_at
            FROM open_house_signins
            WHERE open_house_id = %s AND user_id = %s
            ORDER BY submitted_at DESC
            """,
            (open_house_id, current_user.id),
        )
        signins = cur.fetchall()

        return render_template("openhouses/detail.html", openhouse=oh, signins=signins)

    finally:
        conn.close()

@app.route("/openhouse/<token>", methods=["GET", "POST"])
def openhouse_public_signin(token):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        cur.execute("""
            SELECT id, created_by_user_id, address_line1, city, state, zip, start_datetime, end_datetime, house_photo_url
            FROM open_houses
            WHERE public_token = %s
        """, (token,))
        oh = cur.fetchone()
        if not oh:
            abort(404)
        
        open_house_id = oh["id"] if isinstance(oh, dict) else oh[0]
        owner_user_id = oh["created_by_user_id"] if isinstance(oh, dict) else oh[1]

        if request.method == "POST":
            first_name = (request.form.get("first_name") or "").strip()
            last_name = (request.form.get("last_name") or "").strip()
            email = normalize_email(request.form.get("email"))
            phone = normalize_phone(request.form.get("phone") or request.form.get("related_phone"))

            working_with_agent = request.form.get("working_with_agent")
            if working_with_agent == "yes":
                working_with_agent_bool = True
            elif working_with_agent == "no":
                working_with_agent_bool = False
            else:
                working_with_agent_bool = None

            agent_name = (request.form.get("agent_name") or "").strip() or None
            agent_phone = normalize_phone(request.form.get("agent_phone") or "")
            agent_brokerage = (request.form.get("agent_brokerage") or "").strip() or None

            # Optional bullets (must remain below agent question in template)
            looking_to_buy = truthy_checkbox(request.form.get("looking_to_buy"))
            looking_to_sell = truthy_checkbox(request.form.get("looking_to_sell"))
            timeline = (request.form.get("timeline") or "").strip() or None
            notes = (request.form.get("notes") or "").strip() or None
            consent_to_contact = truthy_checkbox(request.form.get("consent_to_contact"))

            if working_with_agent_bool is True and not agent_name:
                flash("If you are working with an agent, please enter the agent name.", "danger")
                return render_template(
                    "public/openhouse_signin.html",
                    openhouse=oh,
                    hide_nav=True
                )

            # Match or create contact (scoped to this open house owner)
            contact_id = None

            if email:
                cur.execute("""
                    SELECT id
                    FROM contacts
                    WHERE user_id = %s AND LOWER(email) = %s
                    LIMIT 1
                """, (owner_user_id, email))
                r = cur.fetchone()
                if r:
                    contact_id = r["id"] if isinstance(r, dict) else r[0]
            
            if not contact_id and phone:
                cur.execute("""
                    SELECT id
                    FROM contacts
                    WHERE user_id = %s AND phone = %s
                    LIMIT 1
                """, (owner_user_id, phone))
                r = cur.fetchone()
                if r:
                    contact_id = r["id"] if isinstance(r, dict) else r[0]

            if contact_id:
                cur.execute("""
                    UPDATE contacts
                    SET working_with_agent = %s,
                        agent_name = %s,
                        agent_phone = %s,
                        agent_brokerage = %s,
                        lead_source = COALESCE(lead_source, 'Open House'),
                        last_open_house_id = %s
                    WHERE id = %s AND user_id = %s
                """, (working_with_agent_bool, agent_name, agent_phone, agent_brokerage, open_house_id, contact_id, owner_user_id))

            else:
                full_name = f"{first_name} {last_name}".strip()
                cur.execute("""
                    INSERT INTO contacts
                      (user_id, name, first_name, last_name, email, phone, working_with_agent, agent_name, agent_phone, agent_brokerage, lead_source, last_open_house_id)
                    VALUES
                      (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (owner_user_id, full_name, first_name, last_name, email, phone, working_with_agent_bool, agent_name, agent_phone, agent_brokerage, "Open House", open_house_id))
                r = cur.fetchone()
                contact_id = r["id"] if isinstance(r, dict) else r[0]

            cur.execute("""
                INSERT INTO open_house_signins
                  (open_house_id, user_id, contact_id,
                   first_name, last_name, email, phone,
                   working_with_agent, agent_name, agent_phone, agent_brokerage,
                   looking_to_buy, looking_to_sell, timeline, notes, consent_to_contact)
                VALUES
                  (%s, %s, %s,
                   %s, %s, %s, %s,
                   %s, %s, %s, %s,
                   %s, %s, %s, %s, %s)
            """, (
                open_house_id,
                owner_user_id,   # ← THIS is the important addition
                contact_id,
                first_name,
                last_name,
                email,
                phone,
                working_with_agent_bool,
                agent_name,
                agent_phone,
                agent_brokerage,
                looking_to_buy,
                looking_to_sell,
                timeline,
                notes,
                consent_to_contact
            ))

            conn.commit()
            flash("Thanks. You are signed in.", "success")
            return redirect(url_for("openhouse_public_signin", token=token))

        return render_template(
            "public/openhouse_signin.html",
            openhouse=oh,
            hide_nav=True
        )

    finally:
        conn.close()

@app.route("/openhouse-privacy")
def openhouse_privacy():
    return_url = request.args.get("return")
    return render_template(
        "public/openhouse_privacy.html",
        hide_nav=True,
        return_url=return_url
    )

@app.route("/openhouses/<int:open_house_id>/export.csv")
@login_required
def openhouse_export_csv(open_house_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        cur.execute(
            "SELECT id FROM open_houses WHERE id = %s AND created_by_user_id = %s",
            (open_house_id, current_user.id),
        )
        if not cur.fetchone():
            abort(404)

        cur.execute(
            """
            SELECT
              submitted_at,
              first_name, last_name, email, phone,
              working_with_agent, agent_name, agent_phone, agent_brokerage,
              looking_to_buy, looking_to_sell, timeline, notes, consent_to_contact
            FROM open_house_signins
            WHERE open_house_id = %s AND user_id = %s
            ORDER BY submitted_at ASC
            """,
            (open_house_id, current_user.id),
        )
        rows = cur.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "submitted_at",
            "first_name", "last_name", "email", "phone",
            "working_with_agent", "agent_name", "agent_phone", "agent_brokerage",
            "looking_to_buy", "looking_to_sell", "timeline", "notes", "consent_to_contact"
        ])

        for r in rows:
            writer.writerow([
                r["submitted_at"],
                r["first_name"], r["last_name"], r["email"], r["phone"],
                r["working_with_agent"], r["agent_name"], r["agent_phone"], r["agent_brokerage"],
                r["looking_to_buy"], r["looking_to_sell"], r["timeline"], r["notes"], r["consent_to_contact"]
            ])

        csv_data = output.getvalue()
        output.close()

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=open_house_{open_house_id}_signins.csv"}
        )

    finally:
        conn.close()

@app.route("/newsletter/signup/<public_token>", methods=["GET", "POST"])
def newsletter_signup(public_token):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, created_by_user_id, title, redirect_url, is_active
        FROM newsletter_signup_links
        WHERE public_token = %s
        """,
        (public_token,)
    )
    link = cur.fetchone()

    if not link or not link["is_active"]:
        conn.close()
        abort(404)

    if request.method == "GET":
        conn.close()
        return render_template(
            "newsletter/signup.html",
            page_title=link["title"],
            public_token=public_token
        )

    # POST
    first_name = (request.form.get("first_name") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()
    email = _normalize_email(request.form.get("email"))
    resident_flag = (request.form.get("is_resident") or "").strip()  # "yes" or "no" or ""

    if not email or "@" not in email:
        conn.close()
        return render_template(
            "newsletter/signup.html",
            page_title=link["title"],
            public_token=public_token,
            error="Please enter a valid email address."
        )

    # Find existing contact by email for the owner of this link
    user_id = link["created_by_user_id"]

    cur.execute(
        """
        SELECT id
        FROM contacts
        WHERE user_id = %s AND lower(email) = %s
        """,
        (user_id, email)
    )
    existing = cur.fetchone()

    now_ts = datetime.now()

    if existing:
        contact_id = existing["id"]
        cur.execute(
            """
            UPDATE contacts
            SET first_name = COALESCE(NULLIF(%s, ''), first_name),
                last_name = COALESCE(NULLIF(%s, ''), last_name),
                newsletter_opt_in = true,
                newsletter_opt_in_date = COALESCE(newsletter_opt_in_date, %s),
                newsletter_source = COALESCE(newsletter_source, 'Keyport Newsletter Signup')
            WHERE id = %s AND user_id = %s
            """,
            (first_name, last_name, now_ts, contact_id, user_id)
        )
    else:
        # Put resident info into notes for MVP (no schema change needed)
        notes = None
        if resident_flag in ("yes", "no"):
            notes = f"Newsletter signup. Keyport resident: {resident_flag}."

        cur.execute(
            """
            INSERT INTO contacts (user_id, first_name, last_name, email, notes, newsletter_opt_in, newsletter_opt_in_date, newsletter_source)
            VALUES (%s, NULLIF(%s,''), NULLIF(%s,''), %s, %s, true, %s, 'Keyport Newsletter Signup')
            RETURNING id
            """,
            (user_id, first_name, last_name, email, notes, now_ts)
        )
        row = cur.fetchone()
        contact_id = row["id"] if row else None

    # Defensive guard
    if not contact_id:
        conn.rollback()
        conn.close()
        return render_template(
            "newsletter/signup.html",
            page_title=link["title"],
            public_token=public_token,
            error="Sorry, something went wrong. Please try again."
        )

    # Optional: log engagement (only if your engagements table supports it)
    # Adjust columns to match your schema if needed.
    try:
        cur.execute(
            """
            INSERT INTO engagements (user_id, contact_id, engagement_type, summary, occurred_at, created_at)
            VALUES (%s, %s, 'newsletter_signup', 'Signed up for Keyport newsletter', %s, now())
            """,
            (user_id, contact_id, now_ts)
        )
    except Exception:
        # Do not fail the signup if engagement logging is not compatible
        conn.rollback()
        # Re-apply the contact change if rollback happened
        conn.close()
        return redirect(url_for("newsletter_thanks", public_token=public_token))

    conn.commit()
    conn.close()

    # Redirect to Substack subscribe page if configured
    if link["redirect_url"]:
        return redirect(link["redirect_url"])

    return redirect(url_for("newsletter_thanks", public_token=public_token))


@app.route("/newsletter/thanks/<public_token>")
def newsletter_thanks(public_token):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT title, redirect_url, is_active
        FROM newsletter_signup_links
        WHERE public_token = %s
        """,
        (public_token,)
    )
    link = cur.fetchone()
    conn.close()

    if not link or not link["is_active"]:
        abort(404)

    return render_template(
        "newsletter/thanks.html",
        page_title=link["title"],
        redirect_url=link["redirect_url"]
    )

@app.route("/api/reminders/due")
@login_required
def api_reminders_due():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT i.id,
               i.notes,
               i.due_at,
               c.first_name,
               c.last_name
        FROM interactions i
        JOIN contacts c
          ON i.contact_id = c.id
         AND c.user_id = %s
        WHERE i.user_id = %s
          AND i.due_at IS NOT NULL
          AND i.due_at <= NOW()
          AND i.due_at >= NOW() - INTERVAL '10 minutes'
          AND i.is_completed = FALSE
          AND (i.notified IS FALSE OR i.notified IS NULL)
        """,
        (current_user.id, current_user.id),
    )
    rows = cur.fetchall()

    # rows is a list of dicts, so use keys not indexes
    interaction_ids = [row["id"] for row in rows]
    if interaction_ids:
        cur.execute(
            """
            UPDATE interactions
            SET notified = TRUE
            WHERE user_id = %s
              AND id = ANY(%s::int[])
            """,
            (current_user.id, interaction_ids),
        )
        conn.commit()

    reminders = []
    for row in rows:
        interaction_id = row["id"]
        notes = row["notes"] or ""
        due_at = row["due_at"]
        first_name = row["first_name"] or ""
        last_name = row["last_name"] or ""
        contact_name = (first_name + " " + last_name).strip()

        reminders.append(
            {
                "id": interaction_id,
                "title": notes,
                "due_at": due_at.isoformat() if due_at else None,
                "contact_name": contact_name,
            }
        )

    conn.close()
    return jsonify(reminders)

@app.route("/followups.ics")
def followups_ics():
    """
    Calendar feed of upcoming follow-ups.
    Subscribe to: https://<your-domain>/followups.ics?key=YOUR_ICS_TOKEN
    """
    if ICS_TOKEN:
        key = request.args.get("key", "")
        if key != ICS_TOKEN:
            return Response("Unauthorized", status=401, mimetype="text/plain")
    """
    Calendar feed of upcoming follow-ups.
    Subscribe to: https://<your-domain>/followups.ics
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            id,
            name,
            first_name,
            last_name,
            next_follow_up,
            next_follow_up_time,
            pipeline_stage,
            priority,
            target_area
        FROM contacts
        WHERE next_follow_up IS NOT NULL
          AND next_follow_up <> ''
        ORDER BY next_follow_up, name
        """
    )
    rows = cur.fetchall()
    conn.close()

    lines = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//Ulysses CRM//EN")

    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    for row in rows:
        date_str = row["next_follow_up"]
        if not date_str:
            continue

        display_name = row["name"]
        fn = row.get("first_name") or ""
        ln = row.get("last_name") or ""
        full = (fn + " " + ln).strip()
        if full:
            display_name = full

        summary = f"Follow up: {display_name}"

        desc_parts = []
        if row.get("pipeline_stage"):
            desc_parts.append(f"Stage: {row['pipeline_stage']}")
        if row.get("priority"):
            desc_parts.append(f"Priority: {row['priority']}")
        if row.get("target_area"):
            desc_parts.append(f"Area: {row['target_area']}")

        description = "\\n".join(desc_parts) if desc_parts else ""

        uid = f"ulysses-followup-{row['id']}@ulyssescrm"

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{dtstamp}")
        lines.append(f"SUMMARY:{summary}")

        time_str = row.get("next_follow_up_time")

        if time_str:
            try:
                d_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                hh, mm = time_str.split(":")
                hh24 = int(hh)
                mm_int = int(mm)
                start_dt = datetime(d_obj.year, d_obj.month, d_obj.day, hh24, mm_int)
                end_dt = start_dt + timedelta(minutes=30)

                dtstart = start_dt.strftime("%Y%m%dT%H%M%S")
                dtend = end_dt.strftime("%Y%m%dT%H%M%S")

                lines.append(f"DTSTART:{dtstart}")
                lines.append(f"DTEND:{dtend}")
            except Exception:
                dtstart = date_str.replace("-", "")
                lines.append(f"DTSTART;VALUE=DATE:{dtstart}")
                lines.append(f"DTEND;VALUE=DATE:{dtstart}")
        else:
            dtstart = date_str.replace("-", "")
            lines.append(f"DTSTART;VALUE=DATE:{dtstart}")
            lines.append(f"DTEND;VALUE=DATE:{dtstart}")

        if description:
            lines.append(f"DESCRIPTION:{description}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    ics_text = "\r\n".join(lines) + "\r\n"

    return Response(ics_text, mimetype="text/calendar")


@app.route("/delete/<int:contact_id>", methods=["POST"])
@login_required
def delete_contact(contact_id):
    """
    Backward compatible safety shim.
    This route used to hard-delete contacts. It now archives them.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE contacts
            SET archived_at = %s
            WHERE id = %s AND user_id = %s AND archived_at IS NULL
            """,
            (datetime.utcnow(), contact_id, current_user.id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            abort(404)
        conn.commit()
    finally:
        conn.close()

    flash("Contact archived. This did not delete any data.", "success")
    return redirect(url_for("contacts"))

@app.route("/contacts/<int:contact_id>/archive", methods=["POST"])
@login_required
def archive_contact(contact_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE contacts
            SET archived_at = %s
            WHERE id = %s AND user_id = %s AND archived_at IS NULL
            """,
            (datetime.utcnow(), contact_id, current_user.id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            abort(404)
        conn.commit()
    finally:
        conn.close()

    flash("Contact archived. You can unarchive at any time.", "success")
    return redirect(url_for("edit_contact", contact_id=contact_id))


@app.route("/contacts/<int:contact_id>/unarchive", methods=["POST"])
@login_required
def unarchive_contact(contact_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE contacts
            SET archived_at = NULL
            WHERE id = %s AND user_id = %s AND archived_at IS NOT NULL
            """,
            (contact_id, current_user.id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            abort(404)
        conn.commit()
    finally:
        conn.close()

    flash("Contact unarchived. Restored to active workflows.", "success")
    return redirect(url_for("edit_contact", contact_id=contact_id))

@app.route("/api/listing-checklist/<int:item_id>/update", methods=["POST"])
@login_required
def update_listing_checklist_item(item_id):
    is_complete = request.form.get("is_complete") == "true"
    due_date = request.form.get("due_date") or None

    completed_at = datetime.utcnow() if is_complete else None

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE listing_checklist_items
        SET is_complete = %s,
            due_date = %s,
            completed_at = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (is_complete, due_date, completed_at, item_id)
    )
    conn.commit()
    conn.close()

    return jsonify(success=True)

@app.route("/contact/<int:contact_id>/special-dates/add", methods=["POST"])
@login_required
def add_special_date(contact_id):
    label = (request.form.get("label") or "").strip()
    special_date = (request.form.get("special_date") or "").strip()
    notes = (request.form.get("notes") or "").strip()
    is_recurring = True if request.form.get("is_recurring") == "on" else False

    if not label or not special_date:
        flash("Please provide a label and a date.", "warning")
        return redirect(url_for("edit_contact", contact_id=contact_id))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO contact_special_dates (contact_id, label, special_date, is_recurring, notes)
        VALUES (%s, %s, %s, %s, %s)
    """, (contact_id, label, special_date, is_recurring, notes))
    conn.commit()
    conn.close()

    flash("Special date saved.", "success")
    return redirect(url_for("edit_contact", contact_id=contact_id))


@app.route("/special-dates/<int:special_date_id>/delete", methods=["POST"])
@login_required
def delete_special_date(special_date_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT contact_id FROM contact_special_dates WHERE id = %s", (special_date_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        flash("Special date not found.", "warning")
        return redirect(url_for("contacts"))

    contact_id = row["contact_id"] if isinstance(row, dict) else row[0]

    cur.execute("DELETE FROM contact_special_dates WHERE id = %s", (special_date_id,))
    conn.commit()
    conn.close()

    flash("Special date deleted.", "success")
    return redirect(url_for("edit_contact", contact_id=contact_id))

@app.route("/api/add_interaction", methods=["POST"])
@login_required
def api_add_interaction():
    """
    Lightweight API endpoint so macOS/iOS Shortcuts can log interactions.

    Expected JSON body fields (all optional except kind and one of contact_id/email/phone):

    {
      "contact_id": 123,          # or
      "email": "client@example.com",
      "phone": "+1 (732) 555-1212",
      "kind": "Text",             # Call, Text, Email, Meeting, Other
      "happened_at": "2025-12-06",
      "time_of_day": "3:15 PM",
      "notes": "Followed up about listing appointment"
    }
    """
    if SHORTCUT_API_KEY:
        api_key = request.headers.get("X-API-Key", "")
        if api_key != SHORTCUT_API_KEY:
            return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}

    kind = (data.get("kind") or "Other").strip()
    if not kind:
        kind = "Other"

    contact_id = data.get("contact_id")
    email = (data.get("email") or "").strip().lower()
    phone_raw = (data.get("phone") or "").strip()
    phone_digits = normalize_phone_digits(phone_raw)

    if not contact_id and not email and not phone_digits:
        return jsonify(
            {"error": "Must provide contact_id or email or phone to match a contact"}
        ), 400

    conn = get_db()
    cur = conn.cursor()
    
    try:
        contact_row = None
    
        if contact_id:
            cur.execute(
                "SELECT id FROM contacts WHERE id = %s AND user_id = %s",
                (contact_id, current_user.id),
            )
            contact_row = cur.fetchone()
    
        if not contact_row and email:
            cur.execute(
                "SELECT id FROM contacts WHERE user_id = %s AND lower(email) = %s LIMIT 1",
                (current_user.id, email),
            )
            contact_row = cur.fetchone()
    
        if not contact_row and phone_digits:
            cur.execute(
                """
                SELECT id
                FROM contacts
                WHERE user_id = %s
                  AND regexp_replace(coalesce(phone, ''), '\\D', '', 'g') = %s
                LIMIT 1
                """,
                (current_user.id, phone_digits),
            )
            contact_row = cur.fetchone()
    
        if not contact_row:
            return jsonify({"error": "Contact not found"}), 404
    
        cid = contact_row["id"]
    
        happened_at = data.get("happened_at") or date.today().isoformat()
        time_of_day = (data.get("time_of_day") or "").strip() or None
        notes = (data.get("notes") or "").strip()
    
        cur.execute(
            """
            INSERT INTO interactions (user_id, contact_id, kind, happened_at, time_of_day, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (current_user.id, cid, kind, happened_at, time_of_day, notes),
        )
        conn.commit()
    
        return jsonify({"status": "ok", "contact_id": cid})
    
    except Exception:
        return jsonify({"error": "Database error"}), 500
    
    finally:
        conn.close()
    
ALLOWED_DELIVERY_TYPES = {"email", "text", "either"}

def _render_template_body(raw: str, client_name: str, agent_name: str, brokerage_footer: str) -> str:
    # Simple, safe substitution only for the three allowed tokens
    out = (raw or "")
    out = out.replace("{{client_name}}", client_name or "")
    out = out.replace("{{agent_name}}", agent_name or "")
    out = out.replace("{{brokerage_footer}}", brokerage_footer or "")
    return out

def _get_brokerage_footer() -> str:
    """
    Returns a multi-line footer block for templates.
    Pulls from users + brokerages (by user_id). Falls back to safe defaults.
    """
    # Agent identity
    agent_name = " ".join([p for p in [current_user.first_name, current_user.last_name] if p]).strip()
    agent_name = agent_name or (current_user.email or "Agent")

    title = (getattr(current_user, "title", None) or "").strip() or None
    agent_phone = (getattr(current_user, "agent_phone", None) or "").strip() or None
    agent_website = (getattr(current_user, "agent_website", None) or "").strip() or None
    license_number = (getattr(current_user, "license_number", None) or "").strip() or None

    b = None
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  brokerage_name,
                  address1,
                  address2,
                  city,
                  state,
                  zip,
                  brokerage_phone,
                  brokerage_website,
                  office_license_number
                FROM brokerages
                WHERE user_id = %s
                LIMIT 1;
                """,
                (current_user.id,),
            )
            b = cur.fetchone()
    finally:
        conn.close()

    lines = []

    # Line 1: Agent name
    lines.append(agent_name)

    # Line 2: title (optional)
    if title:
        lines.append(title)

    # Brokerage name
    if b and (b.get("brokerage_name") or "").strip():
        lines.append(b["brokerage_name"].strip())

    # Brokerage address line(s)
    if b:
        addr1 = (b.get("address1") or "").strip()
        addr2 = (b.get("address2") or "").strip()
        city = (b.get("city") or "").strip()
        state = (b.get("state") or "").strip()
        zip_code = (b.get("zip") or "").strip()

        if addr1:
            lines.append(addr1)
        if addr2:
            lines.append(addr2)

        city_state_zip_parts = []
        
        if city:
            city_state_zip_parts.append(city)
        
        state_zip = " ".join(p for p in [state, zip_code] if p)
        if state_zip:
            city_state_zip_parts.append(state_zip)
        
        if city_state_zip_parts:
            lines.append(", ".join(city_state_zip_parts))

    # Contact / web (agent first, per your decision)
    if agent_phone:
        lines.append(agent_phone)
    if agent_website:
        lines.append(agent_website)

    # License info (optional)
    # (We can format this differently later, but this is safe + simple.)
    if license_number:
        lines.append(f"License: {license_number}")

    # Brokerage extras (optional)
    if b:
        brokerage_phone = (b.get("brokerage_phone") or "").strip()
        brokerage_website = (b.get("brokerage_website") or "").strip()
        office_license_number = (b.get("office_license_number") or "").strip()

        if brokerage_phone:
            lines.append(f"Office: {brokerage_phone}")
        if brokerage_website:
            lines.append(brokerage_website)
        if office_license_number:
            lines.append(f"Office License: {office_license_number}")

    # Final fallback if the user has basically nothing filled out
    if not lines:
        return "Brokerage information not set"

    return "\n".join(lines)

@app.route("/templates")
@login_required
def templates_index():
    q = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    delivery_type = (request.args.get("delivery_type") or "").strip()
    status = (request.args.get("status") or "").strip()  # locked | draft | ""

    tab = (request.args.get("tab") or "all").strip().lower()
    if tab == "draft":
        status = "draft"
    elif tab == "locked":
        status = "locked"

    where = []
    params = []

    # Tenant boundary (always)
    where.append("user_id = %s")
    params.append(current_user.id)

    # Always hide archived templates by default
    where.append("archived_at IS NULL")

    if q:
        where.append("(title ILIKE %s OR body ILIKE %s OR notes ILIKE %s)")
        like = f"%{q}%"
        params += [like, like, like]

    if category:
        where.append("category = %s")
        params.append(category)

    if delivery_type:
        where.append("delivery_type = %s")
        params.append(delivery_type)

    if status == "locked":
        where.append("is_locked = TRUE")
    elif status == "draft":
        where.append("is_locked = FALSE")

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    conn = get_db()
    try:
        cur = conn.cursor()

        # Category dropdown options must also be tenant-scoped
        cur.execute(
            """
            SELECT DISTINCT category
            FROM templates
            WHERE user_id = %s
              AND archived_at IS NULL
            ORDER BY category ASC;
            """,
            (current_user.id,),
        )
        categories = [r["category"] for r in (cur.fetchall() or [])]

        # Main list query must be tenant-scoped via where_sql
        cur.execute(
            f"""
            SELECT
                id,
                title,
                category,
                delivery_type,
                is_locked,
                created_at,
                updated_at
            FROM templates
            {where_sql}
            ORDER BY updated_at DESC, id DESC;
            """,
            params,
        )
        rows = cur.fetchall() or []

        templates = []
        for r in rows:
            templates.append(
                {
                    "id": r["id"],
                    "title": r["title"],
                    "category": r["category"],
                    "delivery_type": r["delivery_type"],
                    "is_locked": r["is_locked"],
                    "updated_at": r["updated_at"],
                }
            )

        return render_template(
            "templates/index.html",
            templates=templates,
            categories=categories,
            q=q,
            selected_category=category,
            selected_delivery_type=delivery_type,
            selected_status=status,
        )
    finally:
        conn.close()


@app.route("/templates/new", methods=["GET", "POST"])
@login_required
def templates_new():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        category = (request.form.get("category") or "General").strip() or "General"
        delivery_type = (request.form.get("delivery_type") or "either").strip() or "either"
        body = (request.form.get("body") or "").strip()
        notes = (request.form.get("notes") or "").strip()

        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("templates_new"))

        if delivery_type not in ALLOWED_DELIVERY_TYPES:
            delivery_type = "either"

        conn = conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO templates (
                user_id,
                title, category, delivery_type, body, notes,
                is_locked, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, NOW(), NOW())
            RETURNING id;
            """,
            (current_user.id, title, category, delivery_type, body, notes)
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        conn.close()

        flash("Template created.", "success")
        return redirect(url_for("templates_view", template_id=new_id))

    return render_template("templates/edit.html", mode="new", t=None)

@app.route("/templates/<int:template_id>")
@login_required
def templates_view(template_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, category, delivery_type, body, notes, is_locked, created_at, updated_at
        FROM templates
        WHERE id = %s AND user_id = %s;
        """,
        (template_id, current_user.id)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        abort(404)

    t = {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "delivery_type": row["delivery_type"],
        "body": row["body"],
        "notes": row["notes"],
        "is_locked": row["is_locked"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

    # Optional: populate preview with a selected contact
    contact_id = request.args.get("contact_id", type=int)
    selected_contact = None
    
    client_name = "Client Name"
    c = None  # important
    
    if contact_id:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
              id,
              COALESCE(
                NULLIF(TRIM(name), ''),
                NULLIF(TRIM(CONCAT_WS(' ', first_name, last_name)), ''),
                email,
                'Client'
              ) AS display_name
            FROM contacts
            WHERE user_id = %s
              AND id = %s
            LIMIT 1;
            """,
            (current_user.id, contact_id),
        )
        c = cur.fetchone()
        conn.close()
    
    if c:
        selected_contact = {"id": c["id"], "name": c["display_name"]}
        client_name = c["display_name"]

    # Agent name (match your User model: first_name/last_name/email)
    agent_name = " ".join([p for p in [current_user.first_name, current_user.last_name] if p]) or current_user.email or "Agent Name"
    brokerage_footer = _get_brokerage_footer()

    preview = _render_template_body(
        t["body"],
        client_name=client_name,
        agent_name=agent_name,
        brokerage_footer=brokerage_footer
    )

    return render_template(
        "templates/view.html",
        t=t,
        preview=preview,
        selected_contact=selected_contact
    )

@app.route("/templates/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
def templates_edit(template_id):
    conn = conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, category, delivery_type, body, notes, is_locked
        FROM templates
        WHERE id = %s AND user_id = %s;
        """,
        (template_id, current_user.id)
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        abort(404)

    t = {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "delivery_type": row["delivery_type"],
        "body": row["body"],
        "notes": row["notes"],
        "is_locked": row["is_locked"],
    }

    if t["is_locked"]:
        conn.close()
        flash("This template is locked. Duplicate it to create an editable version.", "warning")
        return redirect(url_for("templates_view", template_id=template_id))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        category = (request.form.get("category") or "General").strip() or "General"
        delivery_type = (request.form.get("delivery_type") or "either").strip() or "either"
        body = (request.form.get("body") or "").strip()
        notes = (request.form.get("notes") or "").strip()

        if not title:
            conn.close()
            flash("Title is required.", "danger")
            return redirect(url_for("templates_edit", template_id=template_id))

        if delivery_type not in ALLOWED_DELIVERY_TYPES:
            delivery_type = "either"

        cur.execute(
            """
            UPDATE templates
            SET title = %s,
                category = %s,
                delivery_type = %s,
                body = %s,
                notes = %s,
                updated_at = NOW()
            WHERE id = %s AND user_id = %s;
            """,
            (title, category, delivery_type, body, notes, template_id, current_user.id)
        )
        conn.commit()
        conn.close()

        flash("Template updated.", "success")
        return redirect(url_for("templates_view", template_id=template_id))

    conn.close()
    return render_template("templates/edit.html", mode="edit", t=t)

@app.route("/templates/<int:template_id>/lock", methods=["POST"])
@login_required
def templates_lock(template_id):
    conn = conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT is_locked FROM templates WHERE id = %s AND user_id = %s;",
        (template_id, current_user.id),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        abort(404)

    if row["is_locked"]:
        conn.close()
        flash("Template is already locked.", "info")
        return redirect(url_for("templates_view", template_id=template_id))

    cur.execute(
        "UPDATE templates SET is_locked = TRUE, updated_at = NOW() WHERE id = %s AND user_id = %s;",
        (template_id, current_user.id),
    )
    conn.commit()
    conn.close()

    flash("Template locked.", "success")
    return redirect(url_for("templates_view", template_id=template_id))

@app.route("/templates/<int:template_id>/duplicate", methods=["POST"])
@login_required
def templates_duplicate(template_id):
    conn = conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT title, category, delivery_type, body, notes
        FROM templates
        WHERE id = %s AND user_id = %s;
        """,
        (template_id, current_user.id)
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        abort(404)

    title = row["title"]
    category = row["category"]
    delivery_type = row["delivery_type"]
    body = row["body"]
    notes = row["notes"]
    new_title = f"{title} (Copy)"

    cur.execute(
        """
        INSERT INTO templates (
            user_id,
            title, category, delivery_type, body, notes,
            is_locked, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, FALSE, NOW(), NOW())
        RETURNING id;
        """,
        (current_user.id, new_title, category, delivery_type, body, notes)
    )
    new_id = cur.fetchone()["id"]
    conn.commit()
    conn.close()

    flash("Template duplicated. You can now edit the copy.", "success")
    return redirect(url_for("templates_edit", template_id=new_id))

@app.route("/api/contacts/search")
@login_required
def api_contacts_search():
    q = (request.args.get("q") or "").strip()
    limit = 10

    if not q or len(q) < 2:
        return jsonify([])

    like = f"%{q}%"

    conn = get_db()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                id,
                COALESCE(
                    NULLIF(TRIM(name), ''),
                    NULLIF(TRIM(CONCAT_WS(' ', first_name, last_name)), ''),
                    email,
                    'Unnamed'
                ) AS display_name,
                COALESCE(email, '') AS email
            FROM contacts
            WHERE user_id = %s
              AND (
                  name ILIKE %s
                  OR first_name ILIKE %s
                  OR last_name ILIKE %s
                  OR email ILIKE %s
              )
            ORDER BY last_name NULLS LAST, first_name NULLS LAST, id DESC
            LIMIT %s;
            """,
            (current_user.id, like, like, like, like, limit),
        )

        rows = cur.fetchall() or []

        results = []
        for r in rows:
            results.append(
                {
                    "id": r["id"],
                    "name": r["display_name"],
                    "email": r.get("email") or "",
                }
            )

        return jsonify(results)

    finally:
        conn.close()

@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    conn = get_db()
    try:
        cur = conn.cursor()

        if request.method == "POST":
            # Users (agent) fields (match template field names)
            first_name = (request.form.get("first_name") or "").strip()
            last_name = (request.form.get("last_name") or "").strip()
            title = (request.form.get("title") or "").strip()
            agent_phone = (request.form.get("agent_phone") or "").strip()
            agent_website = (request.form.get("agent_website") or "").strip()
            license_number = (request.form.get("license_number") or "").strip()
            license_state = (request.form.get("license_state") or "").strip()

            # Brokerage fields (match template field names)
            brokerage_name = (request.form.get("brokerage_name") or "").strip()
            address1 = (request.form.get("address1") or "").strip()
            address2 = (request.form.get("address2") or "").strip()
            city = (request.form.get("city") or "").strip()
            state = (request.form.get("state") or "").strip()
            zip_code = (request.form.get("zip") or "").strip()
            brokerage_phone = (request.form.get("brokerage_phone") or "").strip()
            brokerage_website = (request.form.get("brokerage_website") or "").strip()
            office_license_number = (request.form.get("office_license_number") or "").strip()

            try:
                # Update users without overwriting with blanks
                cur.execute(
                    """
                    UPDATE users
                    SET
                        first_name = COALESCE(NULLIF(%s, ''), first_name),
                        last_name = COALESCE(NULLIF(%s, ''), last_name),
                        title = COALESCE(NULLIF(%s, ''), title),
                        agent_phone = COALESCE(NULLIF(%s, ''), agent_phone),
                        agent_website = COALESCE(NULLIF(%s, ''), agent_website),
                        license_number = COALESCE(NULLIF(%s, ''), license_number),
                        license_state = COALESCE(NULLIF(%s, ''), license_state)
                    WHERE id = %s
                    """,
                    (
                        first_name,
                        last_name,
                        title,
                        agent_phone,
                        agent_website,
                        license_number,
                        license_state,
                        current_user.id,
                    ),
                )

                # Upsert brokerages without overwriting with blanks
                cur.execute(
                    """
                    INSERT INTO brokerages (
                        user_id,
                        brokerage_name, address1, address2, city, state, zip,
                        brokerage_phone, brokerage_website, office_license_number,
                        created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET
                        brokerage_name = COALESCE(NULLIF(EXCLUDED.brokerage_name, ''), brokerages.brokerage_name),
                        address1 = COALESCE(NULLIF(EXCLUDED.address1, ''), brokerages.address1),
                        address2 = COALESCE(NULLIF(EXCLUDED.address2, ''), brokerages.address2),
                        city = COALESCE(NULLIF(EXCLUDED.city, ''), brokerages.city),
                        state = COALESCE(NULLIF(EXCLUDED.state, ''), brokerages.state),
                        zip = COALESCE(NULLIF(EXCLUDED.zip, ''), brokerages.zip),
                        brokerage_phone = COALESCE(NULLIF(EXCLUDED.brokerage_phone, ''), brokerages.brokerage_phone),
                        brokerage_website = COALESCE(NULLIF(EXCLUDED.brokerage_website, ''), brokerages.brokerage_website),
                        office_license_number = COALESCE(NULLIF(EXCLUDED.office_license_number, ''), brokerages.office_license_number),
                        updated_at = NOW()
                    """,
                    (
                        current_user.id,
                        brokerage_name, address1, address2, city, state, zip_code,
                        brokerage_phone, brokerage_website, office_license_number,
                    ),
                )

                conn.commit()
                flash("Profile updated.", "success")
                return redirect(url_for("account"))

            except Exception as e:
                conn.rollback()
                flash(f"Error saving profile: {e}", "danger")

        # GET: fetch user + brokerage
        cur.execute(
            """
            SELECT id, email, first_name, last_name, title,
                   agent_phone, agent_website, license_number, license_state
            FROM users
            WHERE id = %s;
            """,
            (current_user.id,),
        )
        u = cur.fetchone()

        cur.execute(
            """
            SELECT brokerage_name, address1, address2, city, state, zip,
                   brokerage_phone, brokerage_website, office_license_number
            FROM brokerages
            WHERE user_id = %s;
            """,
            (current_user.id,),
        )
        b = cur.fetchone()

        return render_template(
            "account/profile.html",
            user=u,
            brokerage=b or {},
            active_page=None
        )

    finally:
        conn.close()

    

if __name__ == "__main__":
    init_db()
    app.run(debug=False)
