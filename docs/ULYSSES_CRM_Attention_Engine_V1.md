(venv) dennisfotopoulos@Denniss-MacBook-Air real-estate-crm % cat
docs/ULYSSES_CRM_Attention_Engine_V1.md \# Ulysses CRM -- Attention
Engine V1

**Initial baseline:** Ulysses CRM v1.10.3\
**Current checkpoint:** Ulysses CRM v1.10.5\
**Status:** V1A-V1D complete and production validated; ready for V1E\
**Phase type:** Architecture / incremental feature development\
**Last reviewed:** August 25, 2026

## Purpose

The Ulysses Attention Engine is intended to proactively surface CRM
items that require the user's attention while preserving Ulysses'
existing source-of-truth, user-intent, and AI guardrail principles.

The Attention Engine is not a second follow-up system. It is an
evaluation layer above existing operational records.

Current architecture:

``` text
Existing operational records
    ├── Engagement Follow-ups
    ├── Tasks
    ├── Transaction milestone dates
    └── Transaction Deadlines
              ↓
        Attention Engine
              ↓
       Notification Policy
              ↓
 Delivery / Deduplication State
              ↓
         Push Delivery
              ↓
      Push Subscriptions
              ↓
       Authorized Devices
```

Future scheduled architecture:

``` text
        Render Scheduler
              ↓
        Attention Engine
              ↓
       Notification Policy
              ↓
 Delivery / Deduplication State
              ↓
         Push Delivery
              ↓
      Push Subscriptions
              ↓
       Authorized Devices
```

The Flask/Gunicorn web process must not run its own internal scheduler.

------------------------------------------------------------------------

## Current Architecture Audit

### Repository State at Start

The repository was verified before implementation:

-   Branch: `main`
-   Branch is up to date with `origin/main`
-   Working tree is clean
-   Current application version: `v1.10.3`
-   Existing top-level domain modules include:
    -   `engagements.py`
    -   `tasks.py`
-   `templates/base.html` exists
-   No current service worker was found
-   No current push-subscription implementation was found
-   No migration framework was identified in the repository scan

This is the clean baseline for Attention Engine development.

------------------------------------------------------------------------

## Existing Operational Sources

### 1. Engagement Follow-ups --- KEEP / REUSE

Phase 11 made Follow-ups first-class child engagement records.

Relevant fields in `engagements`:

-   `parent_engagement_id`
-   `requires_follow_up`
-   `follow_up_due_at`
-   `follow_up_completed`
-   `follow_up_completed_at`

`follow_up_due_at` is stored as `TIMESTAMPTZ`.

The existing Follow-up model remains the source of truth. The Attention
Engine must not create a parallel Follow-up entity or duplicate
Follow-up state.

### 2. Tasks --- KEEP / FUTURE REUSE

The `tasks` table already contains fields suitable for later Attention
rules:

-   `status`
-   `priority`
-   `due_date`
-   `due_at`
-   `snoozed_until`
-   `completed_at`
-   `canceled_at`
-   links to contacts, transactions, engagements, and professionals

`due_at` and `snoozed_until` are `TIMESTAMPTZ`.

Tasks are intentionally excluded from V1A.

### 3. Transactions --- KEEP / FUTURE REUSE

The `transactions` table contains built-in milestone dates including:

-   attorney review end date
-   inspection deadline
-   financing contingency date
-   appraisal deadline
-   mortgage commitment date
-   expected close date
-   actual close date

These remain transaction data and must not be duplicated into the
Attention Engine.

### 4. Transaction Deadlines --- KEEP / FUTURE REUSE

The `transaction_deadlines` table stores additional manual transaction
deadlines.

Relevant fields include:

-   `transaction_id`
-   `name`
-   `due_date`
-   `is_done`
-   `notes`

The existing distinction between built-in transaction milestone dates
and manual transaction deadlines must be preserved.

Transaction deadlines are intentionally excluded from V1A.

------------------------------------------------------------------------

## Legacy Reminder Architecture --- RETIRE, BUT NOT DURING V1A

An older reminder prototype remains partially present.

The `interactions` table still contains:

-   `due_at`
-   `notified`
-   `is_completed`

The current `app.py` also still contains:

``` text
/api/reminders/due
```

That endpoint reads due interaction records and marks
`interactions.notified = TRUE`.

A repository search found no current frontend references to:

-   `Notification.`
-   `requestPermission`
-   `serviceWorker`
-   `PushManager`
-   push subscriptions

Therefore, the legacy browser-notification frontend appears to no longer
be active, while the backend endpoint and database fields remain.

### Decision

The legacy interaction reminder system is classified as:

**RETIRE / DO NOT BUILD UPON**

However, it will not be removed as part of V1A.

Legacy cleanup will be handled separately after the replacement
Attention architecture is functioning. This avoids mixing feature
development with unrelated cleanup or silent refactoring.

------------------------------------------------------------------------

## Attention Engine Design Principle

Attention is **calculated state**, not a new CRM entity.

For example, an overdue Follow-up is already persisted in `engagements`.
The Attention Engine should evaluate that existing record rather than
create a second record merely stating that the Follow-up is overdue.

Therefore:

``` text
Follow-up = persisted operational record
Attention = evaluation of operational state
```

V1A requires no new database table.

------------------------------------------------------------------------

## AI Boundary

The Attention Engine V1 is deterministic application logic, not an AI
agent.

It may evaluate explicit facts already stored in Ulysses, such as
whether a user-created Follow-up is overdue.

It must not autonomously:

-   create a Follow-up
-   schedule a Follow-up
-   modify CRM records
-   infer that a client is strategically important
-   decide what action the user should take
-   save AI-generated output

Example deterministic rule:

``` text
Incomplete child Follow-up
+ due time has arrived or passed
= Attention candidate
```

This preserves Ulysses' existing AI and user-intent guardrails.

------------------------------------------------------------------------

# V1A -- Overdue Follow-up Attention

## Scope

V1A evaluates **overdue child Follow-ups only**.

It does not include:

-   Push notifications
-   Browser notification permission
-   Service workers
-   Render scheduling
-   Tasks
-   Transaction deadlines
-   AI
-   legacy interaction reminders
-   database migrations

## V1A Rule

An Attention candidate exists when:

``` sql
parent_engagement_id IS NOT NULL
AND requires_follow_up = TRUE
AND follow_up_completed = FALSE
AND follow_up_due_at IS NOT NULL
AND follow_up_due_at <= current_time
```

The comparison must preserve Ulysses' timezone strategy.
`follow_up_due_at` is already stored as `TIMESTAMPTZ`.

For testability, the evaluator should support receiving an explicit
timezone-aware `now` value rather than depending exclusively on the
system clock.

## V1A Output Contract

The Attention Engine should return normalized items containing enough
information for future UI and notification consumers.

Initial conceptual shape:

``` python
{
    "attention_type": "overdue_followup",
    "source_type": "engagement",
    "source_id": 123,
    "contact_id": 45,
    "contact_name": "Contact Name",
    "due_at": due_datetime,
    "snippet": "Follow-up context",
    "target_url": "/engagements/123/edit"
}
```

Attention rows are not persisted in V1A.

------------------------------------------------------------------------

## Code Location

V1A will introduce a top-level module:

``` text
attention.py
```

This matches the current repository structure alongside:

``` text
engagements.py
tasks.py
```

The initial public interface should be conceptually similar to:

``` python
list_attention_items(conn, user_id, now=None)
```

The exact implementation may be adjusted to match existing database
helper conventions.

### Single Evaluator Principle

Attention rules must not be duplicated across consumers.

Future architecture:

``` text
Dashboard ───────┐
                 ├── Attention Engine
Render Dispatcher┘
```

The Dashboard and future Render dispatcher should consume the same
Attention evaluator.

------------------------------------------------------------------------

# Implementation Through V1D

## V1A -- Attention Evaluator

**Status: COMPLETE**

-   Added `attention.py`
-   Evaluates overdue child Follow-ups
-   Uses timezone-aware comparisons
-   Attention remains calculated state
-   Tested against known LOCAL Follow-ups

## V1B -- Ulysses Attention UI

**Status: COMPLETE**

The Dashboard consumes the same `attention.py` evaluator for overdue
Follow-ups. The Dashboard does not maintain a separate overdue rule.

## V1C -- Permission-Based Push Subscriptions

**Status: COMPLETE AND DEPLOYED**

Push permission is stored per browser/device subscription. One user may
have multiple authorized devices.

Implemented production table:

``` sql
CREATE TABLE push_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL UNIQUE,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ
);
```

The implemented field is `last_seen_at`, not the earlier conceptual
`last_used_at`.

Implemented components include:

``` text
push_subscriptions.py
static/push-notifications.js
static/service-worker.js
GET  /api/push/public-key
POST /api/push/subscribe
```

The Account/Profile UI provides explicit device-level controls to enable
and turn off notifications.

Web Push uses stable VAPID credentials supplied through
`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, and `VAPID_SUBJECT`.

## V1D -- Web Push Delivery

**Status: COMPLETE AND PRODUCTION VALIDATED**

V1D introduced `push_delivery.py` using `pywebpush==2.1.2`.

The server sends JSON payloads containing `title`, `body`, and `url`.
Attention items include `target_url`; overdue Follow-ups target
`/engagements/<source_id>/edit`.

The service worker receives the push, displays it, and uses the target
URL when the user clicks **Show**. It focuses an existing Ulysses window
when possible or opens a new one.

### Production Validation -- August 25, 2026

V1D was validated end-to-end in production as Ulysses CRM v1.10.5.

Production validation confirmed:

-   the expected `push_subscriptions` schema exists
-   a real active production subscription was created for user ID 1
-   the production Chrome subscription used an FCM Web Push endpoint
-   Render loaded the VAPID environment variables
-   Chrome reported `Notification.permission = granted`
-   the production service worker was activated
-   direct production `showNotification()` succeeded
-   macOS Chrome notification permission was enabled
-   a controlled Attention push was sent for Ethelene Lambert,
    engagement 586
-   the push provider returned HTTP 201
-   the notification appeared
-   clicking **Show** opened `/engagements/586/edit`

Validated production path:

``` text
Production CRM data
        ↓
Attention Engine
        ↓
Overdue Follow-up candidate
        ↓
target_url
        ↓
push_delivery.py
        ↓
Web Push provider / FCM
        ↓
Chrome
        ↓
macOS notification
        ↓
User clicks Show
        ↓
Exact Ulysses engagement
```

A successful provider response does not by itself prove visible OS
presentation. Browser site permission and operating-system browser
notification permission are separate layers.

------------------------------------------------------------------------

# Current Production Boundary

As of v1.10.5, Ulysses can calculate and display overdue Follow-up
Attention items, manage device subscriptions, deliver Web Push with CRM
context, and navigate directly to the exact engagement.

Automatic notification dispatch is intentionally still disabled.

------------------------------------------------------------------------

# V1E -- Notification Orchestration and Deduplication

**Status: NEXT PHASE**

V1E makes Web Push safe to automate before any scheduler is added.

The same unchanged Attention condition must not generate another
notification every time the evaluator runs.

Do not add a generic `notified` field to `engagements`. Notification
state belongs to the notification/orchestration layer.

V1E must establish:

-   deterministic notification eligibility
-   delivery/deduplication state
-   successful-send recording
-   handling of inactive subscriptions
-   behavior with multiple active subscriptions
-   behavior when delivery fails
-   identity of an Attention condition
-   a callable orchestration function for the future scheduler

The exact schema must distinguish the Attention event itself from
delivery attempts to individual subscriptions.

------------------------------------------------------------------------

# V1F -- Scheduled Production Dispatcher

**Status: DEFERRED UNTIL V1E IS PROVEN**

Only after V1E is working safely should Render invoke the orchestration
automatically.

``` text
Render Scheduler
        ↓
V1E orchestration function
        ↓
Attention Engine
        ↓
Notification Policy
        ↓
Delivery / Deduplication State
        ↓
Authorized push subscriptions
        ↓
Web Push
```

The dispatcher must run outside the Flask/Gunicorn web process.

------------------------------------------------------------------------

# Future Attention Sources

After V1 is stable, deterministic Attention rules may expand to:

### Tasks

Potential inputs:

-   open status
-   due time/date
-   snooze state
-   completion/cancellation state
-   priority

### Transaction Milestones

Potential inputs:

-   attorney review end
-   inspection deadline
-   financing contingency
-   appraisal deadline
-   mortgage commitment
-   expected closing

### Manual Transaction Deadlines

Potential inputs:

-   due date
-   completion state

Future rules must continue to read the canonical operational records
rather than duplicating their state.

Subjective or inferential rules, such as determining that a client has
been neglected or deciding which client is strategically important, are
outside V1 and require separate design review.

------------------------------------------------------------------------

# Timestamp Note

The current database contains some historical timestamp inconsistency.

Scheduling-critical fields relevant to Attention include timezone-aware
values such as:

-   `engagements.follow_up_due_at` --- `TIMESTAMPTZ`
-   `tasks.due_at` --- `TIMESTAMPTZ`
-   `tasks.snoozed_until` --- `TIMESTAMPTZ`
-   `push_subscriptions.created_at` --- `TIMESTAMPTZ`
-   `push_subscriptions.updated_at` --- `TIMESTAMPTZ`
-   `push_subscriptions.last_seen_at` --- `TIMESTAMPTZ`

Other older fields use `TIMESTAMP WITHOUT TIME ZONE`.

Attention Engine development must not expand into an unrelated timestamp
migration. Existing historical timestamp cleanup is outside this phase.

------------------------------------------------------------------------

# Locked V1 Decisions

1.  The Attention Engine sits above existing operational records.
2.  Existing Follow-ups remain canonical child engagements.
3.  The initial Attention rule evaluates overdue Follow-ups only.
4.  Attention itself is calculated rather than persisted.
5.  `attention.py` owns the Attention rule.
6.  Consumers reuse the same evaluator.
7.  Tasks and transaction deadlines remain future Attention sources.
8.  Push permission is per browser/device subscription.
9.  One user may have multiple push subscriptions.
10. Push subscriptions may be activated or deactivated independently.
11. Web Push uses stable VAPID credentials.
12. Notification delivery state is separate from operational CRM
    records.
13. A generic `notified` field must not be added to `engagements`.
14. Notifications may contain a target URL to the exact CRM record.
15. The service worker owns browser notification presentation and click
    navigation.
16. V1D Web Push delivery has been validated in production.
17. A successful provider response does not by itself prove visible OS
    presentation.
18. Browser permission and operating-system notification permission are
    separate layers.
19. Automatic dispatch remains disabled until
    orchestration/deduplication exists.
20. V1E implements orchestration and deduplication before scheduling.
21. V1F introduces the Render scheduler only after V1E is proven.
22. The scheduler must run outside Flask/Gunicorn.
23. The legacy `interactions` reminder architecture will not be reused.
24. Legacy reminder cleanup remains separate.
25. Attention Engine V1 contains no AI and makes no autonomous CRM
    record changes.

------------------------------------------------------------------------

# Implementation Checkpoint

``` text
V1A  Attention evaluator                         COMPLETE
V1B  Dashboard Attention UI                      COMPLETE
V1C  Permission-based push subscriptions         COMPLETE
V1D  Web Push + exact engagement navigation      COMPLETE
      Production validation                      COMPLETE
V1E  Notification orchestration + deduplication  NEXT
V1F  Render scheduled dispatcher                 DEFERRED
```

Current production version: `v1.10.5`

------------------------------------------------------------------------

# Immediate Next Step

Design V1E before writing code.

Specifically determine:

1.  what uniquely identifies a notification-worthy Attention condition
2.  what delivery/deduplication state must be persisted
3.  whether state is per Attention condition, per device delivery, or
    both
4.  when a previously notified condition may become eligible again
5.  how failed delivery differs from successful notification
6.  how multiple active device subscriptions are handled
7.  what callable orchestration interface the future Render dispatcher
    will invoke

Only after those decisions are locked should the V1E database schema and
implementation be created.
