
# Phase 11 – Follow-ups as Engagement Children

## Overview

Phase 11 introduces a structural redesign of how follow-ups are handled in Ulysses CRM.

Historically, follow-ups were stored as attributes on a parent engagement record. This approach limited the system’s ability to represent ongoing conversations, created ambiguity in engagement history, and restricted future AI analysis.

Phase 11 converts follow-ups into **child engagement records**, allowing engagements to form a simple parent–child relationship chain.

This change transforms follow-ups from a field into a **first-class engagement object**.

The result is a more accurate engagement history and a structure that supports richer workflows, analytics, and AI summarization.

---

# Core Concept

An engagement may optionally generate a follow-up.

Instead of modifying the original engagement record, the system now creates a **child engagement** representing the follow-up.

Parent Engagement  
↓  
Child Engagement (Follow-up)

Child engagements behave like normal engagements but are linked to their parent.

This enables engagement threads while preserving the chronological history of interactions.

---

# Engagement Relationship Model

Engagements now support a hierarchical structure using the field:

`parent_engagement_id`

Behavior rules:

| Scenario | parent_engagement_id |
|--------|--------|
| Normal engagement | NULL |
| Follow-up engagement | parent engagement ID |

A follow-up is therefore defined as:

`parent_engagement_id IS NOT NULL`

This design avoids creating a separate follow-up table and keeps all engagement activity unified in a single model.

---

# Follow-up Lifecycle

The lifecycle of a follow-up engagement includes the following states:

### 1. Creation

A follow-up is created as a child engagement when:

- a user schedules a follow-up from a parent engagement
- a follow-up is added from the engagement log

Key fields set during creation:

- `parent_engagement_id`
- `requires_follow_up = TRUE`
- `follow_up_due_at`

---

### 2. Active Follow-up

An active follow-up meets the following conditions:

- `requires_follow_up = TRUE`
- `follow_up_completed = FALSE`
- `follow_up_due_at IS NOT NULL`

Active follow-ups appear in:

- Dashboard Follow-ups
- Today’s Snapshot
- Upcoming Follow-up lists

---

### 3. Completion

A follow-up becomes completed when:

`follow_up_completed = TRUE`

The system records:

`follow_up_completed_at`

Completed follow-ups remain part of the engagement history.

---

### 4. Reopen Behavior

Editing and saving a completed follow-up reopens it automatically unless the user explicitly selects **Save and Complete**.

This ensures that engagement corrections do not permanently lock a follow-up.

---

# Dashboard Integration

The dashboard treats follow-ups as operational workflow items.

Follow-ups are categorized into:

- **Overdue**
- **Due Today**
- **Upcoming**

The source of truth for dashboard follow-ups is the **engagements table**, filtered by:

- `parent_engagement_id IS NOT NULL`
- `requires_follow_up = TRUE`
- `follow_up_completed = FALSE`
- `follow_up_due_at IS NOT NULL`

---

# Engagement Context Behavior

To provide meaningful context in dashboard snippets, the system attempts to extract text in the following order:

1. Follow-up outcome
2. Follow-up summary
3. Follow-up notes
4. Parent engagement outcome
5. Parent engagement summary
6. Parent engagement notes
7. Most recent non-follow-up engagement

This ensures that even placeholder follow-ups display useful context in the dashboard.

---

# UI Design Decisions

Several UI decisions were made in Phase 11 to simplify the engagement workflow:

- Follow-ups are edited on the **Engagement Follow-up Details page**
- Completed follow-ups display a **green completion banner**
- Editing a completed follow-up reopens it automatically
- The legacy **Follow-ups tab** was removed from the UI to reduce redundancy

The tab code remains commented in the codebase for possible future use.

---

# AI Assist Compatibility

Because follow-ups are now engagement records, they can use the same AI summarization tools as standard engagements.

This ensures that:

- transcripts
- engagement summaries
- follow-up notes

can all be processed consistently by AI tools.

---

# Architectural Benefits

The Phase 11 design provides several long-term advantages:

- unified engagement model
- accurate interaction history
- support for engagement threads
- improved AI context for summarization
- simplified database structure
- easier future reporting and analytics

---

# Future Enhancements

Several enhancements were identified but intentionally deferred:

1. Dashboard snippets with expandable **“See more”** behavior for summaries and outcomes.
2. AI search results that open the **exact follow-up engagement** instead of only the parent engagement.
3. Possible future UI reintroduction of a dedicated follow-ups view if operational needs require it.

These enhancements are considered **post–Phase 11 improvements** rather than core architectural requirements.
