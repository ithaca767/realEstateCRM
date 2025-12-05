import os
from datetime import date, datetime, timedelta

from flask import Flask, render_template_string, request, redirect, url_for, Response
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")


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
    </style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm">
  <div class="container-fluid">
    <a class="navbar-brand d-flex align-items-center" href="{{ url_for('index') }}">
      <img
        src="{{ url_for('static', filename='ulysses-logo.svg') }}"
        alt="Ulysses CRM"
        style="height: 40px;"
        class="me-2"
      >
      <span class="fw-semibold">Ulysses CRM</span>
    </a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse"
            data-bs-target="#mainNav" aria-controls="mainNav" aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-auto mb-2 mb-lg-0">
        <li class="nav-item">
          <a class="nav-link{% if request.endpoint == 'index' %} active{% endif %}"
             href="{{ url_for('index') }}">
            Contacts
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#add-contact">Add Contact</a>
        </li>
        <li class="nav-item">
          <a class="nav-link{% if request.endpoint == 'followups' %} active{% endif %}"
             href="{{ url_for('followups') }}">
            Follow Up Dashboard
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link"
             href="{{ url_for('followups_ics') if 'followups_ics' in globals() else '/followups.ics' }}"
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

                    <div class="col-md-3">
                        <label class="form-label">Price Min</label>
                        <input name="price_min" type="number" class="form-control" placeholder="300000">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Price Max</label>
                        <input name="price_max" type="number" class="form-control" placeholder="600000">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Target Area</label>
                        <input name="target_area" class="form-control" placeholder="Keyport, Hazlet, Netflix zone">
                    </div>

                    <!-- Subject and Current addresses, grouped -->
                    <div class="col-12 mt-3">
                        <h6 class="fw-bold mb-2">Subject Property</h6>
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Street Address</label>
                        <input name="subject_address" class="form-control" placeholder="Property of interest">
                    </div>

                    <div class="col-md-2 col-6">
                        <label class="form-label">City</label>
                        <input name="subject_city" class="form-control" placeholder="Hazlet">
                    </div>
                    <div class="col-md-2 col-3">
                        <label class="form-label">State</label>
                        <input name="subject_state" class="form-control" placeholder="NJ">
                    </div>
                    <div class="col-md-2 col-3">
                        <label class="form-label">ZIP</label>
                        <input name="subject_zip" class="form-control" placeholder="07730">
                    </div>

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
            <form class="row g-3 mb-0" method="get" action="{{ url_for('index') }}">
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
                    <a href="{{ url_for('index') }}" class="btn btn-link">Clear</a>
                </div>
            </form>
        </div>
    </div>

    <!-- Contacts table -->
    <div class="card">
        <div class="card-header fw-bold">
            Contacts ({{ contacts|length }})
        </div>
        <div class="table-responsive bg-white">
            <table class="table table-sm table-striped mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Name</th>
                        <th>Lead Type</th>
                        <th>Stage</th>
                        <th>Priority</th>
                        <th>Price Range</th>
                        <th>Area</th>
                        <th>Current Address</th>
                        <th>Subject Property</th>
                        <th>Source</th>
                        <th>Last Contacted</th>
                        <th>Next Follow Up</th>
                        <th style="width: 220px;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                {% for c in contacts %}
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
                        <td>{{ c["lead_type"] or "" }}</td>
                        <td>{{ c["pipeline_stage"] or "" }}</td>
                        <td>{{ c["priority"] or "" }}</td>
                        <td>
                            {% if c["price_min"] or c["price_max"] %}
                                {% if c["price_min"] %}${{ "{:,}".format(c["price_min"]) }}{% endif %}
                                {% if c["price_min"] and c["price_max"] %} - {% endif %}
                                {% if c["price_max"] %}${{ "{:,}".format(c["price_max"]) }}{% endif %}
                            {% endif %}
                        </td>
                        <td>{{ c["target_area"] or "" }}</td>
                        <td>
                            {% if c["current_address"] or c["current_city"] or c["current_state"] or c["current_zip"] %}
                                {{ c["current_address"] or "" }}
                                {% if c["current_city"] %}, {{ c["current_city"] }}{% endif %}
                                {% if c["current_state"] %}, {{ c["current_state"] }}{% endif %}
                                {% if c["current_zip"] %} {{ c["current_zip"] }}{% endif %}
                            {% endif %}
                        </td>
                        <td>
                            {% if c["subject_address"] or c["subject_city"] or c["subject_state"] or c["subject_zip"] %}
                                {{ c["subject_address"] or "" }}
                                {% if c["subject_city"] %}, {{ c["subject_city"] }}{% endif %}
                                {% if c["subject_state"] %}, {{ c["subject_state"] }}{% endif %}
                                {% if c["subject_zip"] %} {{ c["subject_zip"] }}{% endif %}
                            {% endif %}
                        </td>
                        <td>{{ c["source"] or "" }}</td>
                        <td>{{ c["last_contacted"] or "" }}</td>
                        <td>
                            {{ c["next_follow_up"] or "" }}
                            {% if c["next_follow_up_time"] %}
                                {{ " " }}{{ c["next_follow_up_time"] }}
                            {% endif %}
                        </td>
                        <td>
                            <a href="{{ url_for('edit_contact', contact_id=c['id']) }}" class="btn btn-sm btn-outline-primary">Edit</a>
                            <a href="{{ url_for('delete_contact', contact_id=c['id']) }}"
                               class="btn btn-sm btn-outline-danger"
                               onclick="return confirm('Delete this contact?');">
                               Delete
                            </a>
                        </td>
                    </tr>
                    {% if c["notes"] %}
                    <tr class="table-secondary">
                        <td colspan="12"><strong>Notes:</strong> {{ c["notes"] }}</td>
                    </tr>
                    {% endif %}
                {% endfor %}
                {% if contacts|length == 0 %}
                    <tr><td colspan="12" class="text-center py-3">No contacts yet.</td></tr>
                {% endif %}
                </tbody>
            </table>
        </div>
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
    </style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm">
  <div class="container-fluid">
    <a class="navbar-brand d-flex align-items-center" href="{{ url_for('index') }}">
      <img
        src="{{ url_for('static', filename='ulysses-logo.svg') }}"
        alt="Ulysses CRM"
        style="height: 40px;"
        class="me-2"
      >
      <span class="fw-semibold">Ulysses CRM</span>
    </a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse"
            data-bs-target="#mainNav" aria-controls="mainNav" aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-auto mb-2 mb-lg-0">
        <li class="nav-item">
          <a class="nav-link" href="{{ url_for('index') }}">
            Contacts
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="{{ url_for('followups') }}">
            Follow Up Dashboard
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link"
             href="{{ url_for('followups_ics') if 'followups_ics' in globals() else '/followups.ics' }}"
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

                    <div class="col-md-3">
                        <label class="form-label">Price Min</label>
                        <input name="price_min" type="number" class="form-control"
                               value="{{ c['price_min'] if c['price_min'] is not none else '' }}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Price Max</label>
                        <input name="price_max" type="number" class="form-control"
                               value="{{ c['price_max'] if c['price_max'] is not none else '' }}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Target Area</label>
                        <input name="target_area" class="form-control" value="{{ c['target_area'] or '' }}">
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
                <a href="{{ url_for('index') }}" class="btn btn-secondary mt-3">Cancel</a>
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
    </style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm">
  <div class="container-fluid">
    <a class="navbar-brand d-flex align-items-center" href="{{ url_for('index') }}">
      <img
        src="{{ url_for('static', filename='ulysses-logo.svg') }}"
        alt="Ulysses CRM"
        style="height: 40px;"
        class="me-2"
      >
      <span class="fw-semibold">Ulysses CRM</span>
    </a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse"
            data-bs-target="#mainNav" aria-controls="mainNav" aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-auto mb-2 mb-lg-0">
        <li class="nav-item">
          <a class="nav-link" href="{{ url_for('index') }}">
            Contacts
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link active" href="{{ url_for('followups') }}">
            Follow Up Dashboard
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link"
             href="{{ url_for('followups_ics') if 'followups_ics' in globals() else '/followups.ics' }}"
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

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    lead_type = request.args.get("lead_type", "").strip()
    pipeline_stage = request.args.get("pipeline_stage", "").strip()
    priority = request.args.get("priority", "").strip()
    target_area = request.args.get("target_area", "").strip()

    conn = get_db()
    cur = conn.cursor()

    sql = "SELECT * FROM contacts WHERE 1=1"
    params = []

    if q:
        sql += " AND (name ILIKE %s OR email ILIKE %s OR phone ILIKE %s)"
        like = f"%{q}%"
        params.extend([like, like, like])

    if lead_type:
        sql += " AND lead_type = %s"
        params.append(lead_type)

    if pipeline_stage:
        sql += " AND pipeline_stage = %s"
        params.append(pipeline_stage)

    if priority:
        sql += " AND priority = %s"
        params.append(priority)

    if target_area:
        sql += " AND target_area ILIKE %s"
        params.append(f"%{target_area}%")

    sql += " ORDER BY next_follow_up IS NULL, next_follow_up, name"

    cur.execute(sql, params)
    contacts = cur.fetchall()
    conn.close()

    return render_template_string(
        BASE_TEMPLATE,
        contacts=contacts,
        request=request,
        today=date.today().isoformat(),
        lead_types=LEAD_TYPES,
        pipeline_stages=PIPELINE_STAGES,
        priorities=PRIORITIES,
        sources=SOURCES,
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

    # Convert 12-hour to 24-hour
    if ampm == "AM":
        hour_24 = 0 if hour_12 == 12 else hour_12
    else:  # PM
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
        return redirect(url_for("index"))

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
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


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
            return redirect(url_for("index"))

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
        return redirect(url_for("index"))

    # GET: load contact and its interactions
    cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
    contact = cur.fetchone()

    if not contact:
        conn.close()
        return "Contact not found", 404

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
    conn.close()

    return render_template_string(
        EDIT_TEMPLATE,
        c=contact,
        interactions=interactions,
        lead_types=LEAD_TYPES,
        pipeline_stages=PIPELINE_STAGES,
        priorities=PRIORITIES,
        sources=SOURCES,
        today=date.today().isoformat(),
        next_time_hour=next_time_hour,
        next_time_minute=next_time_minute,
        next_time_ampm=next_time_ampm,
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
        return redirect(url_for("index"))

    contact_id = row["contact_id"]

    # Delete the interaction
    cur.execute("DELETE FROM interactions WHERE id = %s", (interaction_id,))
    conn.commit()
    conn.close()

    # Go back to that contact's edit page
    return redirect(url_for("edit_contact", contact_id=contact_id))

@app.route("/followups")
def followups():
    """
    Simple dashboard view of overdue, today's, and upcoming follow-ups.
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

    return render_template_string(
        FOLLOWUPS_TEMPLATE,
        overdue=overdue,
        today_list=today_list,
        upcoming=upcoming,
        today=today_str,
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

        # Use first/last name if available
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
            # Timed event with 30-minute duration
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
                # Fallback to all-day if something goes wrong
                dtstart = date_str.replace("-", "")
                lines.append(f"DTSTART;VALUE=DATE:{dtstart}")
                lines.append(f"DTEND;VALUE=DATE:{dtstart}")
        else:
            # All-day event
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
    return redirect(url_for("index"))


try:
    init_db()
except Exception as e:
    print("init_db() on import failed:", e)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
