# Ulysses CRM – Phase 8B + Phase 8C
Post-Phase 8A | ActivePipe Bridge (CSV Compatibility Layer)
Version: 1.1.1 (start) → 1.1.x (as released)
Branch: main
Status: Planned (begin implementation after this doc)

## Purpose

Establish a Canon-aligned, non-API “bridge” between Ulysses CRM and ActivePipe using deterministic CSV import and export.

This bridge must:
- Preserve Ulysses as the system of record
- Respect vendor constraints (no API, no scraping, no fragile hacks)
- Provide high-value bulk workflows (export and import)
- Remain multi-tenant safe (user_id scoped, no cross-tenant leakage)
- Keep core Contact model lean (no schema sprawl for vendor-specific fields)

## Canon Governance

All work must conform to:
- docs/ULYSSES_CRM_CANON.md (authoritative)
- Existing phase documentation in docs/phases/
- Release discipline (version bump + release manifest on production commits)
- Local-first workflow
- No destructive schema changes without migrations and documentation

Standing safety rules:
- Never echo full DATABASE_URL in terminal or chat
- Warn if any command could expose credentials
- Rotate credentials after production debugging
- No casual schema changes on main

## Key Concept

ActivePipe is treated as a marketing distribution layer.
Ulysses is treated as the CRM brain.

Integration is implemented as:
- User-initiated CSV export from Ulysses to ActivePipe
- User-initiated CSV import from ActivePipe back into Ulysses
- Integration-specific fields stored outside core contacts in a controlled integration profile

## ActivePipe CSV Contract

ActivePipe headers (as provided):
- firstname, lastname, email, phone, mobile
- streetaddress, city, state, postcode, country
- status, sms_status, subscribed_at, unsubscribed_at, unsubscribed_reason
- source, modified_at, latest_interaction
- buyertype, locations, propertytype, category
- minbeds, maxbeds, minbaths, maxbaths
- minprice, maxprice
- minparking, maxparking
- minlandsize, maxlandsize
- minbuildingsize, maxbuildingsize
- listingtype
- tags

Ulysses must output all headers in consistent order for exports.
Ulysses must accept these headers for imports (tolerant of extra columns, strict about tenant safety).

---

# Phase 8B – Integration Profiles + Contact UI (ActivePipe Card)

## Phase Goal

Create an “Integrations” tab on Contact details and implement an ActivePipe profile card that stores and renders ActivePipe-specific fields without bloating the core Contact model.

Phase 8B includes single-contact export (1-row CSV) to prove the mapping contract.

## Deliverables

### 1) Contact Details UI
- Add an Integrations tab to Contact details page (edit_contact view).
- Inside Integrations, render an ActivePipe card.

ActivePipe card sections:
1. Link and Status
   - status, sms_status
   - subscribed_at, unsubscribed_at, unsubscribed_reason
   - latest_interaction, modified_at, source
   - last_exported_at (from Ulysses integration record)
   - last_imported_at (from Ulysses integration record)

2. Preferences
   - buyertype, locations, propertytype, category, listingtype
   - range fields:
     - minbeds, maxbeds
     - minbaths, maxbaths
     - minprice, maxprice
     - minparking, maxparking
     - minlandsize, maxlandsize
     - minbuildingsize, maxbuildingsize

3. Tags
   - tags (render as subtle rounded-pill badges)
   - edit as text field (v1) using delimiter convention (example: semicolon-separated)

Buttons:
- Download ActivePipe CSV (this contact)
- Save changes (normal form submit)
- Clear ActivePipe fields (clears integration payload only, not the contact)

### 2) Integration Storage
Add a single generic table to store per-contact integration profiles.

Table: contact_integrations
- id (pk)
- user_id (fk to users)
- contact_id (fk to contacts)
- integration_key (text, example: 'activepipe')
- external_id (text, nullable, reserved for future)
- payload_json (jsonb, stores integration-specific fields)
- last_exported_at (timestamp)
- last_imported_at (timestamp)
- created_at, updated_at

Rules:
- Unique constraint: (user_id, contact_id, integration_key)
- All reads/writes scoped by user_id and contact_id
- No contact_integrations row required to render the contact page

### 3) Single-Contact Export
- Provide a route that downloads a 1-row ActivePipe CSV for the current contact.
- Headers must match the ActivePipe contract and remain ordered.
- Values for identity and address map from Contacts when available.
- All other ActivePipe fields map from contact_integrations.payload_json.

Update last_exported_at on success.

## File Plan (Phase 8B)

Templates:
- templates/contacts/edit_contact.html
  - Add Integrations tab and ActivePipe card partial area

Optional partial:
- templates/integrations/_activepipe_card.html

Services:
- services/integrations/activepipe.py
  - ACTIVEPIPE_HEADERS (ordered list)
  - normalize helpers (phone, ranges, tags)
  - emit_csv_row(contact, integration_payload)
  - parse_csv_row(row) (used later in 8C)

Routes:
- app.py (or routes module if present)
  - GET /integrations/activepipe/contact/<contact_id>/export.csv

Static:
- Only if needed for small enhancements. Prefer server-rendered.

Docs:
- docs/integrations/activepipe_bridge.md
  - Mapping table
  - Import merge policy
  - Export rules
  - Dedupe rules (8C-ready)

## Migration Plan (Phase 8B)

Add migration file:
- docs/migrations/YYYY_MM_DD_add_contact_integrations.sql

SQL actions:
- CREATE TABLE contact_integrations (...)
- Add unique constraint on (user_id, contact_id, integration_key)
- Add indexes:
  - (user_id, contact_id)
  - (user_id, integration_key)
  - (user_id, integration_key, external_id) optional

No destructive changes.

## Acceptance Criteria (Phase 8B)

- Integrations tab renders for any contact with no integration row
- ActivePipe card can save and reload payload fields reliably
- 1-row export downloads with correct ActivePipe headers and stable ordering
- last_exported_at updates correctly on export
- All queries are user_id scoped (no cross-tenant leakage)
- No duplicate render_template args, no uninitialized variables
- py_compile passes before commit

---

# Phase 8C – Bulk Export, Bulk Import, Logging, and Conflict Handling

## Phase Goal

Deliver high-value workflows:
- Bulk export from Ulysses to ActivePipe
- Bulk import from ActivePipe to Ulysses with safe merge and deterministic matching
- Audit logging of import and export events
- Clear preview and conflict reporting

## Deliverables

### 1) Bulk Export
From Contacts list:
- Export selected contacts OR export contacts matching current filter.
- Output ActivePipe-ready CSV with all contract headers and ordered columns.

Export options (minimal v1):
- Mode:
  - Selected contacts
  - All contacts matching filters (bounded)
- Phone mapping:
  - Prefer mobile then phone

Guardrails:
- Export cap (configurable constant). Default: 5000 rows.
- Pre-export summary shown (count and mode).
- Export is user-initiated only.

Update last_exported_at per contact integration row on export success.

### 2) Bulk Import with Preview
Provide an import page:
- Upload ActivePipe CSV
- Preview summary:
  - total rows
  - matched contacts
  - new contacts
  - updated contacts
  - conflicts
  - skipped rows (missing match keys)

Deterministic match order:
1. email
2. mobile
3. phone

Merge policy (Canon-safe default):
- For core contact fields:
  - Fill blanks only (default)
  - Overwrite mode must be explicit (checkbox, off by default)
- For integration fields:
  - Always store ActivePipe fields into payload_json
  - Update last_imported_at

Skips:
- If a row has no email and no phone and no mobile, skip with a logged reason.

### 3) Integration Event Logging
Add lightweight logging for imports and exports.

Table: integration_events
- id (pk)
- user_id
- integration_key (text, 'activepipe')
- event_type (text, 'import' or 'export')
- filename (text, nullable)
- total_rows (int)
- new_count (int)
- updated_count (int)
- conflict_count (int)
- skipped_count (int)
- created_at

Optional:
- Store a small JSON summary blob if needed, but keep it controlled.

### 4) Conflict Handling
A conflict is defined as:
- A match key indicates an existing contact (email or phone), but key identity fields differ materially (example: different firstname/lastname) AND overwrite mode is off.

Conflicts behavior:
- Do not overwrite core contact fields in default mode
- Still store integration payload_json updates
- Report conflicts in preview results and final import summary

## File Plan (Phase 8C)

Templates:
- templates/integrations/activepipe_import.html
  - upload form, preview results, import submit
- templates/integrations/activepipe_export.html (optional)
  - export options UI, or reuse Contacts UI modal

Services:
- services/integrations/activepipe.py
  - parse_csv(file)
  - validate headers
  - parse_row(row)
  - match_contact(user_id, row) with deterministic order
  - apply_merge_policy(existing_contact, row, overwrite=False)
  - upsert_contact_integration(user_id, contact_id, payload)

Routes:
- GET /integrations/activepipe/import
- POST /integrations/activepipe/import
- GET /integrations/activepipe/export.csv

Migration:
- docs/migrations/YYYY_MM_DD_add_integration_events.sql

## Acceptance Criteria (Phase 8C)

- Bulk export produces ActivePipe-ready CSV with stable ordering and correct headers
- Bulk export respects caps and does not rely on scroll regions or only current page
- Bulk import is idempotent and does not create duplicates on repeated imports
- Bulk import never crosses tenant boundaries, even if another user has matching email
- Import preview correctly reports counts and conflicts
- Default import policy fills blanks only for core contact fields
- Integration fields always stored in payload_json and timestamps update
- integration_events logs are created for every import and export
- py_compile passes before commit

---

# Release Discipline

- Any production deployment must include:
  - version bump
  - release manifest under docs/releases/
  - mention of Phase 8B or 8C completion state
- No migrations land without:
  - migration file in docs/migrations/
  - clear notes in manifest

---

# Implementation Order (No Detours)

1. Phase 8B migration: contact_integrations
2. Add Integrations tab UI and ActivePipe card (read/write payload_json)
3. Add single-contact export route and button
4. Phase 8C migration: integration_events
5. Add bulk export route and UI wiring
6. Add bulk import page with preview and merge policy
7. Add logging, conflict reporting, and final polish

---

# Notes

- This bridge is intentionally user-driven.
- No background syncing is introduced in 8B or 8C.
- No vendor scraping or automation is permitted.
- The integration model is generic to support future integrations without contact schema bloat.
