# Ulysses CRM -- Attention Engine V1

**Baseline:** Ulysses CRM v1.10.3\
**Status:** Architecture locked; ready for V1A implementation\
**Phase type:** Architecture / incremental feature development\
**Last reviewed:** August 21, 2026

## Purpose

The Ulysses Attention Engine is intended to proactively surface CRM
items that require the user's attention while preserving Ulysses'
existing source-of-truth, user-intent, and AI guardrail principles.

The Attention Engine is not a second follow-up system. It is an
evaluation layer above existing operational records.

Long-term architecture:

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
       Push Subscriptions
              ↓
      Render Dispatcher
              ↓
          Web Push
```

The implementation will be incremental. V1A begins only with existing
overdue Follow-ups.

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
    "snippet": "Follow-up context"
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

# Planned Incremental Build

## V1A --- Attention Evaluator

-   Add `attention.py`
-   Evaluate overdue Follow-ups
-   No database writes
-   Test directly against LOCAL data
-   Verify returned items against known Follow-ups

## V1B --- Ulysses Attention UI

-   Surface Attention results inside Ulysses
-   Reuse the V1A evaluator
-   Follow established Ulysses dashboard/UI standards
-   No push notifications yet

## V1C --- Permission-Based Push Subscriptions

Introduce explicit per-device/browser notification permission.

Likely new table:

``` text
push_subscriptions
```

Conceptual fields:

-   `id`
-   `user_id`
-   `endpoint`
-   `p256dh`
-   `auth`
-   `created_at`
-   `updated_at`
-   `last_used_at`
-   `is_active`

Push permission belongs to a user + browser/device subscription, not
simply to the user record.

One user may have multiple authorized devices.

The exact schema will be designed only when V1C begins.

## V1D --- Test Web Push

-   Add service worker
-   Register browser/device subscription
-   Send a controlled test push
-   Verify permission behavior and device delivery
-   No automated Attention dispatch yet

## V1E --- Render Dispatcher

Add scheduled production evaluation outside the Flask/Gunicorn web
process.

Conceptual flow:

``` text
Render scheduled process
        ↓
Attention Engine
        ↓
Notification policy
        ↓
Authorized push subscriptions
        ↓
Web Push
```

The web process must not run its own internal timer.

## V1F --- Notification Deduplication / Delivery State

Prevent repeated pushes for the same unchanged Attention condition.

Do not add a generic `notified` flag to `engagements`.

Notification delivery state belongs to the notification layer, not the
Follow-up record.

A future delivery/history structure may contain concepts such as:

-   user
-   subscription
-   attention type
-   source type
-   source ID
-   sent time
-   delivery status

The exact schema is intentionally deferred until the push pipeline is
proven.

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

Other older fields use `TIMESTAMP WITHOUT TIME ZONE`.

Attention Engine development must not expand into an unrelated timestamp
migration. Existing historical timestamp cleanup is outside this phase.

------------------------------------------------------------------------

# Locked V1 Decisions

1.  The Attention Engine sits above existing operational records.
2.  Existing Follow-ups remain canonical child engagements.
3.  V1A evaluates overdue Follow-ups only.
4.  Attention is calculated and is not persisted in V1A.
5.  V1A requires no database migration.
6.  `attention.py` owns the Attention rule.
7.  Consumers must reuse the same evaluator.
8.  Tasks and transaction deadlines are deferred.
9.  Push permission is per browser/device subscription.
10. Push infrastructure is deferred until V1C.
11. Render scheduling is deferred until V1E.
12. Notification delivery/deduplication state is separate from
    operational CRM records.
13. The old `interactions` reminder system will not be reused.
14. Legacy reminder cleanup will occur separately after the replacement
    path is working.
15. The Attention Engine V1 contains no AI and makes no autonomous CRM
    changes.

------------------------------------------------------------------------

# Immediate Next Step

Implement V1A by creating:

``` text
attention.py
```

Then test the evaluator against the LOCAL database and verify that its
returned Attention candidates correspond exactly to known overdue child
Follow-ups before wiring the engine into any UI.
