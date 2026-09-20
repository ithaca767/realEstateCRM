# Ulysses Activity Engine V1

Status: Design approved for initial implementation planning  
Date: September 2026

## Purpose

The Ulysses Activity Engine will provide one authoritative way to assemble and interpret actionable work across the CRM.

It will power multiple Ulysses interfaces without creating separate and potentially conflicting versions of the user's schedule or work queue.

Primary consumers:

- Ulysses Dashboard
- Calendar integrations
- Ulysses Assist, including future Ulysses/Penelope conversational interfaces

Core architecture:

CRM source records
    ↓
Activity Engine
    ↓
Dashboard | Calendar Integration | Ulysses Assist

## Core Principle

Source records remain authoritative.

The Activity Engine normalizes and presents those records. It does not duplicate them into a second activity database.

V1 will therefore be implemented as a service/query layer rather than a new `activities` table.

Actions taken from an Activity must ultimately operate on the authoritative source record.

Examples:

- Completing a Follow-up completes the underlying engagement Follow-up.
- Completing a Task updates the underlying Task.
- Completing a Transaction Deadline updates the underlying deadline.

## V1 Authoritative Sources

### 1. Engagement Follow-ups

Authoritative source:

`engagements`

An actionable Follow-up is currently represented by a child engagement with:

- `parent_engagement_id IS NOT NULL`
- `requires_follow_up = TRUE`
- `follow_up_completed = FALSE`
- `follow_up_due_at IS NOT NULL`

Follow-ups support:

- exact due timestamp
- contact relationship
- parent engagement context
- completion state
- overdue detection through the Attention Engine

The existing Dashboard explicitly treats engagement Follow-ups as the Follow-up source of truth.

Legacy `contacts.next_follow_up` and `contacts.next_follow_up_time` fields are not the Activity Engine Follow-up source.

### 2. Tasks

Authoritative source:

`tasks`

Active Tasks include appropriate records in the existing Task lifecycle:

- open
- expired snoozed tasks that behave as open

Completed and canceled Tasks are not active Activities.

Future Activity normalization should preserve useful Task relationships including:

- contact
- transaction
- engagement
- professional
- priority
- due date
- exact due timestamp
- snooze state

### 3. Transaction Deadlines

Authoritative source:

`transaction_deadlines`

An actionable Transaction Deadline is:

- not complete (`is_done = FALSE`)
- assigned a `due_date`

Relevant fields include:

- transaction
- name
- due date
- completion state
- notes

## Deferred Activity Sources

### Buyer and Seller Checklist Items

Checklist records remain workflow records in V1.

They will not automatically become Activities merely because they have a `due_date`.

Reason:

A workflow due date does not necessarily mean that an item should appear on the user's primary Activity List or calendar.

Seller checklist defaults currently generate many dated workflow records. Automatically promoting every dated checklist item would create excessive Activity noise.

Future versions may support:

- explicit promotion of a checklist item to Activity
- checklist template rules controlling Activity behavior
- selected checklist categories becoming Activities automatically

### Transaction Date Fields

Transactions currently contain structured dates such as:

- attorney review end date
- inspection deadline
- financing contingency date
- appraisal deadline
- mortgage commitment date
- expected closing date
- actual closing date

These may overlap with `transaction_deadlines`.

They will not be independently ingested into Activity Engine V1 until the relationship between transaction date fields and Transaction Deadline records is formally defined.

The Activity Engine must not create duplicate Activities for the same real-world deadline.

## Activity Classification

Ulysses distinguishes among three concepts.

### Actionable Activity

Something Ulysses should actively bring to the user's attention.

Examples:

- Follow-up
- Task
- Transaction Deadline

### Workflow Tracking

Something useful for managing a process but not necessarily appropriate for the primary Activity List.

Examples:

- buyer checklist item
- seller checklist item

Workflow records may later be promoted to actionable Activities according to explicit rules.

### Calendar-Worthy Activity

An Activity appropriate for external calendar presentation.

Not every Activity is necessarily calendar-worthy.

Examples likely to be calendar-worthy:

- timed Follow-up
- appointment
- showing
- closing
- important transaction deadline
- explicitly calendar-enabled Task

Examples that may remain Activity-only:

- low-level workflow checklist items
- administrative reminders that the user does not want placed on an external calendar

Calendar behavior must therefore be explicit rather than inferred solely from the existence of a due date.

## Normalized Activity Contract

Each Activity Engine result should expose a stable normalized representation while preserving its source identity.

Initial conceptual fields:

- `activity_type`
- `source_type`
- `source_id`
- `title`
- `description`
- `contact_id`
- `contact_name`
- `transaction_id`
- `due_date`
- `due_at`
- `status`
- `priority`
- `is_overdue`
- `is_today`
- `is_upcoming`
- `calendar_eligible`
- `target_url`

Not every source will populate every field.

The Activity Engine must preserve enough source information for Ulysses to route actions back to the authoritative record.

No Activity identifier should be treated as a replacement for the underlying source identifier.

## Time Semantics

Ulysses system timezone rules remain authoritative.

- PostgreSQL `timestamptz` values represent instants.
- Python timestamp handling must use timezone-aware datetimes.
- America/New_York is the application/user display and calendar timezone.
- Browser `datetime-local` values represent New York wall time and must be converted before storage.
- UTC timestamps must be converted to America/New_York before display or date-based grouping.

Activity Engine classification such as Today, Overdue, and Upcoming must use these rules consistently.

Date-only records must remain date semantics rather than being silently converted into arbitrary appointment times.

## Activity Buckets

V1 should support at least:

### Overdue

Incomplete actionable Activities whose due date/time has passed.

### Today

Incomplete actionable Activities due today in America/New_York and not already classified as overdue.

For timestamped Activities, a time earlier today may be Overdue.

### Upcoming

Incomplete actionable Activities due after Today within a defined query horizon.

The Activity Engine should support query ranges rather than permanently hard-coding one Dashboard horizon.

This allows future consumers to ask:

- What do I have today?
- What do I have tomorrow?
- What is coming up this week?
- What deadlines do I have over the next seven days?

## Dashboard Integration

The existing Dashboard already contains an early form of Activity aggregation.

It currently:

- retrieves engagement Follow-ups
- retrieves Tasks
- determines overdue/today state
- normalizes some presentation fields
- combines source types
- deduplicates records
- sorts them by due time

V1 should extract/generalize this behavior into the Activity Engine rather than create a parallel implementation.

The Dashboard should become a consumer of the Activity Engine.

## Attention Engine Relationship

The Attention Engine currently provides deterministic overdue Follow-up detection.

Activity Engine and Attention Engine responsibilities must remain explicit.

The Activity Engine should not introduce competing definitions of overdue Follow-ups.

As implementation proceeds, shared deterministic rules should be centralized or reused so Dashboard, Attention Engine, Calendar and Assist cannot disagree about the state of the same source record.

## Calendar Architecture

Calendar integration is a first-class Activity Engine consumer.

Architecture:

Activity Engine
    ↓
Calendar Integration Layer
    ↓
ICS / Apple Calendar
Google Calendar
Microsoft Outlook / Microsoft 365

### Universal ICS Support

Ulysses should retain standards-based ICS support.

The current `/followups.ics` implementation is legacy because it reads:

- `contacts.next_follow_up`
- `contacts.next_follow_up_time`

rather than the modern engagement Follow-up source.

The future feed should be generated from Activity Engine results.

ICS provides a universal baseline suitable for calendar clients including Apple Calendar.

### Google Calendar

A future direct Google Calendar adapter should be evaluated for authenticated synchronization beyond passive ICS subscription.

Potential capabilities include:

- create Ulysses calendar events
- update existing Ulysses-created events
- remove or complete reflected events appropriately
- maintain stable external event identity
- avoid duplicate events
- optionally read selected external calendar information into Ulysses

### Microsoft Outlook / Microsoft 365

A future Microsoft calendar adapter should provide equivalent integration through Microsoft's supported calendar APIs.

The Google and Microsoft adapters should consume the same Activity Engine contract.

Provider-specific logic must not determine Ulysses Activity semantics.

### Calendar Synchronization Principles

Ulysses remains authoritative for Ulysses-generated Activities.

Calendar synchronization must use stable source identity so updates do not create duplicates.

The integration should distinguish:

- Ulysses source identity
- external provider
- external calendar
- external event identity
- synchronization state

Any future two-way synchronization must define conflict behavior explicitly before implementation.

## Ulysses Assist Integration

Ulysses Assist will consume the Activity Engine rather than independently querying and interpreting every underlying table.

Examples:

"What does my activity list look like today?"

"What do I have tomorrow?"

"What's coming up this week?"

"Anything important before Friday?"

"What deadlines do I have over the next seven days?"

The Activity Engine returns deterministic CRM data.

Assist may summarize and conversationally present that data, but it must not invent Activities or independently redefine Activity status.

Future action example:

"Add a follow-up with Tyler for Tuesday at 10."

Expected architecture:

1. Assist interprets the request.
2. Ulysses resolves the exact contact using verified CRM identity and relationships.
3. Ulysses proposes the Follow-up.
4. User approves when required.
5. Ulysses writes the authoritative Follow-up record.
6. Activity Engine reflects the new Follow-up.
7. Calendar integration reflects it according to calendar rules.

## Identity and Data Isolation

Activity Engine results must preserve exact source and relationship identity.

AI must never determine CRM identity merely from similar names or conversational probability.

Ulysses resolves and validates record identity.

This is especially important when Activities reference:

- contacts
- associated contacts
- transactions
- properties
- engagements

Core Assist safety principle:

AI interprets.
Ulysses resolves and validates.
User approves consequential writes.
Database commits.

## Initial Implementation Direction

V1 implementation should proceed incrementally.

1. Create Activity Engine read/service layer.
2. Normalize engagement Follow-ups.
3. Normalize Tasks.
4. Normalize Transaction Deadlines.
5. Establish deterministic Overdue / Today / Upcoming classification.
6. Add automated tests for source isolation, classification, timezone handling and deduplication.
7. Replace Dashboard's embedded Follow-up/Task aggregation with Activity Engine results without changing intended Dashboard behavior.
8. Build Activity-based ICS feed.
9. Evaluate and design direct Google Calendar integration.
10. Evaluate and design direct Microsoft Outlook / Microsoft 365 integration.
11. Expose Activity Engine as a structured Ulysses Assist capability.

Checklist Activities and transaction-derived date fields remain deferred until their semantics are explicitly defined.

## Non-Goals for V1

V1 will not:

- create a generalized `activities` database table
- duplicate authoritative source records
- automatically place every dated CRM record on the calendar
- automatically ingest all checklist due dates
- use AI to determine Activity status
- use AI to infer record identity
- implement email integration
- implement uncontrolled two-way calendar synchronization
- silently modify CRM records based on external calendar changes

## Long-Term Direction

The Activity Engine should become the authoritative scheduling and actionable-work interface inside Ulysses.

A user should eventually be able to move naturally among:

- Dashboard
- calendar
- typed Assist
- spoken Ulysses/Penelope interaction

without those interfaces disagreeing about what needs attention.

The goal is one underlying Ulysses understanding of the user's work, exposed through multiple interfaces.
