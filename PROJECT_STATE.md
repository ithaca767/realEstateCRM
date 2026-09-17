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

### 1. Associated Contacts Edit Bug - COMPLETE

Fixed and locally validated September 17, 2026.

- Added the missing `update_contact_association()` helper.
- Preserved the existing live Edit Association UI and route.
- Update is tenant-safe and verifies that the association includes the current contact.
- Notes and relationship edits were manually tested and confirmed persistent.
- Application version bumped to v1.10.6.
- Implementation checkpoint: `c7a4b80`.

### 2. Engagement Navigation - COMPLETE

Fixed and locally validated September 17, 2026.

- Changed the ordinary View / Edit Engagement page-level navigation from `Back` to `Back to Contact`.
- Preserved the existing destination to the associated Contact's Engagements section.
- Follow-up navigation was already correctly labeled `Back to Contact` and was left unchanged.
- Application version bumped to v1.10.7.
- Implementation checkpoint: `540a470`.

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

Associated Contacts editing is complete at checkpoint `c7a4b80`.

Engagement Navigation is complete at checkpoint `540a470`.

Next: Open House Archiving.

Inspect the existing Open House schema, routes, templates, and current delete behavior before choosing an implementation. The goal is to allow Open Houses to leave the normal operational view while preserving their history. Do not alter the data model or delete behavior until the existing implementation is understood.

Work one issue at a time:

1. Inspect existing implementation.
2. Scope the change.
3. Modify locally.
4. Test locally.
5. Review diff.
6. Commit.
7. Move to the next issue.
