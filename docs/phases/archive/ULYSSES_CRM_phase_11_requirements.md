# Ulysses CRM -- Phase 11 Requirements

## Followups as Child Engagements

Version: Draft 1\
Author: Dennis Fotopoulos / Ulysses CRM Development\
Purpose: Establish a clear requirements specification for implementing
followups as child engagements within the Engagements system.

------------------------------------------------------------------------

# 1. Overview

Phase 11 introduces **Engagement Children**, enabling followups to exist
as **sub‑engagements** under a parent engagement rather than as a
separate workflow object.

This change aligns the CRM with a **narrative relationship model**,
where conversations naturally lead to followups, forming a chronological
chain of related interactions.

The goal is to eliminate workflow friction caused by managing followups
separately while allowing followups to capture the same level of detail
as full engagements.

Key design principle:

Followups are **not a separate object type**.\
Followups are **engagement records with a parent reference**.

------------------------------------------------------------------------

# 2. Core Design Decision

Followups will be implemented using the existing **engagements table**.

A followup is defined as:

-   an engagement row
-   where `parent_engagement_id` is NOT NULL

A root engagement is defined as:

-   an engagement row
-   where `parent_engagement_id` IS NULL

This preserves the single-table architecture and allows followups to
inherit all engagement functionality.

------------------------------------------------------------------------

# 3. Goals

Phase 11 aims to:

• Remove workflow friction caused by followups being separate objects\
• Allow followups to contain full engagement detail\
• Allow AI summarization on followups\
• Support multiple open followups simultaneously\
• Maintain narrative continuity inside contact engagement history\
• Preserve all existing engagement records without modification

------------------------------------------------------------------------

# 4. Non‑Goals

Phase 11 does not include:

• Removing legacy follow_up fields\
• Complex workflow automation\
• Thread-level AI summarization (parent + children combined)\
• Multi-user permission changes\
• Email ingestion automation

These may be addressed in future phases.

------------------------------------------------------------------------

# 5. Data Model Changes

## Migration 11A -- Parent Engagement Relationship

Add a nullable foreign key column to the engagements table:

    parent_engagement_id INTEGER REFERENCES engagements(id) ON DELETE CASCADE

Behavior:

NULL → root engagement\
NOT NULL → followup engagement

This change is **additive and safe**. Existing records remain unchanged.

------------------------------------------------------------------------

## Migration 11B -- Completion Tracking (Recommended)

Add completion tracking for followups:

    completed_at TIMESTAMPTZ NULL

This enables:

• clean "open vs completed" state\
• dashboard followup tracking\
• reporting and analytics

------------------------------------------------------------------------

## Due Date Support

Followups may optionally include a due date.

If engagements does not currently contain a due date column, add:

    due_at TIMESTAMPTZ NULL

Each followup may therefore have its own due date.

Multiple followups may be open simultaneously.

------------------------------------------------------------------------

# 6. Legacy Followup Fields

Existing fields such as:

• requires_follow_up\
• follow_up_due_at\
• follow_up_completed\
• follow_up_completed_at

will remain unchanged during Phase 11.

They may later be:

• deprecated • repurposed as "next action mirror" fields

Phase 11 does **not modify or delete them**.

------------------------------------------------------------------------

# 7. Workflow Model

## Step 1 --- Log a Root Engagement

User logs a normal engagement for a contact.

Example:

Contact → Engagements → Add Engagement

Result:

    Engagement A
    parent_engagement_id = NULL

------------------------------------------------------------------------

## Step 2 --- Add Followup

User clicks **Add Followup** from the engagement card.

The system creates a new engagement with:

-   same contact_id
-   parent_engagement_id = parent engagement id

Example:

    Engagement B
    parent_engagement_id = A

------------------------------------------------------------------------

## Step 3 --- Followup Completion

A followup may be completed by:

• marking `completed_at` • logging the followup interaction

Completed followups remain visible as historical records.

------------------------------------------------------------------------

# 8. UI Requirements

## Engagement Card

Each root engagement should display a **Followups section**.

Example:

Call with Tracy -- Offer Discussion

Followups (2 open)

• Feb 27 -- Call Brian re SS letter\
• Feb 28 -- Confirm deposit

Actions:

Add Followup\
Edit Engagement\
AI Summarize

------------------------------------------------------------------------

## Followup Display

Child engagements should appear nested beneath their parent.

Behavior:

• collapsed by default\
• expandable section\
• indented visual hierarchy

------------------------------------------------------------------------

## Add Followup UX

Add Followup should:

• open the same engagement creation UI\
• automatically populate parent_engagement_id\
• reuse existing engagement fields

This prevents the need for a separate followup interface.

------------------------------------------------------------------------

# 9. Dashboard Behavior

A dashboard view may display **Open Followups**.

Open followups are defined as:

    parent_engagement_id IS NOT NULL
    AND completed_at IS NULL

Followups should be sortable by due date if present.

------------------------------------------------------------------------

# 10. AI Summary Integration

Because followups are stored in the engagements table, they
automatically support:

• AI summarization\
• engagement search\
• embeddings and future semantic search

No special logic is required.

Future enhancement:

Thread-level summarization combining parent + children.

------------------------------------------------------------------------

# 11. Backfill Strategy (Optional)

Because the system currently supports only one followup slot per
engagement, a one‑time migration may create child engagements from
existing followup fields.

Rules:

• Only create one child per legacy followup\
• Do not modify original data\
• Migration must be idempotent

This step is optional because only one primary user exists.

------------------------------------------------------------------------

# 12. Acceptance Criteria

Phase 11 is considered complete when:

1.  A followup can be created as a child engagement.
2.  Child engagements appear nested under their parent.
3.  Multiple open followups can exist simultaneously.
4.  Followups can include due dates.
5.  Followups can be AI summarized.
6.  Followups can be marked completed.
7.  Existing engagement records remain unchanged.

------------------------------------------------------------------------

# 13. Future Opportunities

Possible enhancements following Phase 11:

• Thread summarization (parent + children AI summary) • Automatic
followup creation from email replies • Followup reminders /
notifications • Visual engagement thread timeline • Conversation chain
visualization

------------------------------------------------------------------------

# 14. Summary

Phase 11 restructures followups into **engagement children**, allowing
Ulysses CRM to maintain a narrative workflow while eliminating the
friction of managing followups as separate objects.

This design:

• simplifies workflow\
• preserves historical engagement data\
• enables richer followup records\
• integrates seamlessly with AI summarization features
