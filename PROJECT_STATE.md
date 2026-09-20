# Ulysses CRM - Project State

**Last updated:** September 20, 2026
**Current production version:** v1.10.10
**Current branch:** main
**Current checkpoint:** da509d1
**Session mode:** Calendar Foundation Complete / Next Work Prioritization

## Current Architecture

Ulysses CRM is a Flask/PostgreSQL application deployed through GitHub to Render.

Primary domain modules currently include:

- `engagements.py`
- `tasks.py`
- `attention.py`
- `push_subscriptions.py`
- `push_delivery.py`
- `activity_engine.py`
- `calendar_activity.py`
- `calendar_feed.py`
- `calendar_ics.py`

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
- The authenticated account's configured timezone for runtime display, scheduling, and calendar presentation.
- `America/New_York` as the current/default account timezone when no different valid account timezone is configured.
- Browser `datetime-local` values as account-local wall time before conversion to UTC.
- UTC instants converted to the account timezone before display or date-based grouping.
- Date-only values remain true dates and must not be converted into artificial timed instants.

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
- Production v1.10.9 deployed and validated September 17, 2026.
- Production validation confirmed desktop and mobile responsive presentation and working `See more` / `See less` behavior.

### 5. Listing Checklist Management - COMPLETE

Completed, deployed, and production validated September 18, 2026.

- Seller checklist items can be added per contact with optional due dates.

- Seller checklist items are removed operationally through archival rather than destructive deletion.

- Seller checklist updates and archival are tenant-scoped.

- Existing Seller checklist history is preserved.

- Buyer Checklist was modernized from fixed `buyer_profiles` boolean fields to independent per-contact checklist item records.

- Existing Buyer checklist values were migrated without changing their completion state.

- Buyer checklist items support completion status, optional due dates, custom items, and archival removal.

- Legacy Buyer checklist columns remain in `buyer_profiles` as a safety net but are no longer written by the application.

- Seller production migration: `docs/migrations/2026_09_18_listing_checklist_add_archived_at.sql`.

- Buyer production migration: `docs/migrations/2026_09_18_buyer_checklist_items.sql`.

- Seller implementation checkpoints: `5e3bf1e`, `4d99a4a`, `6d2220a`.

- Buyer implementation checkpoint: `83f401e`.

- Production Seller migration verified with 345 existing checklist rows preserved.

- Production Buyer migration verified with 98 expected rows, 98 matched rows, and 0 mismatches across 14 Buyer Profiles.

- Production application deployed through checkpoint `83f401e`.

- Application version bumped to v1.10.10.

### Deferred Maintenance Note

- Intermittent stale `Please log in to access this page.` flash messages have occasionally appeared while the user is already authenticated, on both desktop and mobile.
- During September 17, 2026 production validation, two identical messages were present but did not return after dismissal and Dashboard refresh.
- No authentication change was made because the issue was not reproducible on refresh and existing login protection appeared to be functioning normally.
- Investigate only when the behavior can be reproduced reliably.

## Calendar Foundation - COMPLETE AND PRODUCTION VALIDATED

Completed September 20, 2026 through checkpoint `0f67799`.

The legacy direct Follow-up ICS implementation has been replaced by the shared Calendar architecture:

`Activity Engine -> Calendar Integration Layer / Adapter -> ICS serializer -> /followups.ics`

Current Calendar rules:

- `/followups.ics` is one consumer of Ulysses Calendar services, not the Calendar architecture itself.
- Calendar retrieval is tenant-isolated by exact `user_id`; there is no admin bypass.
- External calendar subscriptions use per-user credentials. The credential resolves exactly one owning user.
- Raw calendar credentials are returned only when generated and are never stored.
- Regenerating a Calendar Feed revokes the prior active credential.
- Calendar Feed management is available at `More > Calendar Feed`.
- Only `calendar_eligible` Activities are exported.
- Timed Activities are converted to the credential owner's account timezone.
- Date-only Activities remain true all-day events.
- Calendar event UIDs are derived from stable Activity identity.
- ICS serialization contains no database, tenant, authentication, or Flask logic.
- Invalid, missing, revoked, or otherwise unusable credentials return the same non-disclosing Calendar Feed unavailable response.
- Safari Calendar subscription was manually validated against the local feed.
- Calendar route, credential management, adapter, and serializer tests are in place.
- Full local suite passed: 84 tests.
- Production deployment and end-to-end Calendar validation completed September 20, 2026.
- Production migration `docs/migrations/2026_09_20_users_add_timezone_name.sql` was applied successfully; all existing production users were assigned `America/New_York`, with a non-null account timezone and the intended default.
- Production migration `docs/migrations/2026_09_20_calendar_feed_tokens.sql` was applied successfully; the per-user credential table and active-user/token-hash uniqueness indexes were verified.
- Production Calendar Feed credential generation was manually validated.
- A production Calendar subscription successfully returned real Ulysses Engagement Follow-up Activities.
- No Transaction Deadline Activity was available during production QA, so the production all-day deadline path remains covered by automated/local validation rather than a live production example.
- Regenerating the production Calendar Feed credential successfully revoked the prior credential; the old subscription URL returned the expected unavailable/error response.
- Production environment requirements `TOKEN_PEPPER` and `PUBLIC_BASE_URL` were confirmed present without exposing their values.

### Future Calendar Connection UX

The credential-bearing subscription URL remains part of the Calendar integration protocol, but it should not need to be exposed during the normal user experience.

Preferred future UX:

- Present provider-oriented connection actions such as Apple Calendar, Google Calendar, and Outlook where supported.
- Generate and pass the per-user credential through the connection workflow rather than requiring routine manual URL handling.
- Use confirmation UI for connecting, resetting, or revoking a Calendar connection.
- Preserve an Advanced / Manual Setup option that exposes the one-time subscription URL for unsupported calendar clients or troubleshooting.
- The existing security model remains unchanged: raw credentials are not stored, credential ownership remains tenant-specific, and resetting a connection revokes the prior active credential.

Implementation checkpoints:

- `59c10e8` - Use account timezone in Activity Engine
- `931832b` - Add per-user calendar feed credentials
- `beae871` - Add Activity Engine calendar adapter
- `231e9f0` - Add Activity calendar ICS serializer
- `0f67799` - Integrate tenant-isolated Activity calendar feed

## Ulysses Assist - ARCHITECTURAL DIRECTION LOCKED

Ulysses Assist is a conversational interface to Ulysses, not an AI feature bolted onto Ulysses.

Assist must operate through bounded Ulysses-owned services and tools. The model must never receive unrestricted database access or a wholesale database dump.

Non-negotiable Assist invariants:

1. Tenant isolation is enforced below the AI layer. No user, administrator, Assist request, background job, API, or future voice client may use AI as a path around user-level data isolation.
2. Entity resolution occurs before synthesis. A name, property, listing, transaction, or other reference must be resolved to authorized CRM entities before related records are assembled.
3. Cross-client contamination is prohibited. Context may expand across contacts only through explicit Ulysses relationships or other authoritative CRM associations.
4. CRM facts are source-grounded. Important factual assertions should retain the Ulysses record or object from which they were retrieved.
5. Conversation state is not authoritative CRM data. Conversational context may preserve references such as "they" or "that transaction," but current CRM facts must be retrieved from authoritative Ulysses data when they matter.
6. Reads and writes are separate operations. Assist may retrieve and summarize authorized data naturally. Mutations must pass through defined Ulysses services/actions that validate ownership, permissions, data shape, and business rules.
7. The model must not directly write SQL or manipulate database rows.
8. If a requested fact is not established by authorized Ulysses data, Assist must not invent it.

The intended retrieval pattern is:

`Authenticated User -> Entity Resolution -> Tenant-Scoped Ulysses Services -> Bounded Retrieval Envelope -> Assist`

The intended mutation pattern is:

`Assist Request -> Entity Resolution -> Proposed Structured Action -> Ulysses Validation / Authorization -> CRM Mutation`

The Activity Engine and Calendar Integration Layer are foundational services for Assist. Future consumers should use the same authoritative service layer rather than parse ICS or recreate Calendar logic.

## Assist Product Direction

Assist will begin web-first inside the authenticated Ulysses application, but the intelligence layer must be interface-independent and voice-ready.

The same Assist services are intended to support:

- the Ulysses web conversation interface;
- text conversation about contacts, engagements, Activities, transactions, listings, and Calendar;
- document intake and structured proposed CRM updates;
- one-tap mobile access;
- voice-first interaction;
- future mobile or native clients;
- notifications and daily briefings.

A future voice client may use a selected call name such as `Ulysses` or `Penelope`; this is a presentation preference and must not create a separate intelligence or data-access architecture.

Document intake is an Assist capability, not a separate source of CRM truth. Documents may be interpreted by AI, but proposed data must be resolved to the correct authorized CRM entities and validated by Ulysses before persistence.

## Active Feature Backlog

Captured September 20, 2026 from the current approved feature-request list. These items are approved for planning, but inclusion here does not mean that architecture, implementation order, or release scope has been finalized.

### Activity / Task / Reminder Foundation

- Support independent real-estate Tasks that are not required to belong to a Contact, such as `Send emails to commercial contacts`, `Send out mass mailer`, or `Start marketing campaign`.
- Determine whether the existing Task / Activity model can support both Contact-associated and independent CRM work without creating a duplicate task system.
- Add Reminders for real-estate work. Reminders may be associated with Contacts when appropriate but must also support independent CRM work.
- Future reminder delivery should consider integration with the user's external reminder/calendar environment while preserving Ulysses as the authoritative CRM context.
- Before implementation, explicitly define the relationship among Activity, Task, Reminder, due date/time, completion, association, Calendar eligibility, and notification behavior.

### Dashboard / Contact Workflow

- Set apart `Active` clients on the Dashboard, representing clients with signed contracts.
- Add an `Add Contact` action to the Dashboard Active Contacts card.
- Consider isolating imported Contacts in a separate view/tab until they are activated or reactivated.
- Add search capability for Professionals.

### Buyer / Seller Data

- Add square footage, bedrooms, and bathrooms to Buyer and Seller sheets/profiles, including minimum requirements where applicable.
- Add per-square-foot pricing support for commercial leases.

### Transactions / Listings / Offers

- Add a Notes field to Transactions.
- Add an Agent field to Transactions.
- Design Listing and Offer status handling as a dedicated branch before implementation.

### Showings / Feedback

- Add showing interactions and agent feedback for Sellers.
- Before implementation, evaluate a generalized Showing model that can support both Buyer and Seller workflows rather than creating separate showing systems.
- A Showing may become relevant to an Offer or Transaction, but an Offer remains a distinct business object.

### Reporting / Assist

- Add a daily interactions report or summary.
- Evaluate the daily summary as an Assist / Activity Engine capability so conversational briefings and traditional presentation do not develop conflicting interpretations of CRM activity.

### Checklist Polish

- Optional future polish for Transaction and Checklist tabs: subtle `Changes save automatically` text or a disabled `Auto-saved` indicator.
- This is not required for current functionality and should not displace higher-value work.

### Backlog Planning Notes

- Activity / Task / Reminder semantics should be reviewed first because they affect Calendar, Attention Engine, notifications, daily briefings, and Ulysses Assist.
- Perform the previously identified tenant-isolation audit before exposing broader CRM retrieval services to Ulysses Assist.
- Showing / Feedback requires architecture review before implementation.
- Calendar connection UX improvements remain banked for later; the current production Calendar Feed is functional and secure.
- Ulysses Assist remains architecturally approved but implementation has not begun.

## RESUME HERE

Maintenance / Stabilization queue completed September 18, 2026.

Calendar foundation completed and production validated September 20, 2026. Production schema migrations, credential generation, live Calendar subscription, and credential revocation were successfully verified.

The intermittent stale `Please log in to access this page.` flash remains deferred until it can be reproduced reliably.

No numbered Maintenance / Stabilization queue items remain.

Before beginning the next implementation, review and prioritize the approved feature list. Ulysses Assist architecture is now directionally locked, but Assist implementation has not begun. Preserve the Calendar, tenant-isolation, timezone, entity-resolution, source-grounding, and validated-mutation contracts when designing future work.
