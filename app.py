import os
import re
import secrets
import csv
import io

from version import APP_VERSION
from functools import wraps
from datetime import date, datetime, timedelta, time
from math import ceil

from engagements import (
    list_engagements_for_contact,
    insert_engagement,
    delete_engagement,
)

from dotenv import load_dotenv
load_dotenv()

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

from werkzeug.security import check_password_hash

import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

@app.context_processor
def inject_app_version():
    return {"APP_VERSION": APP_VERSION}

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
                            
@app.context_processor
def inject_calendar_feed_url():
    calendar_url = url_for("followups_ics")
    if ICS_TOKEN:
        calendar_url = calendar_url + f"?key={ICS_TOKEN}"
    return {"calendar_feed_url": calendar_url}

@app.context_processor
def inject_current_year():
    return {"current_year": datetime.now().year}

DATABASE_URL = os.environ.get("DATABASE_URL")
SHORTCUT_API_KEY = os.environ.get("SHORTCUT_API_KEY")  # optional shared secret

def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


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

def truthy_checkbox(value):
    return value in ("on", "true", "1", "yes")

def normalize_email(email: str) -> str:
    return (email or "").strip().lower()

def normalize_phone(phone: str) -> str:
    return (phone or "").strip()

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

def get_professionals_for_dropdown(category=None):
    """
    Return a list of professionals for dropdowns.
    Excludes blacklist. Orders by grade priority and then by name.
    If category is given (for example 'Attorney') filters to that category.
    """
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    base_sql = """
        SELECT id, name, company, phone, email, category, grade
        FROM professionals
        WHERE grade != %s
    """
    params = ['blacklist']

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

def init_db():
    conn = get_db()
    cur = conn.cursor()

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
            address_line TEXT NOT NULL,
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
          CASE
            WHEN ca.contact_id_primary = %s THEN ca.contact_id_related
            ELSE ca.contact_id_primary
          END AS other_contact_id,
          c.name AS other_name,
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
        ORDER BY c.name ASC
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
    "Past client",
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


def ensure_listing_checklist_initialized(contact_id: int) -> None:
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM listing_checklist_items WHERE contact_id = %s LIMIT 1",
        (contact_id,)
    )
    if cur.fetchone():
        conn.close()
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
        rows
    )

    conn.commit()
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


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        email = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, email, password_hash, first_name, last_name, role, is_active
            FROM users
            WHERE email = %s
            """,
            (email,),
        )
        row = cur.fetchone()

        if row and row["is_active"] and check_password_hash(row["password_hash"], password):
            login_user(User(row))

            cur.execute(
                "UPDATE users SET last_login_at = NOW() WHERE id = %s",
                (row["id"],),
            )
            conn.commit()

            cur.close()
            conn.close()

            next_url = request.args.get("next") or url_for("dashboard")
            return redirect(next_url)

        cur.close()
        conn.close()
        error = "Invalid username or password"

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
    ACTIVE_LIMIT = 60

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
            ORDER BY e.occurred_at DESC
            LIMIT 1
        ) le ON TRUE

        WHERE {contacts_scope_sql}
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

        LIMIT %s
    """

    # Interval param needs to be a string like '30 days'
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

    active_params += [ACTIVE_LIMIT]

    cur.execute(active_sql, tuple(active_params))
    active_rows = cur.fetchall()

    # Active reasons badges
    now_dt = datetime.now()
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
        if nf_date:
            if nf_date < today:
                badges.append("Follow-up overdue")
            elif nf_date == today:
                badges.append("Follow-up today")
            else:
                badges.append("Follow-up scheduled")

        row["active_reasons"] = badges
        active_contacts.append(row)

    # Recent engagements feed (last 10)
    recent_sql = f"""
        SELECT
            e.id,
            e.contact_id,
            c.name AS contact_name,
            e.engagement_type,
            e.occurred_at,
            e.outcome,
            e.summary_clean
        FROM engagements e
        JOIN contacts c ON c.id = e.contact_id
        WHERE {contacts_scope_sql}
        {"AND e.user_id = %s" if engagements_has_user else ""}
        ORDER BY e.occurred_at DESC
        LIMIT 10
    """
    recent_params = []
    recent_params += list(contacts_scope_params)
    if engagements_has_user:
        recent_params += [current_user.id]
    cur.execute(recent_sql, tuple(recent_params))
    recent_engagements = cur.fetchall()

    # Follow-ups with context (single query then split into overdue/upcoming in Python)
    followups_sql = f"""
        SELECT
            c.id AS contact_id,
            c.name,
            c.first_name,
            c.last_name,
            c.next_follow_up,
            c.next_follow_up_time,

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
            ORDER BY e.occurred_at DESC
            LIMIT 1
        ) le ON TRUE

        WHERE {contacts_scope_sql}
          AND c.next_follow_up IS NOT NULL
        ORDER BY c.next_follow_up ASC, c.name ASC
    """
    followups_params = []
    followups_params += list(contacts_scope_params)
    followups_params += list(engagements_scope_params)

    cur.execute(followups_sql, tuple(followups_params))
    followup_rows = cur.fetchall()

    conn.close()

    followups_overdue = []
    followups_upcoming = []

    for row in followup_rows:
        nf_date = _nf_to_date(row.get("next_follow_up"))
        if not nf_date:
            continue

        if nf_date < today:
            followups_overdue.append(row)
        else:
            if nf_date <= (today + timedelta(days=UPCOMING_DAYS)):
                followups_upcoming.append(row)

    return render_template(
        "dashboard.html",
        active_contacts=active_contacts,
        recent_engagements=recent_engagements,
        followups_overdue=followups_overdue,
        followups_upcoming=followups_upcoming,
        today=today_str,
        total_contacts=total_contacts,
        upcoming_days=UPCOMING_DAYS,
        active_days=ACTIVE_DAYS,
        active_page="dashboard",
    )

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

    # Build WHERE clause parts
    where_clauses = []
    params = []

    # Tabs mapped to your existing schema:
    # Buyers  -> lead_type = "Buyer"
    # Sellers -> lead_type = "Seller"
    # Leads   -> pipeline_stage in ["New lead", "Nurture", "Active", "Under contract", "Closed", "Lost"]
    # Past Clients -> pipeline_stage = "Past Client / Relationship"
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
    # tab == "all" has no extra filter

    # Search filter (name / email / phone / notes)
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

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

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
            notes
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
        today=today,
    )

def parse_follow_up_time_from_form():
    hour = request.form.get("next_follow_up_hour")
    minute = request.form.get("next_follow_up_minute")
    ampm = request.form.get("next_follow_up_ampm")

    # If any field is missing or blank, return None
    if not hour or not minute or not ampm:
        return None

    try:
        hour = int(hour)
        minute = int(minute)

        # Convert to 24-hour time
        if ampm == "PM" and hour != 12:
            hour += 12
        elif ampm == "AM" and hour == 12:
            hour = 0

        return time(hour, minute)
    except:
        return None


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
        "phone": (request.form.get("phone") or "").strip(),
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
            name, email, phone, lead_type, pipeline_stage, price_min, price_max,
            target_area, source, priority, last_contacted, next_follow_up, next_follow_up_time, notes,
            first_name, last_name,
            current_address, current_city, current_state, current_zip,
            subject_address, subject_city, subject_state, subject_zip
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s)
        RETURNING id
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
        ),
    )

    new_contact = cur.fetchone()
    new_id = new_contact["id"]

    conn.commit()
    conn.close()
    return redirect(url_for("edit_contact", contact_id=new_id))

@app.route("/edit/<int:contact_id>", methods=["GET", "POST"])
@login_required
def edit_contact(contact_id):
    conn = get_db()
    cur = conn.cursor()

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
            "phone": (request.form.get("phone") or "").strip(),
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
            WHERE id = %s
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
            ),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("edit_contact", contact_id=contact_id, saved=1))

    # GET: load contact and its interactions
    cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
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

    engagements = list_engagements_for_contact(conn, current_user.id, contact_id, limit=50)

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
        WHERE contact_id = %s AND user_id = %s
        ORDER BY COALESCE(expected_close_date, updated_at) DESC, id DESC
        LIMIT 5
        """,
        (contact_id, current_user.id),
    )
    transactions = cur.fetchall()
    
    # NEW: split interactions into open and completed
    cur.execute(
        """
        SELECT *
        FROM interactions
        WHERE contact_id = %s AND is_completed = FALSE
        ORDER BY happened_at DESC NULLS LAST, id DESC
        """,
        (contact_id,),
    )
    open_interactions = cur.fetchall()

    cur.execute(
        """
        SELECT *
        FROM interactions
        WHERE contact_id = %s AND is_completed = TRUE
        ORDER BY completed_at DESC NULLS LAST,
                 happened_at DESC NULLS LAST,
                 id DESC
        """,
        (contact_id,),
    )
    completed_interactions = cur.fetchall()

    #Load Special Dates
    cur.execute("""
        SELECT id, label, special_date, is_recurring, notes
        FROM contact_special_dates
        WHERE contact_id = %s
        ORDER BY special_date ASC, label ASC
        """, (contact_id,))
    special_dates = cur.fetchall()

    associations = get_contact_associations(conn, current_user.id, contact_id)

    conn.close()

    return render_template(
        "edit_contact.html",
        c=contact,
        associations=associations,
        engagements=engagements,
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
        transactions=transactions,
        transaction_statuses=TRANSACTION_STATUSES,
    )

@app.route("/contacts/search")
@login_required
def contacts_search():
    q = (request.args.get("q") or "").strip()
    conn = get_db()
    cur = conn.cursor()

    if not q:
        conn.close()
        return jsonify([])

    like = f"%{q}%"
    cur.execute(
        """
        SELECT id, name, email, phone
        FROM contacts
        WHERE user_id = %s
          AND (name ILIKE %s OR email ILIKE %s OR phone ILIKE %s)
        ORDER BY name ASC
        LIMIT 10
        """,
        (current_user.id, like, like, like),
    )
    rows = cur.fetchall()
    conn.close()
    return jsonify(rows)


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
    phone = (request.form.get("phone") or "").strip()
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

    # Create new contact
    cur.execute(
        """
        INSERT INTO contacts (user_id, name, first_name, last_name, email, phone)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (current_user.id, full_name, first_name, last_name, email, phone),
    )
    
    row = cur.fetchone()
    new_id = row["id"]
    
    create_contact_association(
        conn,
        current_user.id,
        contact_id,
        new_id,
        relationship_type,
    )
    
    conn.commit()
    conn.close()
    return redirect(next_url)
    

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
    )

    flash("Engagement added.", "success")
    return redirect(url_for("edit_contact", contact_id=contact_id))


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

@app.route("/engagements/<int:engagement_id>/edit", methods=["GET", "POST"])
@login_required
def edit_engagement(engagement_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, contact_id, engagement_type, occurred_at, outcome, notes, transcript_raw, summary_clean
        FROM engagements
        WHERE id = %s AND user_id = %s
        """,
        (engagement_id, current_user.id),
    )
    e = cur.fetchone()

    if not e:
        conn.close()
        return "Engagement not found", 404

    next_url = request.args.get("next") or request.form.get("next") or url_for("edit_contact", contact_id=e["contact_id"])

    if request.method == "POST":
        engagement_type = (request.form.get("engagement_type") or "call").strip()
        occurred_at_str = (request.form.get("occurred_at") or "").strip()
        outcome = (request.form.get("outcome") or "").strip() or None
        notes = (request.form.get("notes") or "").strip() or None
        transcript_raw = (request.form.get("transcript_raw") or "").strip() or None
        summary_clean = (request.form.get("summary_clean") or "").strip() or None

        occurred_at = e["occurred_at"]
        if occurred_at_str:
            try:
                occurred_at = datetime.strptime(occurred_at_str, "%Y-%m-%dT%H:%M")
            except Exception:
                pass

        cur.execute(
            """
            UPDATE engagements
            SET engagement_type = %s,
                occurred_at = %s,
                outcome = %s,
                notes = %s,
                transcript_raw = %s,
                summary_clean = %s,
                updated_at = now()
            WHERE id = %s AND user_id = %s
            """,
            (engagement_type, occurred_at, outcome, notes, transcript_raw, summary_clean, engagement_id, current_user.id),
        )
        conn.commit()
        conn.close()
        return redirect(next_url)

    conn.close()
    return render_template(
        "edit_engagement.html",
        e=e,
        next=next_url,
        active_page="contacts",
    )

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
        INSERT INTO interactions (contact_id, kind, happened_at, time_of_day, notes)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (contact_id, kind, happened_at, time_of_day, notes),
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
        "SELECT contact_id FROM interactions WHERE id = %s",
        (interaction_id,),
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
    phone = (request.form.get("related_phone") or "").strip()
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
    cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
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
            property_type = (request.form.get("property_type") or "").strip()
            timeframe = (request.form.get("timeframe") or "").strip()
            preapproval_status = (request.form.get("preapproval_status") or "").strip()
            lender_name = (request.form.get("lender_name") or "").strip()
            areas = (request.form.get("areas") or "").strip()
            property_types = (request.form.get("property_types") or "").strip()
            referral_source = (request.form.get("referral_source") or "").strip()
            notes = (request.form.get("notes") or "").strip()

            min_price = parse_int_or_none(request.form.get("min_price"))
            max_price = parse_int_or_none(request.form.get("max_price"))

            if buyer_profile:
                # Update existing buyer profile
                cur.execute(
                    """
                    UPDATE buyer_profiles
                    SET timeframe = %s,
                        min_price = %s,
                        max_price = %s,
                        areas = %s,
                        property_types = %s,
                        property_type = %s,
                        preapproval_status = %s,
                        lender_name = %s,
                        referral_source = %s,
                        notes = %s
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
                        notes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        pros_attorneys=pros_attorneys,
        pros_lenders=pros_lenders,
        pros_inspectors=pros_inspectors,
        
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
        phone = request.form.get("phone")
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
                    (name, company, phone, email, category, grade, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (name, company, phone, email, category, grade, notes),
            )
            conn.commit()
            flash("Professional saved.", "success")

        return redirect(url_for("professionals"))

    professionals_list = get_professionals_for_dropdown()
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
        phone = request.form.get("phone")
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

    cur.execute("SELECT * FROM professionals WHERE id = %s", (prof_id,))
    professional = cur.fetchone()
    if not professional:
        flash("Professional not found.", "danger")
        return redirect(url_for("professionals"))

    return render_template(
        "edit_professional.html",
        professional=professional,
        active_page="professionals"
    )

@app.route("/professionals/<int:prof_id>/delete", methods=["POST"])
@login_required
def delete_professional(prof_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM professionals WHERE id = %s", (prof_id,))
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
        seller_attorney_phone = (request.form.get("seller_attorney_phone") or "").strip()
        seller_attorney_referred = bool(request.form.get("seller_attorney_referred"))

        # Professionals - Lender
        seller_lender_name = (request.form.get("seller_lender_name") or "").strip()
        seller_lender_email = (request.form.get("seller_lender_email") or "").strip()
        seller_lender_phone = (request.form.get("seller_lender_phone") or "").strip()
        seller_lender_referred = bool(request.form.get("seller_lender_referred"))

        # Professionals - Home Inspector
        seller_inspector_name = (request.form.get("seller_inspector_name") or "").strip()
        seller_inspector_email = (request.form.get("seller_inspector_email") or "").strip()
        seller_inspector_phone = (request.form.get("seller_inspector_phone") or "").strip()
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
    pros_attorneys = get_professionals_for_dropdown(category="Attorney")
    pros_lenders = get_professionals_for_dropdown(category="Lender")
    pros_inspectors = get_professionals_for_dropdown(category="Inspector")

    ensure_listing_checklist_initialized(contact_id)
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
    today_str = date.today().isoformat()

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

    overdue = []
    today_list = []
    upcoming = []

    for row in rows:
        nf = row["next_follow_up"]
        if not nf:
            continue
        if nf < today_str:
            overdue.append(row)
        elif nf == today_str:
            today_list.append(row)
        else:
            upcoming.append(row)

    return render_template(
        "followups.html",
        overdue=overdue,
        today_list=today_list,
        upcoming=upcoming,
        today=today_str,
        active_page="followups",
    )

@app.route("/interaction/<int:interaction_id>/complete", methods=["POST"])
@login_required
def complete_interaction(interaction_id):
    conn = get_db()
    cur = conn.cursor()

    # Get the contact_id so we know where to send you back
    cur.execute(
        "SELECT contact_id FROM interactions WHERE id = %s",
        (interaction_id,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return "Interaction not found", 404

    contact_id = row["contact_id"]

    # Mark as completed
    cur.execute(
        """
        UPDATE interactions
        SET is_completed = TRUE,
            completed_at = NOW()
        WHERE id = %s
        """,
        (interaction_id,),
    )

    conn.commit()
    conn.close()

    # Back to the edit page for that contact
    return redirect(url_for("edit_contact", contact_id=contact_id))

@app.route("/interaction/<int:interaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit_interaction(interaction_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM interactions WHERE id = %s", (interaction_id,))
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
            WHERE id = %s
            """,
            (happened_at, kind, notes, time_of_day, is_completed, interaction_id),
        )

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

    next_url = request.args.get("next") or url_for("edit_contact", contact_id=contact_id)

    cur.execute(
        "SELECT id FROM contacts WHERE id = %s AND user_id = %s",
        (contact_id, current_user.id),
    )
    if not cur.fetchone():
        conn.close()
        return "Contact not found", 404

    if request.method == "POST":
        status = (request.form.get("status") or "draft").strip()
        transaction_type = (request.form.get("transaction_type") or "unknown").strip().lower()

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
            "lead",  # safe default
            "none",  # safe default
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

        tx_id = row["id"]
        conn.commit()
        conn.close()

        return redirect(next_url)

    conn.close()
    return render_template(
        "transactions/transaction_form.html",
        mode="new",
        tx=None,
        transaction_statuses=TRANSACTION_STATUSES,
        next_url=next_url,
        deadlines=[],
    )


@app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id):
    conn = get_db()
    cur = conn.cursor()

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

    # Phase 3.1: Read-only deadlines for this transaction
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
    cur = conn.cursor()

    cur.execute("""
        SELECT id, address_line1, city, state, zip, start_datetime, end_datetime, public_token
        FROM open_houses
        ORDER BY start_datetime DESC
    """)
    rows = cur.fetchall()
    return render_template("openhouses/list.html", openhouses=rows)


@app.route("/openhouses/new", methods=["GET", "POST"])
@login_required
def openhouse_new():
    conn = get_db()
    cur = conn.cursor()

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
            return render_template("openhouses/new.html")

        token = generate_public_token()

        cur.execute("""
            INSERT INTO open_houses
              (created_by_user_id, address_line1, city, state, zip, start_datetime, end_datetime, public_token, house_photo_url, notes)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (1, address_line1, city, state, zip_code, start_dt, end_dt, token, house_photo_url, notes))

        open_house_id = cur.fetchone()["id"] if isinstance(cur.fetchone, object) else None

        # Safer: fetch id properly depending on cursor type
        conn.commit()

        # Re-fetch the inserted id the reliable way for RealDictCursor
        cur.execute("SELECT id FROM open_houses WHERE public_token = %s", (token,))
        open_house_id = cur.fetchone()["id"]

        flash("Open house created.", "success")
        return redirect(url_for("openhouse_detail", open_house_id=open_house_id))

    return render_template("openhouses/new.html")


@app.route("/openhouses/<int:open_house_id>")
@login_required
def openhouse_detail(open_house_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, address_line1, city, state, zip, start_datetime, end_datetime, public_token, house_photo_url, notes
        FROM open_houses
        WHERE id = %s
    """, (open_house_id,))
    oh = cur.fetchone()
    if not oh:
        abort(404)

    cur.execute("""
        SELECT id, first_name, last_name, email, phone, working_with_agent, agent_name, submitted_at
        FROM open_house_signins
        WHERE open_house_id = %s
        ORDER BY submitted_at DESC
    """, (open_house_id,))
    signins = cur.fetchall()

    return render_template("openhouses/detail.html", openhouse=oh, signins=signins)


@app.route("/openhouse/<token>", methods=["GET", "POST"])
def openhouse_public_signin(token):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, address_line1, city, state, zip, start_datetime, end_datetime, house_photo_url
        FROM open_houses
        WHERE public_token = %s
    """, (token,))
    oh = cur.fetchone()
    if not oh:
        abort(404)

    open_house_id = oh["id"] if isinstance(oh, dict) else oh[0]

    if request.method == "POST":
        first_name = (request.form.get("first_name") or "").strip()
        last_name = (request.form.get("last_name") or "").strip()
        email = normalize_email(request.form.get("email"))
        phone = normalize_phone(request.form.get("phone"))

        working_with_agent = request.form.get("working_with_agent")
        if working_with_agent == "yes":
            working_with_agent_bool = True
        elif working_with_agent == "no":
            working_with_agent_bool = False
        else:
            working_with_agent_bool = None

        agent_name = (request.form.get("agent_name") or "").strip() or None
        agent_phone = (request.form.get("agent_phone") or "").strip() or None
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
        # Match or create contact (email first, then phone)
        contact_id = None

        if email:
            cur.execute("SELECT id FROM contacts WHERE LOWER(email) = %s LIMIT 1", (email,))
            r = cur.fetchone()
            if r:
                contact_id = r["id"] if isinstance(r, dict) else r[0]

        if not contact_id and phone:
            cur.execute("SELECT id FROM contacts WHERE phone = %s LIMIT 1", (phone,))
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
                WHERE id = %s
            """, (working_with_agent_bool, agent_name, agent_phone, agent_brokerage, open_house_id, contact_id))
        else:
            full_name = f"{first_name} {last_name}".strip()
            cur.execute("""
                INSERT INTO contacts
                  (name, first_name, last_name, email, phone, working_with_agent, agent_name, agent_phone, agent_brokerage, lead_source, last_open_house_id)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (full_name, first_name, last_name, email, phone, working_with_agent_bool, agent_name, agent_phone, agent_brokerage, "Open House", open_house_id))
            r = cur.fetchone()
            contact_id = r["id"] if isinstance(r, dict) else r[0]

        cur.execute("""
            INSERT INTO open_house_signins
              (open_house_id, contact_id, first_name, last_name, email, phone,
               working_with_agent, agent_name, agent_phone, agent_brokerage,
               looking_to_buy, looking_to_sell, timeline, notes, consent_to_contact)
            VALUES
              (%s, %s, %s, %s, %s, %s,
               %s, %s, %s, %s,
               %s, %s, %s, %s, %s)
        """, (open_house_id, contact_id, first_name, last_name, email, phone,
              working_with_agent_bool, agent_name, agent_phone, agent_brokerage,
              looking_to_buy, looking_to_sell, timeline, notes, consent_to_contact))

        conn.commit()
        flash("Thanks. You are signed in.", "success")
        return redirect(url_for("openhouse_public_signin", token=token))

    conn.close()
    return render_template(
        "public/openhouse_signin.html", 
        openhouse=oh, 
        hide_nav=True)

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
    cur = conn.cursor()

    cur.execute("SELECT id FROM open_houses WHERE id = %s", (open_house_id,))
    if not cur.fetchone():
        abort(404)

    cur.execute("""
        SELECT
          submitted_at,
          first_name, last_name, email, phone,
          working_with_agent, agent_name, agent_phone, agent_brokerage,
          looking_to_buy, looking_to_sell, timeline, notes, consent_to_contact
        FROM open_house_signins
        WHERE open_house_id = %s
        ORDER BY submitted_at ASC
    """, (open_house_id,))

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
        if isinstance(r, dict):
            writer.writerow([
                r["submitted_at"],
                r["first_name"], r["last_name"], r["email"], r["phone"],
                r["working_with_agent"], r["agent_name"], r["agent_phone"], r["agent_brokerage"],
                r["looking_to_buy"], r["looking_to_sell"], r["timeline"], r["notes"], r["consent_to_contact"]
            ])
        else:
            writer.writerow(list(r))

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=open_house_{open_house_id}_signins.csv"}
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
        JOIN contacts c ON i.contact_id = c.id
        WHERE i.due_at IS NOT NULL
          AND i.due_at <= NOW()
          AND i.due_at >= NOW() - INTERVAL '10 minutes'
          AND i.is_completed = FALSE
          AND (i.notified IS FALSE OR i.notified IS NULL)
        """
    )
    rows = cur.fetchall()

    # rows is a list of dicts, so use keys not indexes
    interaction_ids = [row["id"] for row in rows]
    if interaction_ids:
        cur.execute(
            "UPDATE interactions SET notified = TRUE WHERE id = ANY(%s)",
            (interaction_ids,),
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


@app.route("/delete/<int:contact_id>")
@login_required
def delete_contact(contact_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM contacts WHERE id = %s", (contact_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("contacts"))


def normalize_phone_digits(phone: str) -> str:
    """
    Strip non-digits from a phone string.
    """
    if not phone:
        return ""
    return re.sub(r"\\D+", "", phone)

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

    contact_row = None

    try:
        if contact_id:
            cur.execute("SELECT id FROM contacts WHERE id = %s", (contact_id,))
            contact_row = cur.fetchone()
        if not contact_row and email:
            cur.execute(
                "SELECT id FROM contacts WHERE lower(email) = %s LIMIT 1",
                (email,),
            )
            contact_row = cur.fetchone()
        if not contact_row and phone_digits:
            cur.execute(
                """
                SELECT id
                FROM contacts
                WHERE regexp_replace(coalesce(phone, ''), '\\D', '', 'g') = %s
                LIMIT 1
                """,
                (phone_digits,),
            )
            contact_row = cur.fetchone()
    except Exception as e:
        conn.close()
        return jsonify({"error": f"Database error: {e}"}), 500

    if not contact_row:
        conn.close()
        return jsonify({"error": "Contact not found"}), 404

    cid = contact_row["id"]

    happened_at = data.get("happened_at")
    if not happened_at:
        happened_at = date.today().isoformat()

    time_of_day = (data.get("time_of_day") or "").strip() or None
    notes = (data.get("notes") or "").strip()

    try:
        cur.execute(
            """
            INSERT INTO interactions (contact_id, kind, happened_at, time_of_day, notes)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (cid, kind, happened_at, time_of_day, notes),
        )
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"error": f"Insert failed: {e}"}), 500

    conn.close()
    return jsonify({"status": "ok", "contact_id": cid})


try:
    init_db()
except Exception as e:
    print("init_db() on import failed:", e)


import os  # near the top with other imports


if __name__ == "__main__":
    init_db()
    app.run(debug=False)
