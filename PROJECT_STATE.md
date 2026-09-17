# Ulysses CRM - Project State

**Last updated:** September 17, 2026  
**Current production version:** v1.10.5  
**Current branch:** main  
**Current checkpoint:** 33badd0  
**Session mode:** Maintenance / Stabilization

## Current Architecture

Ulysses CRM is a Flask/PostgreSQL application deployed through GitHub to Render.

Primary domain modules currently include:

- `engagements.py`
- `tasks.py`
- `attention.py`
- `push_subscriptions.py`
- `push_delivery.py`

Application version is maintained in `version.py`.

## Development Rules

The governing project rules remain in:

- `docs/ULYSSES_CRM_CANON.md`
- `docs/ui_consistency_checklist_v2.md`

Key operating rules:

- Repository state is the source of truth.
- Database schema is authoritative.
- Production data is sacred.
- Develop and validate locally before production.
- No silent refactors.
- Preserve history over destructive deletion.
- Templates are contracts.
- UI changes must follow established Ulysses patterns.
- Production deployments require truthful version increments.

## Timezone Strategy

Scheduling-critical timestamps use timezone-aware values.

Ulysses uses:

- PostgreSQL `TIMESTAMPTZ` for scheduling-critical instants.
- Timezone-aware Python datetimes.
- `America/New_York` as the application/user display timezone.
- Browser `datetime-local` values as New York wall time before conversion to UTC.
- UTC instants converted to New York time before display or date-based grouping.

Do not introduce naive datetime handling into scheduling-critical code.

## Attention Engine

Current state:

- V1A - Attention evaluator: COMPLETE
- V1B - Dashboard Attention UI: COMPLETE
- V1C - Push subscriptions: COMPLETE
- V1D - Web Push delivery: COMPLETE AND PRODUCTION VALIDATED
- V1E - Notification orchestration and deduplication: DEFERRED / NEXT PLANNED PHASE
- V1F - Scheduled production dispatcher: DEFERRED

Automatic notification dispatch remains disabled.

Current maintenance work must not expand into V1E unless explicitly approved.

## Current Maintenance Queue

### 1. Associated Contacts Edit Bug

Reproducible error when editing an existing associated contact:

`Could not update association: name 'update_contact_association' is not defined`

Investigate the existing association update route/helper before changing architecture.

### 2. Engagement Navigation

Replace ambiguous `Back` navigation with `Back to Contact` or equivalent.

### 3. Open House Archiving

Allow Open Houses to be archived rather than destructively deleted.

Archived Open Houses should leave the normal operational view while preserving history.

### 4. Dashboard Follow-ups Mobile Layout

Improve mobile Follow-up presentation.

Intended hierarchy:

- Row 1: Contact name + follow-up date
- Row 2: Last engagement plus useful context such as notes or summary

Follow established Dashboard mobile presentation patterns.

### 5. Listing Checklist Management

Review and improve the existing listing checklist.

Desired capabilities include:

- Add checklist items
- Remove or hide checklist items
- Preserve existing checklist history appropriately

Do not choose the data model until the current checklist schema and implementation are inspected.

## RESUME HERE

Current session is Maintenance / Stabilization.

Begin with the Associated Contacts edit bug.

Work one issue at a time:

1. Inspect existing implementation.
2. Scope the change.
3. Modify locally.
4. Test locally.
5. Review diff.
6. Commit.
7. Move to the next issue.
