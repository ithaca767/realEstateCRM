# Ulysses CRM - Project State

**Last updated:** September 17, 2026  
**Current production version:** v1.10.8
**Current branch:** main  
**Current checkpoint:** 26478f1
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

### 3. Open House Archiving - COMPLETE

Completed and locally validated September 18, 2026.

- Added `archived_at timestamptz` to `open_houses`.
- Active Open Houses are the default operational view.
- Added separate Active and Archived views.
- Added tenant-scoped POST-only Archive and Unarchive actions.
- Archiving preserves the Open House record and sign-in history.
- Archived Open House detail and CSV export remain accessible to the owner.
- Archived public sign-in links display a closed message and cannot process new sign-ins.
- Unarchiving restores the same public sign-in link.
- Application version bumped to v1.10.8.
- Local migration: `docs/migrations/2026_09_17_open_houses_add_archived_at.sql`.
- Implementation checkpoint: `005cd21`.
- Production database migration completed and verified September 17, 2026.
- Production v1.10.8 deployed and fully validated September 17, 2026.
- Production validation confirmed Active/Archived views, preserved sign-in history and CSV access, Archive/Unarchive lifecycle, and public sign-in closure/restoration.

### 4. Dashboard Follow-ups Mobile Layout - COMPLETE

Completed and locally validated September 17, 2026.

- Added a dedicated responsive mobile Follow-up presentation without changing Follow-up behavior.
- Mobile hierarchy presents contact name and due date first, followed by Last Engagement context and actions.
- Preserved the existing desktop table while refining desktop column proportions.
- Constrained the desktop Name column and allowed Last Engagement to use the flexible remaining width.
- Last Engagement detail is limited to two lines by default with an in-place `See more` / `See less` control.
- Preserved the existing Open and Done actions.
- No database, query, Follow-up lifecycle, or Attention Engine changes were required.
- Application version bumped to v1.10.9.
- Implementation checkpoint: `26478f1`.

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

Open House Archiving is complete and production validated in v1.10.8 at checkpoint `005cd21`.

Dashboard Follow-ups Mobile Layout is complete and locally validated in v1.10.9 at checkpoint `26478f1`.

Next: Listing Checklist Management.

Review and improve the existing listing checklist.

Desired capabilities include:

1. Add checklist items.
2. Remove or hide checklist items.
3. Preserve existing checklist history appropriately.

Do not choose the data model or deletion/archive/hide behavior until the current checklist schema and implementation are inspected.

Work one issue at a time:

1. Inspect existing implementation.
2. Scope the change.
3. Modify locally.
4. Test locally.
5. Review diff.
6. Commit.
7. Move to the next issue.
