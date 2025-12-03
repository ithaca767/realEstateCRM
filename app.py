import os
from datetime import date

from flask import Flask, render_template_string, request, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# PostgreSQL connection string from environment (Render)
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Ensure base table exists
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

    # Schema upgrades (safe to re-run)
    schema_updates = [
        "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS first_name TEXT",
        "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS last_name TEXT",
        "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS current_address TEXT",
        "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS subject_address TEXT",
    ]

    for stmt in schema_updates:
        try:
            cur.execute(stmt)
            conn.commit()
        except Exception as e:
            print("Schema update skipped:", e)

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
    </style>
</head>
<body>
<div class="container py-4">
<div class="d-flex align-items-center mb-3">
    <img
        src="{{ url_for('static', filename='ulysses-logo.svg') }}"
        alt="Ulysses CRM"
        style="height: 72px;"
    >
</div>
    <!-- Add contact form -->
    <div class="card mb-4">
        <div class="card-header">
            Add new contact
        </div>
        <div class="card-body">
            <form method="post" action="{{ url_for('add_contact') }}">
                <div class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label">Name *</label>
                        <input name="name" class="form-control" required>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Email</label>
                        <input name="email" type="email" class="form-control">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Phone</label>
                        <input name="phone" class="form-control">
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Lead type</label>
                        <select name="lead_type" class="form-select">
                            <option value="">Select...</option>
                            {% for t in lead_types %}
                                <option value="{{ t }}">{{ t }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Pipeline stage</label>
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
                        <label class="form-label">Price min</label>
                        <input name="price_min" type="number" class="form-control" placeholder="300000">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Price max</label>
                        <input name="price_max" type="number" class="form-control" placeholder="600000">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Target area</label>
                        <input name="target_area" class="form-control" placeholder="Keyport, Hazlet, Netflix zone">
                    </div>

                    <div class="col-md-3">
                        <label class="form-label">Last contacted</label>
                        <input name="last_contacted" type="date" class="form-control" value="{{ today }}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Next follow up</label>
                        <input name="next_follow_up" type="date" class="form-control">
                    </div>

                    <div class="col-12">
                        <label class="form-label">Notes</label>
                        <textarea name="notes" class="form-control" rows="2"
                         placeholder="Motivation, timing, specific needs..."></textarea>
                    </div>
                </div>
                <button class="btn btn-primary mt-3" type="submit">Add contact</button>
            </form>
        </div>
    </div>

    <!-- Filters -->
    <form class="row g-3 mb-3" method="get" action="{{ url_for('index') }}">
        <div class="col-md-3">
            <input type="text" name="q" value="{{ request.args.get('q','') }}" class="form-control"
                   placeholder="Search name, email, phone">
        </div>
        <div class="col-md-2">
            <select name="lead_type" class="form-select">
                <option value="">Lead type</option>
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
            <button class="btn btn-outline-secondary" type="submit">Apply filters</button>
            <a href="{{ url_for('index') }}" class="btn btn-link">Clear</a>
        </div>
    </form>

    <!-- Contacts table -->
    <div class="card">
        <div class="card-header">
            Contacts ({{ contacts|length }})
        </div>
        <div class="table-responsive">
            <table class="table table-sm table-striped mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Name</th>
                        <th>Lead type</th>
                        <th>Stage</th>
                        <th>Priority</th>
                        <th>Price range</th>
                        <th>Area</th>
                        <th>Source</th>
                        <th>Last contacted</th>
                        <th>Next follow up</th>
                        <th style="width: 220px;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                {% for c in contacts %}
                    <tr>
                        <td>{{ c["name"] }}</td>
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
                        <td>{{ c["source"] or "" }}</td>
                        <td>{{ c["last_contacted"] or "" }}</td>
                        <td>{{ c["next_follow_up"] or "" }}</td>
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
                        <td colspan="10"><strong>Notes:</strong> {{ c["notes"] }}</td>
                    </tr>
                    {% endif %}
                {% endfor %}
                {% if contacts|length == 0 %}
                    <tr><td colspan="10" class="text-center py-3">No contacts yet.</td></tr>
                {% endif %}
                </tbody>
            </table>
        </div>
    </div>
</div>
</body>
</html>
"""


EDIT_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Ulysses CRM - Edit contact</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet"
    >
    <style>
      body {
        background-color: #6eb8f9;
      }
    </style>
</head>
<body>
<div class="container py-4">
    <h1 class="mb-4">Edit contact</h1>
    <form method="post">
        <div class="row g-3">
            <div class="col-md-4">
                <label class="form-label">Name *</label>
                <input name="name" class="form-control" required value="{{ c['name'] }}">
            </div>
            <div class="col-md-4">
                <label class="form-label">Email</label>
                <input name="email" type="email" class="form-control" value="{{ c['email'] }}">
            </div>
            <div class="col-md-4">
                <label class="form-label">Phone</label>
                <input name="phone" class="form-control" value="{{ c['phone'] }}">
            </div>

            <div class="col-md-3">
                <label class="form-label">Lead type</label>
                <select name="lead_type" class="form-select">
                    <option value="">Select...</option>
                    {% for t in lead_types %}
                        <option value="{{ t }}" {% if c['lead_type'] == t %}selected{% endif %}>{{ t }}</option>
                    {% endfor %}
                </select>
            </div>

            <div class="col-md-3">
                <label class="form-label">Pipeline stage</label>
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
                <label class="form-label">Price min</label>
                <input name="price_min" type="number" class="form-control"
                       value="{{ c['price_min'] if c['price_min'] is not none else '' }}">
            </div>
            <div class="col-md-3">
                <label class="form-label">Price max</label>
                <input name="price_max" type="number" class="form-control"
                       value="{{ c['price_max'] if c['price_max'] is not none else '' }}">
            </div>
            <div class="col-md-3">
                <label class="form-label">Target area</label>
                <input name="target_area" class="form-control" value="{{ c['target_area'] or '' }}">
            </div>

            <div class="col-md-3">
                <label class="form-label">Last contacted</label>
                <input name="last_contacted" type="date" class="form-control"
                       value="{{ c['last_contacted'] or '' }}">
            </div>
            <div class="col-md-3">
                <label class="form-label">Next follow up</label>
                <input name="next_follow_up" type="date" class="form-control"
                       value="{{ c['next_follow_up'] or '' }}">
            </div>

            <div class="col-12">
                <label class="form-label">Notes</label>
                <textarea name="notes" class="form-control" rows="3">{{ c['notes'] or '' }}</textarea>
            </div>
        </div>
        <button class="btn btn-primary mt-3" type="submit">Save changes</button>
        <a href="{{ url_for('index') }}" class="btn btn-secondary mt-3">Cancel</a>
    </form>
</div>
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


@app.route("/add", methods=["POST"])
def add_contact():
    data = {
        "name": request.form.get("name", "").strip(),
        "email": request.form.get("email", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "lead_type": request.form.get("lead_type", "").strip(),
        "pipeline_stage": request.form.get("pipeline_stage", "").strip(),
        "priority": request.form.get("priority", "").strip(),
        "source": request.form.get("source", "").strip(),
        "price_min": parse_int_or_none(request.form.get("price_min")),
        "price_max": parse_int_or_none(request.form.get("price_max")),
        "target_area": request.form.get("target_area", "").strip(),
        "last_contacted": request.form.get("last_contacted") or None,
        "next_follow_up": request.form.get("next_follow_up") or None,
        "notes": request.form.get("notes", "").strip(),
    }

    if not data["name"]:
        return redirect(url_for("index"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO contacts (
            name, email, phone, lead_type, pipeline_stage, price_min, price_max,
            target_area, source, priority, last_contacted, next_follow_up, notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            data["notes"],
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
        data = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "lead_type": request.form.get("lead_type", "").strip(),
            "pipeline_stage": request.form.get("pipeline_stage", "").strip(),
            "priority": request.form.get("priority", "").strip(),
            "source": request.form.get("source", "").strip(),
            "price_min": parse_int_or_none(request.form.get("price_min")),
            "price_max": parse_int_or_none(request.form.get("price_max")),
            "target_area": request.form.get("target_area", "").strip(),
            "last_contacted": request.form.get("last_contacted") or None,
            "next_follow_up": request.form.get("next_follow_up") or None,
            "notes": request.form.get("notes", "").strip(),
        }

        cur.execute(
            """
            UPDATE contacts
            SET name = %s, email = %s, phone = %s, lead_type = %s, pipeline_stage = %s,
                price_min = %s, price_max = %s, target_area = %s, source = %s, priority = %s,
                last_contacted = %s, next_follow_up = %s, notes = %s
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
                data["notes"],
                contact_id,
            ),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
    contact = cur.fetchone()
    conn.close()
    if not contact:
        return "Contact not found", 404
    return render_template_string(
        EDIT_TEMPLATE,
        c=contact,
        lead_types=LEAD_TYPES,
        pipeline_stages=PIPELINE_STAGES,
        priorities=PRIORITIES,
        sources=SOURCES,
    )


@app.route("/delete/<int:contact_id>")
def delete_contact(contact_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM contacts WHERE id = %s", (contact_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# Ensure tables exist when the app module is imported (Render / gunicorn)
try:
    init_db()
except Exception as e:
    print("init_db() on import failed:", e)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
