# Ulysses CRM  
## Phase 11 – Follow-Ups as Engagement Children  
### Updated Requirements (Post-Chat Revision)

**Version:** Phase 11A Working Requirements, Rev 2  
**Status:** Active Development  
**Scope:** Engagement follow-ups converted to child engagements, with ongoing UI refinement and workflow hardening

---

## 1. Purpose

Phase 11 introduces a structural improvement to how follow-ups are handled in Ulysses CRM.

Instead of storing follow-ups as simple attributes on a parent engagement record, follow-ups become **child engagements** linked to a parent engagement.

This improves:

- historical accuracy
- engagement chain tracking
- reporting
- AI summarization context
- dashboard follow-up tracking
- long-term extensibility for engagement-thread workflows

This phase introduces the concept of:

**Engagement Threads**

Where a primary engagement can generate one or more follow-ups as child engagements.

---

## 2. Core Data Model

Engagements now support hierarchical relationships.

### `engagements` table fields

| Field | Purpose |
|---|---|
| `id` | primary key |
| `contact_id` | associated contact |
| `user_id` | tenant isolation |
| `parent_engagement_id` | links follow-up to parent engagement |
| `engagement_type` | call, text, email, meeting, etc. |
| `occurred_at` | engagement timestamp |
| `requires_follow_up` | flag indicating follow-up requirement |
| `follow_up_due_at` | follow-up due datetime |
| `follow_up_completed` | completion flag |
| `follow_up_completed_at` | datetime completed, when applicable |

---

## 3. Parent vs Child Engagement Logic

### Parent Engagement

A standard engagement created by the user.

Characteristics:

- `parent_engagement_id = NULL`
- may optionally generate one or more follow-up engagements
- serves as the root record for an engagement thread

### Child Engagement (Follow-Up)

A follow-up engagement generated from a parent engagement.

Characteristics:

- `parent_engagement_id = parent engagement id`
- behaves like a normal engagement record for content purposes
- is visually grouped beneath its parent
- may be completed independently
- remains part of the historical record even after completion

---

## 4. Follow-Up Creation Workflow

### User creates engagement

User may populate:

- engagement type
- date/time
- outcome
- notes
- transcript
- summary

User may also select:

- **Follow-up required**

and optionally set:

- follow-up due date
- follow-up due time

### System behavior

When saved:

1. Parent engagement is stored.
2. If follow-up is required, a child engagement is created.

Child engagement inherits:

- `contact_id`
- `user_id`
- `engagement_type`

Child engagement receives:

- `parent_engagement_id = parent id`
- `requires_follow_up = true`
- `follow_up_due_at = due date/time`
- `follow_up_completed = false`

### Workflow note clarified in this chat

A common intended workflow is:

1. Create an engagement.
2. Paste transcript or voice transcript text.
3. Use AI Assist to summarize.
4. Copy the one-sentence summary into **Outcome**.
5. Copy suggested follow-up items into **Notes**.
6. Set **Follow-up required** and due date/time if applicable.
7. Save engagement.

This workflow should remain supported and visually intuitive.

---

## 5. Follow-Up Completion

When a follow-up is completed:

- `follow_up_completed = true`
- `follow_up_completed_at` should be set where appropriate

The follow-up remains part of the engagement history.

Completion does **not** delete the record.

---

## 6. Engagement Table UI Behavior

Engagements are displayed in a table on the Contact page.

### Current design direction

The engagement log is being refactored toward a more readable multi-row display pattern.

### Parent Engagement Display

Parent engagement row should display:

- when
- type
- follow-up control / count
- row actions

A second detail row should display:

- outcome preview
- expandable text when needed

### Expandable Follow-Up Section

Each parent engagement row can expand to show its children.

Display pattern:

```text
Parent Engagement
  Outcome preview

  Follow-ups for this engagement
    Follow-up 1
      Outcome preview
    Follow-up 2
      Outcome preview
```

Follow-ups appear directly beneath the parent engagement row.

### Important refinement from this chat

The original single-row table became too crowded.

The preferred direction now is:

- metadata/action row
- detail row beneath it spanning the table
- expandable child follow-up section beneath that

This structure is not yet fully polished, but it is the current target.

---

## 7. Follow-Up Badges and Buttons

### Parent Engagement

Parent engagement should display a control showing active child follow-ups.

Previous / interim forms included:

- `Follow-ups`
- `Follow-ups 1 / 3`

### Updated target from this chat

The preferred parent-row control is:

**Active Follow-ups**

Requirements:

- style the control light yellow
- visually match the dashboard follow-up badge treatment
- count **active** follow-ups only
- avoid emphasizing completed totals in the primary button label

### Child Engagement

Child engagement may display badges such as:

- `Follow-up`
- `Completed`

depending on status.

---

## 8. UI Design Principles

Follow-up UI follows the Ulysses UI Consistency Guidelines.

Key rules:

- use Bootstrap button groups
- small buttons (`btn-group-sm`)
- consistent alignment with dashboard rows
- forms should not live inside button groups
- avoid UI clutter
- hide implementation language where possible
- preserve workflow clarity over technical exposition

### User-facing terminology principles reinforced in this chat

Avoid exposing internal model language such as:

- child engagement
- parent engagement, where avoidable
- implementation-detail phrasing

However, at this point **Parent Engagement** remains acceptable in some screen contexts because no better label has been finalized yet.

### Visual subordination

Follow-ups should appear visually subordinate to parent engagements.

Suggested and partially implemented style directions:

- indentation
- subtle thread/timeline treatment
- soft background shading
- lighter detail rows
- clamped previews instead of large blocks of text

---

## 9. Engagement Editing

Editing an engagement allows modification of:

- `requires_follow_up`
- `follow_up_due_at`
- `follow_up_completed`
- engagement content fields such as outcome, notes, transcript, and summary

### Important Phase 11 refinement

Editing is now explicitly split into two user experiences:

### Parent engagement edit page

Should focus on:

- engagement details
- follow-up requirement / due date
- engagement content
- child follow-up visibility

Parent pages should **not** show controls that imply the parent itself is a follow-up completion item.

### Child follow-up edit page

Should present a dedicated follow-up experience.

Current intended structure:

- page title: **Engagement Follow-up**
- subhead: outcome, or fallback to engagement date
- parent engagement information
- follow-up details
- follow-up content

Desired header controls on child page:

- Mark As Complete
- Download `.ics`
- Back

---

## 10. Parent / Child Page UI Requirements

### Child follow-up page

The child edit page should include:

#### Header
- title: **Engagement Follow-up**
- subhead using:
  - outcome, if present
  - otherwise “Engagement dated …”

#### Card 1
**Parent Engagement Information**

Should contain:

- link to parent engagement
- excerpt from parent content
- due date if present

Excerpt priority established in this chat:

1. `summary_clean`
2. `notes`
3. `outcome`

#### Card 2
**Follow-up Details**

Contains:

- type
- occurred at
- outcome

#### Card 3
**Follow-up Content**

Contains:

- notes
- transcript
- summary
- AI Assist tools

#### Footer
- Cancel
- Save changes

### Parent engagement page

Current direction:

- show child follow-ups on the parent page
- child follow-ups must be directly accessible from the parent page
- parent page cards should be consolidated and visually simplified in the next UI cleanup pass

---

## 11. Multiple Follow-Ups Per Parent

This was explicitly confirmed during this chat.

A parent engagement may have **more than one** child follow-up.

This is now a core Phase 11 requirement.

This means the system must support:

- `child_followups = list`
- not only a single `child_fu`

A compatibility layer may temporarily preserve older `fu_*` UI variables where needed, but the underlying model must support multiple child follow-ups.

---

## 12. Dashboard Follow-Up Logic

Follow-ups continue to power the Dashboard Follow-Up widget.

Dashboard logic must include child engagements where:

```sql
requires_follow_up = true
AND follow_up_completed = false
```

Child engagements are included in follow-up lists.

### Styling note from this chat

The dashboard follow-up badge style is now the visual reference for the Contact-page engagement-row follow-up button.

---

## 13. AI Engagement Summaries

Phase 11 preserves compatibility with the existing AI engagement summarization workflow.

Transcript summaries remain attached to the engagement record.

Current supported uses include:

- transcript summarization on engagement creation
- summarization of existing engagements
- CRM narrative summaries
- suggested follow-up items
- insert into notes / summary workflows

Future Phase 12 enhancements may allow:

- AI follow-up extraction
- auto-creation of follow-ups

---

## 14. Multi-Tenant Safety

All queries must include:

```sql
WHERE user_id = current_user.id
```

This applies to:

- engagement retrieval
- parent engagement retrieval
- child follow-up retrieval
- follow-up creation
- follow-up editing
- follow-up completion
- dashboard queries

Tenant scoping was reaffirmed repeatedly during this chat.

---

## 15. Migration Files

Phase 11 uses the following migrations:

- `2026_03_02_phase_11A_engagement_children_schema.sql`
- `2026_03_02_phase_11B_backfill_followup_children_shell.sql`

Purpose:

- introduce `parent_engagement_id` relationship
- allow future backfill of historical follow-ups

Backfill is optional because the system is still early stage.

---

## 16. Known Issues Addressed Across Phase 11 Work

The following issues were identified and worked through during this chat.

### Issue: single-child assumptions breaking multi-follow-up behavior

Cause:

Earlier code assumed one child follow-up per parent.

Fix direction:

- move toward `child_followups` list handling
- preserve temporary compatibility variables such as:
  - `child_fu`
  - `fu_requires`
  - `fu_child_id`
  - `fu_due`

### Issue: parent content card showed “No parent details available yet” even when content existed

Cause:

Parent excerpt logic did not prioritize available fields properly.

Fix:

Parent text fallback order updated to use:

- `summary_clean`
- `notes`
- `outcome`

### Issue: routing / rendering instability during transition from one child to many

Cause:

Route and template logic were partially updated while older `fu_*` expectations remained.

Fix direction:

Preserve compatibility layer until the phase settles.

### Issue: outcome display became crowded and inconsistent

Cause:

Outcome, notes, and summary were competing inside narrow table cells.

Fix direction:

- clamp outcome text
- use “See more”
- move toward multi-row engagement display

### Issue: engagement table striping looked wrong

Cause:

Bootstrap `table-striped` alternates by `<tr>`, but each engagement now renders as multiple rows.

Fix direction:

- remove striping from engagement log table
- use dedicated table styling such as:
  - `engagement-log-table`
  - `engagement-detail-row`
  - `eng-followups-nested`

### Issue: duplicate global `toggleOutcome()` helper

Cause:

Function was accidentally defined twice in `base.html`.

Fix:

Keep one global copy only.

---

## 17. Current UI State at End of This Chat

The engagement/follow-up UI is mid-refinement.

### Confirmed direction
- follow-ups are child engagements
- parent pages can surface child follow-ups
- child pages show parent context
- engagement log is being reshaped to support two-row records
- outcome text clamp behavior exists
- UI cleanup remains in progress

### Not fully settled yet
- final engagement log shading
- final detail row visual treatment
- final nested follow-up styling
- final button label/treatment for parent-row follow-up control
- card consolidation on engagement pages

---

## 18. Remaining Work (Phase 11A / current next-step set)

Still to implement or finish:

- active follow-up button styling on parent engagement rows
- change button label to **Active Follow-ups**
- count active follow-ups only
- complete engagement log two-row layout cleanup
- remove stripe/shading conflicts in engagement log
- consolidate cards on view/edit engagement pages
- continue follow-up UI refinement for nested child records
- optionally align Follow-ups tab preview treatment with new outcome-clamp pattern

---

## 19. Immediate Next-Chat UI Cleanup Goals

Explicitly identified for the next chat:

1. **Shade the followups count button in the engagement row light yellow**, matching the dashboard follow-up badge style
2. Change the button text to **“Active Follow-ups”**
3. Count only the active ones
4. **Consolidate the cards** in the view engagement and edit engagement pages
5. Continue the remaining Phase 11 feature enhancements

---

## 20. Future Enhancements

Possible Phase 11B / Phase 12 improvements:

- richer engagement thread visualization
- follow-up chaining (follow-up of follow-up)
- AI suggested follow-up extraction
- dashboard follow-up prioritization
- automated follow-up reminders
- fuller timeline-style activity presentation

---

## 21. Phase Goal

The objective of Phase 11 is to establish **engagement threads** as the core CRM interaction model.

This enables:

- richer relationship tracking
- more powerful AI summarization
- structured follow-up workflows
- more natural parent/child engagement history

while maintaining compatibility with existing engagement records and preserving tenant safety.
