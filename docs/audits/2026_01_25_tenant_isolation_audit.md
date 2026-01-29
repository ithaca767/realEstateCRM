# Tenant Isolation Audit — Ulysses CRM
Date: 2026-01-25
Scope: Local (schema_local.sql) + codebase (app.py, tasks.py, engagements.py, other *.py)
Goal: Hard tenant isolation; no cross-user reads/writes by ID guessing; no leaks in list/search/export/feed/public endpoints.

## Ground Rules
- Default tenant key: user_id
- Allowed alternate owner keys (must be treated as tenant keys consistently):
  - created_by_user_id (Open Houses)
  - owner_user_id (only when derived from a tenant-owned record or token)
- Every SELECT/UPDATE/DELETE must be tenant-scoped:
  - WHERE user_id = current_user.id
  - OR WHERE created_by_user_id = current_user.id
  - OR parent-join that enforces tenant ownership
- Public routes must derive tenant ownership from an unguessable token and write with that owner id.

## Status Legend
- PASS: Tenant-safe as implemented
- FIXED: Was unsafe; fixed in this audit (documented)
- TODO: Known gap; requires change
- DEFER: Requires production users rollout first

## What was changed in this chat (memorialized)
- Professionals: helper signature updated to get_professionals_for_dropdown(user_id, category=None) and all call sites updated to pass current_user.id. Professionals table now requires user_id locally for true isolation.
- Open Houses: open_houses uses created_by_user_id. Public /openhouse/<token> signin INSERT updated to include user_id = owner_user_id (defense in depth). open_house_signins requires user_id column + backfill.

## Schema Inventory
### Tables with tenant key (user_id or approved owner key)
(list here)

### Tables missing tenant key (must be fixed or parent-scoped)
(list here)

## Code Hotspots Checklist
### List routes
- Must filter by tenant key

### Detail routes
- Must fetch with id AND tenant key (or validate ownership before fetch)

### Mutations
- UPDATE/DELETE must include tenant key in WHERE
- INSERT must set tenant key

### Search endpoints
- Must filter by tenant key

### Exports
- Must validate tenant ownership before export and scope data query

### Feeds (calendar/ICS)
- Must be bound to a user-specific secret/token and scope queries

### Public endpoints
- Must derive tenant via token and never allow ID-based enumeration

## Findings and Fixes Log
Format per entry:
- Area:
- File:line:
- Problem:
- Fix:
- Verification:


## Tenant Key Inventory (from schema_local.sql)
### user_id NOT NULL (tenant-keyed)
- brand_settings.user_id
- contact_associations.user_id
- contacts.user_id
- engagements.user_id
- password_resets.user_id
- task_document_links.user_id
- tasks.user_id
- transaction_deadlines.user_id
- transactions.user_id

### created_by_user_id NOT NULL (tenant-keyed)
- newsletter_signup_links.created_by_user_id
- open_houses.created_by_user_id

### Missing tenant key (requires fix)
- open_house_signins (no user_id; must add + backfill for defense in depth)


## Open Houses — open_house_signins.user_id migration (LOCAL)
- Status: FIXED (defense in depth)
- Evidence:
  - \d+ open_house_signins shows user_id integer NOT NULL
  - Indexes: idx_open_house_signins_user_id, idx_open_house_signins_open_house_user
  - Backfill checks:
    - SELECT COUNT(*) FROM open_house_signins WHERE user_id IS NULL; => 0
    - SELECT COUNT(*) FROM open_house_signins WHERE user_id IS NULL OR user_id = 0; => 0
    
    ## Open Houses — Tenant scoping for list/detail/export (LOCAL)
- Status: FIXED
- Tenant keys:
  - open_houses.created_by_user_id = current_user.id
  - open_house_signins.user_id = current_user.id
- Code changes (app.py):
  - /openhouses (list):
    - Ensured query filters open_houses by created_by_user_id = current_user.id
  - /openhouses/<open_house_id> (detail):
    - Ensured open house fetch validates id AND created_by_user_id = current_user.id
    - Ensured signins query filters by open_house_id AND user_id = current_user.id
  - /openhouses/<open_house_id>/export.csv (export):
    - Ensured ownership check filters open_houses by id AND created_by_user_id = current_user.id
    - Ensured export query filters open_house_signins by open_house_id AND user_id = current_user.id
      - Example:
        - WHERE open_house_id = %s AND user_id = %s  (open_house_id, current_user.id)
- Rationale:
  - Prevent cross-tenant access via guessed open_house_id
  - Prevent cross-tenant leakage in signins display and CSV export
- Verification:
  - As User A, attempting to access User B’s /openhouses/<id> returns 404
  - As User A, attempting to export User B’s /openhouses/<id>/export.csv returns 404
  - As User A, signins shown for an owned open house only include rows with user_id = current_user.id
  
  ## Open Houses — Tenant Isolation (LOCAL)
Status: CLOSED

### Ownership model
- open_houses.created_by_user_id is the sole owner key
- open_house_signins.user_id mirrors the owning open house user

### Routes verified
- /openhouses (list)
  - Scoped by created_by_user_id = current_user.id
- /openhouses/<id> (detail)
  - Ownership enforced via id AND created_by_user_id
  - Sign-ins scoped by open_house_signins.user_id
- /openhouses/<id>/export.csv
  - Ownership verified prior to export
  - Export rows scoped by open_house_signins.user_id
- /openhouse/<token> (public)
  - Token resolves open house
  - Owner user derived from created_by_user_id
  - All contact updates, inserts, and sign-ins written with owner user_id

### Schema verification
- open_house_signins.user_id present, NOT NULL, indexed
- Backfill verified (0 NULL user_id rows)

### Negative tests
- Cross-user ID guessing returns 404 for detail and export
- User B cannot view or export User A open houses



