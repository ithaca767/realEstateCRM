import os
import re
from datetime import date, datetime, timedelta

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template,
    render_template_string,
    jsonify,
)

import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
SHORTCUT_API_KEY = os.environ.get("SHORTCUT_API_KEY")  # optional shared secret


def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


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

    # Related contacts table (associated contacts)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS related_contacts (
            id SERIAL PRIMARY KEY,
            contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
            related_name TEXT NOT NULL,
            relationship TEXT,
            email TEXT,
            phone TEXT,
            notes TEXT
        )
        """
    )
    conn.commit()

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

    conn.close()

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


@app.route("/")
def dashboard():
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

    # Total contacts count
    cur.execute("SELECT COUNT(*) AS cnt FROM contacts")
    total_contacts = cur.fetchone()["cnt"]

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
        "dashboard.html",
        overdue=overdue,
        today_list=today_list,
        upcoming=upcoming,
        today=today_str,
        total_contacts=total_contacts,
        active_page="dashboard",
    )

@app.route("/contacts")
def contacts():
    q = request.args.get("q", "").strip()
    lead_type = request.args.get("lead_type", "").strip()
    pipeline_stage = request.args.get("pipeline_stage", "").strip()
    priority = request.args.get("priority", "").strip()
    target_area = request.args.get("target_area", "").strip()

    conn = get_db()
    cur = conn.cursor()

    sql = """
        SELECT
            c.*,
            (bp.id IS NOT NULL) AS has_buyer_profile,
            (sp.id IS NOT NULL) AS has_seller_profile
        FROM contacts c
        LEFT JOIN buyer_profiles bp ON bp.contact_id = c.id
        LEFT JOIN seller_profiles sp ON sp.contact_id = c.id
        WHERE 1=1
    """
    params = []

    if q:
        sql += " AND (c.name ILIKE %s OR c.email ILIKE %s OR c.phone ILIKE %s)"
        like = f"%{q}%"
        params.extend([like, like, like])

    if lead_type:
        sql += " AND c.lead_type = %s"
        params.append(lead_type)

    if pipeline_stage:
        sql += " AND c.pipeline_stage = %s"
        params.append(pipeline_stage)

    if priority:
        sql += " AND c.priority = %s"
        params.append(priority)

    if target_area:
        sql += " AND c.target_area ILIKE %s"
        params.append(f"%{target_area}%")

    sql += " ORDER BY c.next_follow_up IS NULL, c.next_follow_up, c.name"

    cur.execute(sql, params)
    contacts = cur.fetchall()
    conn.close()

    return render_template(
        "contacts.html",
        contacts=contacts,
        request=request,
        today=date.today().isoformat(),
        lead_types=LEAD_TYPES,
        pipeline_stages=PIPELINE_STAGES,
        priorities=PRIORITIES,
        sources=SOURCES,
        active_page="contacts",
    )

def parse_int_or_none(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_follow_up_time_from_form(prefix: str = "next_follow_up_"):
    """
    Reads hour/minute/ampm from the form and returns a 24-hour "HH:MM" string or None.
    Prefix is for field names like next_follow_up_hour, next_follow_up_minute, next_follow_up_ampm.
    """
    hour_raw = (request.form.get(prefix + "hour") or "").strip()
    minute = (request.form.get(prefix + "minute") or "").strip()
    ampm = (request.form.get(prefix + "ampm") or "").strip().upper()

    if not hour_raw or not minute or ampm not in ("AM", "PM"):
        return None

    try:
        hour_12 = int(hour_raw)
        if hour_12 < 1 or hour_12 > 12:
            return None
    except ValueError:
        return None

    if ampm == "AM":
        hour_24 = 0 if hour_12 == 12 else hour_12
    else:
        hour_24 = 12 if hour_12 == 12 else hour_12 + 12

    return f"{hour_24:02d}:{minute}"


@app.route("/add", methods=["POST"])
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
        return redirect(url_for("contacts"))

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

    # Pre-fill follow-up time selects if we have a stored time
    next_time_hour = None
    next_time_minute = None
    next_time_ampm = None
    t_str = contact.get("next_follow_up_time")
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
        SELECT * FROM interactions
        WHERE contact_id = %s
        ORDER BY happened_at DESC NULLS LAST, id DESC
        """,
        (contact_id,),
    )
    interactions = cur.fetchall()

    # Associated contacts for this contact
    cur.execute(
        """
        SELECT * FROM related_contacts
        WHERE contact_id = %s
        ORDER BY id
        """,
        (contact_id,),
    )
    related_contacts = cur.fetchall()

    conn.close()

    return render_template(
        "edit_contact.html",
        c=contact,
        interactions=interactions,
        related_contacts=related_contacts,
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
    )

@app.route("/add_interaction/<int:contact_id>", methods=["POST"])
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
def buyer_profile(contact_id):
    conn = get_db()
    cur = conn.cursor()

    # Load contact
    cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
    contact = cur.fetchone()
    if not contact:
        conn.close()
        return "Contact not found", 404

    if request.method == "POST":
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

        # Buyer documents checklist fields
        cis_signed = bool(request.form.get("cis_signed"))
        buyer_agreement_signed = bool(request.form.get("buyer_agreement_signed"))
        wire_fraud_notice_signed = bool(request.form.get("wire_fraud_notice_signed"))
        dual_agency_consent_signed = bool(request.form.get("dual_agency_consent_signed"))

        # Professionals - Attorney
        buyer_attorney_name = (request.form.get("buyer_attorney_name") or "").strip()
        buyer_attorney_email = (request.form.get("buyer_attorney_email") or "").strip()
        buyer_attorney_phone = (request.form.get("buyer_attorney_phone") or "").strip()
        buyer_attorney_referred = bool(request.form.get("buyer_attorney_referred"))

        # Professionals - Lender (extend existing lender_name)
        buyer_lender_email = (request.form.get("buyer_lender_email") or "").strip()
        buyer_lender_phone = (request.form.get("buyer_lender_phone") or "").strip()
        buyer_lender_referred = bool(request.form.get("buyer_lender_referred"))

        # Professionals - Home Inspector
        buyer_inspector_name = (request.form.get("buyer_inspector_name") or "").strip()
        buyer_inspector_email = (request.form.get("buyer_inspector_email") or "").strip()
        buyer_inspector_phone = (request.form.get("buyer_inspector_phone") or "").strip()
        buyer_inspector_referred = bool(request.form.get("buyer_inspector_referred"))

        # Any other professionals
        other_professionals = (request.form.get("other_professionals") or "").strip()

        # Check for existing profile
        cur.execute(
            "SELECT id FROM buyer_profiles WHERE contact_id = %s",
            (contact_id,),
        )
        existing = cur.fetchone()

        if existing:
            cur.execute(
                """
                UPDATE buyer_profiles
                SET property_type = %s,
                    timeframe = %s,
                    min_price = %s,
                    max_price = %s,
                    areas = %s,
                    property_types = %s,
                    preapproval_status = %s,
                    lender_name = %s,
                    referral_source = %s,
                    notes = %s,
                    cis_signed = %s,
                    buyer_agreement_signed = %s,
                    wire_fraud_notice_signed = %s,
                    dual_agency_consent_signed = %s,
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
                WHERE contact_id = %s
                """,
                (
                    property_type,
                    timeframe,
                    min_price,
                    max_price,
                    areas,
                    property_types,
                    preapproval_status,
                    lender_name,
                    referral_source,
                    notes,
                    cis_signed,
                    buyer_agreement_signed,
                    wire_fraud_notice_signed,
                    dual_agency_consent_signed,
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
                    contact_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO buyer_profiles (
                    contact_id,
                    property_type,
                    timeframe,
                    min_price,
                    max_price,
                    areas,
                    property_types,
                    preapproval_status,
                    lender_name,
                    referral_source,
                    notes,
                    cis_signed,
                    buyer_agreement_signed,
                    wire_fraud_notice_signed,
                    dual_agency_consent_signed,
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    contact_id,
                    property_type,
                    timeframe,
                    min_price,
                    max_price,
                    areas,
                    property_types,
                    preapproval_status,
                    lender_name,
                    referral_source,
                    notes,
                    cis_signed,
                    buyer_agreement_signed,
                    wire_fraud_notice_signed,
                    dual_agency_consent_signed,
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

        conn.commit()
        conn.close()
        return redirect(url_for("edit_contact", contact_id=contact_id))

    # GET: load profile
    cur.execute(
        "SELECT * FROM buyer_profiles WHERE contact_id = %s",
        (contact_id,),
    )
    bp = cur.fetchone()
    conn.close()

    contact_name = (contact.get("first_name") or "") + (
        " " if contact.get("first_name") and contact.get("last_name") else ""
    ) + (contact.get("last_name") or "")
    contact_name = contact_name.strip() or contact["name"]

    return render_template_string(
        BUYER_TEMPLATE,
        contact_id=contact_id,
        contact_name=contact_name,
        contact_email=contact.get("email"),
        contact_phone=contact.get("phone"),
        bp=bp,
        active_page="contacts",
    )

@app.route("/seller/<int:contact_id>", methods=["GET", "POST"])
def seller_profile(contact_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
    contact = cur.fetchone()
    if not contact:
        conn.close()
        return "Contact not found", 404

    if request.method == "POST":
        property_type = (request.form.get("property_type") or "").strip()
        timeframe = (request.form.get("timeframe") or "").strip()
        motivation = (request.form.get("motivation") or "").strip()
        condition_notes = (request.form.get("condition_notes") or "").strip()
        property_address = (request.form.get("property_address") or "").strip()
        referral_source = (request.form.get("referral_source") or "").strip()
        notes = (request.form.get("notes") or "").strip()

        estimated_price = parse_int_or_none(request.form.get("estimated_price"))

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

        cur.execute(
            "SELECT id FROM seller_profiles WHERE contact_id = %s",
            (contact_id,),
        )
        existing = cur.fetchone()

        if existing:
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        return redirect(url_for("edit_contact", contact_id=contact_id))

    # GET
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

    return render_template_string(
        SELLER_TEMPLATE,
        contact_id=contact_id,
        contact_name=contact_name,
        contact_email=contact.get("email"),
        contact_phone=contact.get("phone"),
        sp=sp,
        active_page="contacts",
    )

@app.route("/followups")
def followups():
    """
    Dashboard view of overdue, today's, and upcoming follow-ups.
    """
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

@app.route("/followups.ics")
def followups_ics():
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


@app.route("/api/add_interaction", methods=["POST"])
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

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
