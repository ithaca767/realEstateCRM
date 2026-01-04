# Ulysses CRM – Phase 5 Design and Scope Document

**Phase:** 5  
**Target Release:** v0.11.0  
**Status:** Draft for implementation planning  
**Environment:** Local-first development. Production remains frozen until explicit parity plan and migration approval.

---

## 1. Purpose

Phase 5 introduces **Tasks** as a first-class workflow feature.

- **Engagements** remain the historical record of communication and activity.
- **Tasks** become the actionable work queue that results from engagements, outreach, transactions, and coordination with professionals.

This phase also introduces a **drive-agnostic document linking** model that allows tasks (and optionally engagements) to reference documents via share URLs without Ulysses storing files.

---

## 2. Goals

### 2.1 Core Goals
1. Provide a reliable place to capture and manage actionable work.
2. Support real agent workflow:
   - Engagement occurs
   - Engagement produces one or more tasks
   - Tasks may involve clients, professionals, or counterpart agents
3. Tasks visible in:
   - Global Tasks dashboard
   - Per-contact Tasks view
4. Support document references using share links that work across desktop and mobile.

### 2.2 Non-Goals for v0.11.0
- File uploads or storage within Ulysses
- OAuth or cloud provider integrations
- Complex automation engines
- Multi-user task assignment beyond ownership
- Major transaction feature expansion

---

## 3. Mental Model

- **Engagements:** What happened
- **Tasks:** What must happen next
- **Documents:** Referenced externally via links

---

## 4. User Stories

### Tasks from Engagements
Create tasks directly from calls, texts, meetings, or emails.

### Tasks for Outreach
Create tasks without a prior engagement (prep, follow-ups, research).

### Tasks Involving Professionals
Track coordination steps with attorneys, lenders, inspectors, and other vendors.

### Document Links
Attach Drive, iCloud, Dropbox, OneDrive, or other share links to tasks.

---

## 5. Data Model

### 5.1 Tasks Table

Fields:
- id
- user_id
- contact_id (nullable)
- transaction_id (nullable)
- engagement_id (nullable)
- professional_id (nullable)
- title
- description
- task_type
- status (open, completed, snoozed, canceled)
- priority
- due_at
- completed_at
- created_at
- updated_at

Indexes:
- (user_id, status, due_at)
- (user_id, contact_id)
- (user_id, transaction_id)

---

### 5.2 Document Links Table

Fields:
- id
- user_id
- title
- url
- provider (google_drive, icloud, dropbox, onedrive, other)
- notes
- created_at

---

### 5.3 Association Tables

- task_document_links
- engagement_document_links (optional for v0.11.0)

---

## 6. Provider Detection

Automatic detection based on URL domain with user override option.

---

## 7. UI and UX

### Global Tasks Dashboard
Sections:
- Overdue
- Due Today
- Upcoming
- No Due Date
- Completed

### Contact Page Tasks Tab
Shows open and completed tasks linked to the contact.

### Engagement Integration
Create tasks directly from engagements.

### Task Detail View
Shows linked entities and document links.

---

## 8. Migration Strategy

- Keep existing engagement follow-up fields initially.
- Introduce Tasks as primary actionable workflow.
- Migrate follow-ups to tasks later if desired.

---

## 9. Routes

- /tasks
- /tasks/new
- /tasks/<id>
- /tasks/<id>/edit
- /tasks/<id>/complete

---

## 10. Permissions

- Scoped by user_id
- Ownership-based access

---

## 11. Guardrails

- No production schema changes without migration docs
- Maintain schema parity
- Phase discipline enforced

---

## 12. Release Plan

### v0.11.0
- Tasks feature end-to-end
- Document links via URLs
- Engagement integration

### Future Releases
- File uploads
- Provider integrations
- Automation rules

---

## 13. Acceptance Criteria

- Tasks can be created, viewed, completed, and snoozed
- Tasks visible globally and per contact
- Document links open on desktop and mobile
- No regression in Engagements or Transactions

---


## 6. Transaction Context (NEW – Phase 5)

### Purpose
Transaction Context provides a high-signal, deal-specific space to capture situational awareness that does not belong in engagements, tasks, or contact-level notes.

This answers the question:
**“What is really going on with this deal right now?”**

Examples:
- Seller expectations or emotional factors
- Buyer decision dynamics or financing risk
- Attorney or counterpart agent behavior
- Appraisal, inspection, or timing concerns

### Scope (v0.11.0)
- One multiline **Transaction Context** textarea on the Transaction edit page
- Stored directly on the transaction record
- Manually edited and saved with the main transaction form
- Visible above deadlines/milestones
- Read/write by owner user only

### Schema Changes (Additive, Production-Safe)
Add to `transactions` table:
- `context_notes TEXT NULL`
- `context_updated_at TIMESTAMP NULL`

No backfill required. No existing columns modified.

### UI Placement
- Appears after core transaction fields (status, pricing, dates)
- Appears before deadlines/milestones
- Includes subtle “Last updated” timestamp

### Explicitly Out of Scope (Deferred)
- Version history
- Comments or threading
- AI summarization
- Auto-task generation
- Sharing or permissions beyond owner user

Transaction Context is intentionally lightweight in Phase 5 and designed to complement Tasks and Engagements without overlapping responsibilities.
