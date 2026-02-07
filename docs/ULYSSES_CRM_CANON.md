
# Ulysses CRM – Project History & Governance

## Purpose of This Document
This document serves as the authoritative historical record and governance reference for the Ulysses CRM project. It preserves design intent, phase discipline, and decision rationale, while providing clear operational guardrails for ongoing development.


## Standing Project Laws
**Effective as of 2026-01-19**

### Law 1: The Database Schema Is the Contract
- The database schema is authoritative.
- Application code must conform to the schema, not guess or adapt to it dynamically.
- Runtime schema detection in production paths is prohibited.
- Schema changes must be deliberate, verified, and inspected directly.

### Law 2: Production Data Is Sacred
- No casual production database changes.
- LOCAL vs PROD environments must be explicitly identified.
- All production-affecting actions must be verified and confirmed.

### Law 3: No Silent Refactors
- Refactors must be explicit, scoped, and inspectable.
- Any behavioral or structural change must be stated before implementation.

### Law 4: Templates Are Contracts
- Template variables are an API.
- Routes must conform unless templates are refactored simultaneously.
- Simplification without a full audit is prohibited.

### Law 5: Transactions Are the Source of Truth
- Transactions own lifecycle, status, financials, and timelines.
- Dashboards and profiles mirror; they do not edit.
- Status lifecycles are MLS-realistic and locked once finalized.

### Law 6: Preserve History Over Deletion
- Prefer archiving and state transitions over destructive deletes.

### Law 7: Version Numbers Must Be Truthful
- Every production deploy increments the version.
- The displayed version must reflect what is live.

### Law 8: Phase Boundaries Are Real
- Each phase has defined scope and non-goals.
- Deferred features remain deferred unless re-approved.

### Law 9: Design Intent Is Protected
- Design/spec chats are canonical.
- Implementation must respect or explicitly propose changes.

### Law 10: Local-First, Then Production
- Develop and validate locally before production integration.

### Law 11: UI Consistency Is Intentional, Not Incremental
- UI consistency is addressed in named, deliberate passes.

### Law 12: Repo State Is the Source of Truth
- Repo output overrides memory or chat history.
- Destructive actions require checkpoints.

### Law 13: Page Structure, Wrappers, and Data Presentation Are Contractual
- Page wrappers, headers, spacing, counters, tables, and lists must follow established patterns.
- New patterns require explicit justification.

## AI Feature Governance
**Effective as of 2026-02-07**

AI functionality within Ulysses CRM is strictly governed to preserve user trust, data ownership, cost control, and system predictability.

### AI Usage Principles
- AI features are **explicitly user-initiated only**
- No background, automatic, or silent AI processing is permitted
- AI output is never auto-saved; the user must explicitly accept or discard results
- AI is treated as an **assistive tool**, not an authoritative system actor

### User-Level Controls
AI access is controlled at the **user level**, not globally.

Each user record may define:
- ai_enabled (boolean)
- ai_daily_request_limit (integer)
- ai_daily_requests_used (integer)
- ai_monthly_cap_cents (integer, optional)
- ai_monthly_spend_cents (integer)
- ai_last_daily_reset_at (date)
- ai_last_monthly_reset_at (date)

AI requests must be denied if:
- ai_enabled is false
- daily request limit is exceeded
- monthly spend cap is exceeded (when ai_monthly_cap_cents is set)

### Guard Enforcement
All AI routes must enforce:
- Global server flag (AI_FEATURES_AVAILABLE)
- Per-user enablement
- Per-user daily limits
- Per-user monthly cost caps

Failures must return a **clear, non-fatal UI message** and never crash core workflows.

### Opt-In Model
AI features are opt-in and may be introduced as:
- Feature flags
- Paid add-ons
- Limited beta tools

AI availability must be clearly communicated to the user at the time of invocation.

### AI-Assisted Engagement Summaries

Ulysses CRM may offer AI-assisted summarization of engagement transcripts or notes.

Rules:
- Summarization is user-triggered via explicit UI action
- No summaries are auto-generated
- Summaries are returned to the UI but not persisted unless explicitly saved
- When the logged-in user is the speaker, summaries should prefer first-person phrasing where appropriate
- AI summaries must be editable before saving

AI summaries are intended to reduce administrative overhead while preserving agent voice and intent.


## How We Work
**Effective as of 2026-01-19**

1. **Declare Intent Up Front**
   - Phase, target version, session type, and constraints.

2. **Anchor Repo State Early**
   - Use git status, branch, tree listings, and explicit paths.

3. **Respect Design Intent**
   - Follow spec or explicitly propose changes before implementing.

4. **Respect UI Structure**
   - Confirm wrapper, headers, tables, counters align with existing patterns.

5. **Protect Schema and Data**
   - Schema-first, production-safe, no guessing.

6. **Scope Changes Before Making Them**
   - State what will change, what will not, and what is deferred.

7. **Honor Pauses**
   - Pauses stop feature velocity until explicit re-entry.

8. **Produce Canonical Summaries**
   - Capture goals, decisions, additions, deferrals.

9. **Name Deviations**
   - Any rule break must be explicit and documented.

10. **Evolve Deliberately**
   - Amendments must be explicit and recorded.


## Session Start Checklist
**Effective as of 2026-01-19**

Use this checklist at the start of any non-trivial chat.

### 1. Session Declaration
- Phase
- Target version (if any)
- Session type (Design / Implementation / Stabilization / Planning / UI Consistency)
- Constraints (e.g. no schema changes, no new UI patterns)

### 2. Repo State Anchor (If Touching Code)
- git status
- branch name
- relevant file paths or tree -L 3

### 3. Design Intent Check
- Follows existing design/spec, or
- Explicitly proposes a design change

### 4. UI Contract Check (Law 13)
- Wrapper matches established pattern
- Header hierarchy consistent
- Tables/lists follow existing formats
- Counters, badges, pagination consistent
- New patterns must be explicitly justified

### 5. Schema & Data Safety
- Schema is authoritative
- No runtime schema guessing
- LOCAL vs PROD identified
- Production changes verified

### 6. Scope Lock
- What will change
- What will not change
- What is deferred

### 7. Pause Awareness
- Active development, stabilization only, or pause

### 8. End-of-Session Requirement
- Summary produced
- Deferrals noted


## UI Consistency Checklist (Law 13 Companion)
**Effective as of 2026-01-19**

Use this checklist whenever UI work is proposed or implemented.

### Page Structure
- Single, consistent top-level container
- No nested containers that alter global spacing
- base.html owns layout; child templates own content only

### Page Header
- Clear page title (h2)
- Optional muted descriptor line
- Action buttons placed consistently

### Tables & Lists
- Column order matches existing tables of the same type
- Action columns placed consistently (usually right-aligned)
- Empty states handled consistently
- Row click vs action click behavior consistent

### Counters, Badges, Pagination
- Badge styles and placement consistent
- Counters represent the same semantic meaning across pages
- Pagination controls placed consistently and labeled clearly

### Forms & Actions
- Save buttons only on editable views
- Button hierarchy consistent (primary vs secondary)
- Destructive actions clearly distinguished

### Visual Rhythm
- Spacing, margins, and card usage consistent
- No ad-hoc padding or margin overrides without justification

### Divergence Handling
- Any deviation from established patterns must be:
  - Explicitly called out
  - Justified
  - Accepted intentionally


---
author: Dennis Fotopoulos
operator: Dennis Fotopoulos
---

# Ulysses CRM – AI Philosophy

## Purpose

This document defines the governing philosophy for all AI functionality within **Ulysses CRM**. It establishes clear boundaries, design principles, and non‑negotiable rules that ensure AI enhances human work without replacing judgment, intent, or accountability.

This philosophy is considered **canon**. Any future AI feature must comply with the principles below or be explicitly rejected.

---

## Core Principle

> **AI may assist with expression, but never with intent, memory, or action.**

This single rule underpins every AI decision in Ulysses CRM.

* **Expression**: wording, summarization, clarity, structure
* **Intent**: goals, decisions, strategy
* **Memory**: what actually happened, historical record
* **Action**: tasks, follow‑ups, scheduling, commitments

AI is permitted only in the first category.

---

## What AI Is In Ulysses

AI in Ulysses is:

* **Assistive** – it helps the user articulate information
* **On‑demand** – it runs only when explicitly triggered
* **Human‑final** – a person decides what is saved
* **Visible** – outputs are shown before any action
* **Reversible** – nothing is written unless manually pasted and saved

AI exists to reduce friction, not to automate judgment.

---

## What AI Is Not

AI in Ulysses is **not**:

* Autonomous
* Background‑running
* Self‑saving
* Opinionated
* Strategic
* Authoritative

AI does not “decide,” “schedule,” “optimize,” or “correct.”

---

## Explicitly Prohibited Uses

The following uses of AI are disallowed within Ulysses CRM:

### 1. Automatic Database Writes

AI must never:

* Save summaries automatically
* Modify notes in the background
* Rewrite historical records
* Perform silent updates of any kind

All persistence must be the result of a human action.

---

### 2. AI‑Created Tasks or Follow‑Ups

AI may not:

* Create tasks
* Schedule reminders
* Mark follow‑ups as required or completed

At most, AI may **suggest** follow‑up items in a preview context. Creation is always manual.

---

### 3. Reinterpretation of Tone or Intent

AI must not:

* Add emotional framing
* Soften or escalate language
* Infer motivations
* Recast client sentiment

Summarization must remain factual and neutral.

---

### 4. Pricing, Offer, or Strategy Guidance

AI may not:

* Recommend prices or counters
* Judge deal strength
* Assess client seriousness
* Offer strategic advice

Ulysses is a system of record, not a decision engine.

---

### 5. Cross‑Contact or Behavioral Analysis

AI may not:

* Profile clients
* Compare contacts
* Analyze behavior across engagements
* Draw conclusions from historical patterns

AI operates at the **single‑engagement level only** unless explicitly re‑authorized by canon.

---

## Approved AI Use Cases

The following are explicitly allowed:

* Drafting engagement summaries
* Cleaning raw transcripts into readable narrative
* Producing one‑sentence recap lines
* Suggesting possible follow‑up items (non‑binding)

All outputs must be previewed before use.

---

## Time‑Shifted Intelligence

Ulysses supports **time‑shifted AI assistance**:

* Capture first
* Refine later
* Improve records intentionally

AI is available when the user is ready, not when the system decides.

---

## Design Guardrails

Every AI feature must satisfy all of the following:

* Explicit user opt‑in
* Global kill switch
* Per‑user usage limits
* No background execution
* No implicit saves
* Clear attribution (AI vs human)

If any guardrail cannot be met, the feature must not ship.

---

## Rationale

Ulysses CRM is trusted with:

* Sensitive conversations
* Incomplete thoughts
* High‑stress negotiations
* Long‑term historical memory

AI that crosses boundaries erodes trust, even if technically correct.

A restrained, predictable AI makes the system stronger.

---

## Canon Status

This document is **binding**.

Any future AI expansion must:

* Reference this philosophy
* Justify alignment
* Explicitly call out any deviation

Absent that justification, the default answer is **no**.

---

---

# Chronological Project History  
**The sections below are a historical record.  
They are descriptive, not prescriptive, and should not be retroactively modified.**

---


## CRM Project -- Development Summary (Historical / Evolution Log)

### Date -- December 1, 2025

### Primary Goal of This Session

The goal of this work session was to **mature the Buyer and Seller
workflows**, improve **commitment clarity**, streamline **contact
engagement flow**, and begin **planning the next phase of reporting**,
while deliberately avoiding feature sprawl and reinforcing long-term
design discipline.

## Key Decisions & Design Principles Reinforced

### 1. Contacts vs. Roles (Core Architecture Principle)

A major principle was reaffirmed:

-   **Contacts are people**

-   **Buyer and Seller sheets are roles**

-   A single contact may hold **multiple concurrent roles** (buyer,
    seller, both)

All UI and data decisions reinforced this separation.

### 2. "Commitment" Is a First-Class Concept

The system now clearly distinguishes between:

-   Leads / uncommitted contacts

-   **Committed buyers and sellers**

This commitment state is visible immediately in the UI and drives
workflow clarity.

### 3. Workflow First, Admin Second

Repeated emphasis was placed on optimizing for **how an agent actually
works**, not for data entry completeness:

-   Reduce friction

-   Minimize unnecessary duplication

-   Always land the user where the next action naturally occurs

## Features Added in This Session

### 1. Dynamic Buyer / Seller Commit Buttons

Buttons now change behavior and appearance based on commitment state:

-   "Commit as Buyer" → **"Committed Buyer Sheet"**

-   "Commit as Seller" → **"Committed Seller Sheet"**

Additional refinements:

-   Buttons remain **independent** (contact can be both buyer and
    seller)

-   Committed states use **solid, professional color styling**

-   Uncommitted states remain outlined

-   Clean, professional visual language was chosen over animation or
    effects

### 2. Buyer & Seller Professional Tracking

Buyer and Seller sheets now support structured capture of:

-   Attorney (name, email, phone, referred by agent)

-   Lender (name, email, phone, referred by agent)

-   Home Inspector (name, email, phone, referred by agent)

-   Other professionals (free text)

This moves transaction-critical information out of notes and into
structured, reportable data.

### 3. Deployment Error Resolved

A production deployment failure was diagnosed and fixed:

-   Root cause: SQL-style (`--`) comments placed inside Python lists

-   Resolution: replaced with valid Python syntax

-   Outcome: successful redeploy and reinforced discipline around
    cross-language syntax

### 4. Add New Contact → Immediate Engagement Flow

A significant UX improvement was agreed upon and implemented
conceptually:

-   After **Add New Contact**, the user should be redirected **directly
    into Edit Contact**

-   This supports immediate engagement, logging, and role commitment

-   Reinforces the principle that contact creation is the *start* of
    work, not the end

### 5. Subject Property Field Reevaluated

A structural decision was made:

-   **Subject Property does not belong on Add New Contact**

-   Property details are now properly captured in:

    -   Buyer sheets (search intent)

    -   Seller sheets (actual property)

Decision:

-   Remove Subject Property from Add Contact UI

-   Avoid data duplication and conflicting "sources of truth"

-   Keep buyer/seller sheets as authoritative property records

## Features Explicitly Deferred

### 1. Reporting (Intentionally Deferred, Fully Planned)

Reporting was identified as the **next major phase**, but deliberately
postponed to allow real-world usage to guide design.

Planned reporting areas:

-   Pipeline health

-   Follow-up compliance

-   Lead sources

-   Committed buyers and sellers

-   Conversion tracking

Export strategy agreed:

-   Phase 1: CSV export (Google Sheets compatible)

-   Phase 2: Direct Google Sheets API integration

No reporting code was added in this session by design.

### 2. Feature Freeze

A conscious decision was made to:

-   Pause feature additions for several days

-   Focus on **using** the CRM

-   Only address bugs or blocking issues

-   Let actual usage surface the next priorities organically

## Design Principles Established or Reinforced

-   **Clarity over cleverness**

-   **One source of truth**

-   **Roles, not labels**

-   **Visual state should communicate workflow state**

-   **Avoid premature abstraction**

-   **Ship, stabilize, then extend**

The system is evolving toward a **personal real estate command center**,
not a bloated general CRM.

## Phase / Version Implications

-   This session represents the **end of a workflow-completion phase**
    for Buyers and Sellers

-   The project is now positioned for:

    -   A **Reporting Phase**

    -   Followed by export and analytics capabilities

```{=html}
<!-- -->
```
-   The CRM is transitioning from *data capture* to *decision support*

## Overall Impact

By the end of this session, the CRM:

-   Feels more intentional and professional

-   Better reflects real real-estate workflows

-   Clearly communicates client commitment state

-   Avoids unnecessary duplication

-   Has a well-defined, disciplined roadmap forward

This session marked a shift from **building features** to **refining a
system**.

# Ulysses CRM --- Project Evolution Summary (Foundational Chat)

**Project Start Date:**\
**December 1--2, 2025** (initial local setup → first Render deployment)

**Project Name:**\
**Ulysses CRM** (renamed from *realEstateCRM* during this phase)

## 1. Original Goals Established

The initial objective was to determine whether a **simple, portable
CRM** could be:

-   Built locally on macOS using Python

-   Deployed to the cloud

-   Accessed across **iMac, MacBook Air, iPhone, and iPad**

-   Gradually evolved into a **professional-grade real estate CRM**
    without overengineering early

Key early questions included:

-   Feasibility of Python + Flask

-   Cloud hosting options

-   Future extensibility (tasks, follow-ups, automation, roles)

## 2. Core Architectural Decisions

### Technology Stack (Locked Early)

-   **Python + Flask**

-   **PostgreSQL** (Render managed database)

-   **Gunicorn** for production

-   **Render** for deployment

-   **GitHub** for version control and CI-style deploys

### Deployment Model

-   Git push → automatic Render redeploy

-   Environment variables for secrets (DATABASE_URL)

-   No local state relied upon after deployment

### Design Philosophy Reinforced

-   **Simple first, extensible later**

-   Avoid premature abstraction

-   Prefer explicit workflows over "magic"

-   One source of truth per concept (no duplicate data)

## 3. Major Features Implemented in This Phase

### A. Contacts (Core Entity)

-   Central **contacts table** established as the foundation

-   First/last name separation implemented

-   Address handling expanded:

    -   Current address

    -   Subject property address

    -   City / State / ZIP for each

```{=html}
<!-- -->
```
-   Mobile-responsive layout refined iteratively

### B. Engagement / Interaction Logging

-   Engagement log added per contact

-   Supports:

    -   Call

    -   Text

    -   Email

    -   Notes

```{=html}
<!-- -->
```
-   Manual time entry added (hour / minute / AM--PM)

-   Delete interaction supported

-   Engagements linked directly to contact record

### C. Follow-Ups & Calendar Integration

-   Follow-up dates stored per contact

-   `/followups` dashboard created

-   `/followups.ics` calendar feed generated

-   Designed for:

    -   Apple Calendar subscription

    -   Daily follow-up review

```{=html}
<!-- -->
```
-   Duration and time handling discussed and incorporated

### D. Navigation & UI Structure

-   Sticky top navigation bar introduced

-   Clean typography and spacing emphasized

-   Section titles standardized (capitalized, bold)

-   Mobile navigation issues identified and iterated

-   Hamburger menu added for mobile

-   Table → card/div-based layouts adopted where appropriate

### E. Branding

-   Application renamed to **Ulysses CRM**

-   SVG logo introduced

-   Logo placement standardized across pages

-   Background color adjusted, then reverted to white for clarity

-   Logo sizing iterated for desktop vs mobile

## 4. Buyer / Seller Profile Architecture (Key Design Decision)

### Decision: Separate Roles from Contacts

A critical architectural choice was made:

-   **Contacts = people**

-   **Roles = how you're working with them**

Implemented:

-   `buyer_profiles` table

-   `seller_profiles` table

Key properties:

-   One contact can be:

    -   Buyer

    -   Seller

    -   Both

    -   Past client / Sphere

```{=html}
<!-- -->
```
-   Buyer and seller data **only captured after commitment**

-   Base contact form intentionally stripped of buyer/seller-specific
    fields

### "Commit Buyer / Commit Seller" Workflow (Approved)

-   Add Contact → capture core info only

-   Buttons on Edit Contact:

    -   "Commit as Buyer"

    -   "Commit as Seller"

```{=html}
<!-- -->
```
-   Clicking creates or updates role-specific profile

-   Prevents form bloat and keeps workflows clear

This became a **foundational design principle** for Ulysses.

## 5. Associated Contacts (Relationships)

-   Related contacts feature added:

    -   Spouse

    -   Partner

    -   Sibling

    -   Friend

    -   Custom relationship text

```{=html}
<!-- -->
```
-   Implemented via `related_contacts` table

-   Delete and add flows refined

-   Duplicate route errors identified and corrected

## 6. Error Handling & Production Lessons Learned

### Key Issues Resolved

-   Flask 3.x deprecations (`before_first_request`)

-   Duplicate route definitions causing deployment failures

-   Missing `DATABASE_URL` causing runtime 500 errors

-   GitHub authentication (token-based)

-   Render environment configuration clarified

### Practices Reinforced

-   One route = one function name

-   No duplicate decorators

-   Always check logs before redeploying

-   Treat Render as production, not a sandbox

## 7. Security & Access

-   GitHub 2FA enabled

-   Render access secured via GitHub auth

-   Login system explicitly **deferred** to a later phase

-   Multi-agent support acknowledged but deferred

## 8. Features Explicitly Deferred (By Design)

Deferred intentionally to avoid scope creep:

-   User authentication / logins

-   Multi-agent accounts

-   Document upload system

-   Automated SMS / email sending

-   Deep OS-level Messages integration

-   Professional directory profiles (attorney/lender tables)

Each deferred item was noted as **future Phase material**, not rejected.

## 9. Phase Transition Marker

This chat represents:

### Phase 0 → Phase 1 Transition

-   Phase 0: Proof of concept, deployment, architecture validation

-   Phase 1: Real CRM behavior, workflows, daily usability

At the end of this chat:

-   Core architecture stabilized

-   Naming locked (Ulysses CRM)

-   Deployment pipeline working

-   Clear roadmap defined

## 10. Design Ethos Captured

Several guiding principles were established and repeatedly reinforced:

-   Ulysses should **think like a real agent**

-   Contacts evolve into roles, not the other way around

-   UI clarity \> feature count

-   Mobile usability matters

-   If something feels like a rabbit hole, pause and reassess

### Status at End of Chat

-   App live on Render

-   PostgreSQL connected

-   Buyer/Seller profiles in place

-   Engagement logging functional

-   Follow-up dashboard operational

-   Ready to move into structured, multi-chat project work

## Ulysses CRM -- Project Evolution Summary

**Chat Start Date:** December 8, 2025\
**Context:** Phase 6 UX & Layout Refinement (post-v0.11.x, pre-v0.12.x)

### 1. Primary Goals of This Session

-   Continue UI unification across templates (`base.html`,
    `contacts.html`, buyer/seller profiles).

-   Improve navigation clarity and user flow between Contact →
    Buyer/Seller sheets.

-   Introduce a global footer with a dynamic copyright notice.

-   Begin groundwork for a future **tab-based UI system** (explicitly
    *not* navbar-based).

### 2. Key Decisions Made

#### Navigation & UX

-   **Confirmed behavior:**

    -   Clicking a contact name should route intelligently:

        -   Buyer profile if committed as buyer

        -   Seller profile if committed as seller

        -   Neutral Edit Contact otherwise

```{=html}
<!-- -->
```
-   **Deferred:** Global tab navigation logic

    -   User clarified they want **page-level tabs**, not navbar
        additions.

    -   Tab system discussion paused intentionally to avoid scope creep.

#### Footer / Copyright

-   Decision to add a **global footer** in `base.html`.

-   Copyright text:

-   `©`` ``{``{`` current_year ``}``}`` Ithaca Enterprises. All rights reserved.`

-   Implemented via a **Flask `@app.context_processor`** to inject
    `current_year`.

-   Several deploy failures occurred before final resolution due to:

    -   Undefined `now()` usage in Jinja

    -   Missing `Response` import

    -   Misplaced `return render_template()` outside of route functions

```{=html}
<!-- -->
```
-   **Outcome:** Footer logic works once context processor placement and
    syntax errors were corrected.

### 3. Features Added or Validated

#### UI / Templates

-   `base.html` standardized with:

    -   Sticky top navbar (unchanged scope)

    -   Central content container

    -   Global footer

```{=html}
<!-- -->
```
-   `contacts.html`, `buyer_profile.html`, `seller_profile.html`:

    -   Verified render calls

    -   Confirmed consistent use of `active_page`

    -   Cleaned up duplicate logos and header inconsistencies

```{=html}
<!-- -->
```
-   Buyer/Seller "Committed" buttons:

    -   Confirmed correct routing to existing profiles

    -   Visual state (solid vs. outline) validated

#### Backend / Flask

-   Added:

-   `@app.context_processor`

-   `def inject_current_year():`

-   `    return ``{``"current_year": datetime.now().year``}`

-   Fixed missing import:

-   `from flask import Response`

-   Identified and corrected a critical structural issue:

    -   `return render_template(...)` placed outside a route function
        caused repeated deploy failures.

### 4. Design Principles Reinforced

-   **Single source of truth:** Shared layout belongs in `base.html`.

-   **Non-destructive iteration:** When something breaks in production,
    fix forward rather than rolling back aggressively.

-   **Clarity over cleverness:** Avoid implicit Jinja globals (`now()`)
    unless explicitly defined.

-   **Separation of concerns:**

    -   Navbar = global app navigation

    -   Tabs = contextual, page-level navigation (explicitly deferred)

### 5. Deferred / Parked Items

-   Full **tab navigation logic** (Buyer / Seller / Engagements /
    Transactions).

-   Tab persistence (URL hash vs. JS state).

-   Any new navbar items.

-   Further UX polish beyond bug fixes.

### 6. Phase / Version Context

-   This work fits into **Phase 6c (UX Maturity & Workflow
    Completion)**.

-   No version bump committed during this session.

-   Several fixes qualify as **production hotfixes**, not feature
    expansion.

-   Tab system is expected to be a **future Phase 6c or Phase 7
    initiative**, depending on scope.

### 7. Notable Takeaways

-   Production-only development workflow confirmed (no local testing
    preference).

-   Render logs proved essential for diagnosing:

    -   Jinja context issues

    -   Syntax errors preventing Gunicorn startup

```{=html}
<!-- -->
```
-   Once structural errors were resolved, system stability returned
    quickly.

**Status at End of Chat:**\
System stable, footer working, navigation clarified, tab discussion
intentionally paused for a future session.

# Ulysses CRM --- Security Hardening, Template Stabilization, and Profile Fixes

**Start date:** December 8, 2025\
**Context:** Phase 6 (Workflow Completion & UX Maturity), late Phase 6b
→ 6c hardening

## High-Level Goals

This work session focused on **hardening the production CRM**, restoring
**workflow stability after recent security changes**, and reinforcing
**template and data-flow consistency** following the transition from
embedded templates to file-based Jinja templates.

Primary goals were:

-   Secure the application without breaking existing workflows

-   Restore Buyer and Seller profile persistence

-   Ensure calendar feed security works end-to-end

-   Eliminate UI duplication introduced during template refactors

-   Re-establish architectural clarity after rapid changes

## Key Decisions & Outcomes

### 1. Authentication & Environment Hardening (Completed)

**Decisions**

-   Production security must fail fast if required secrets are missing.

-   Render environment variables are the single source of truth.

-   GitHub 2FA + Render OAuth is sufficient for deploy security.

**Actions**

-   Verified and enforced required environment variables:

    -   `SECRET_KEY`

    -   `ADMIN_USERNAME`

    -   `ADMIN_PASSWORD`

    -   `FLASK_ENV=production`

```{=html}
<!-- -->
```
-   Confirmed `DATABASE_URL` is managed by Render.

-   Retained optional but recommended variables:

    -   `ICS_TOKEN`

    -   `SHORTCUT_API_KEY`

**Result**

-   Login enforcement is stable.

-   Sessions are secure and production-safe.

-   App no longer boots in an insecure configuration.

### 2. Calendar Feed Security (Completed)

**Problem**

-   Calendar feed returned `401 Unauthorized` after security changes.

-   The navbar "Calendar Feed" menu item still linked to the unprotected
    URL.

**Key Decision**

-   Calendar feed must remain protected using `ICS_TOKEN`.

-   The UI must dynamically generate the correct feed URL.

**Implementation**

-   Introduced a global `@app.context_processor` to inject:

    -   `calendar_feed_url`

```{=html}
<!-- -->
```
-   Updated `base.html` navbar to use the injected URL.

-   Confirmed:

    -   `/followups.ics?key=...` works

    -   macOS Calendar subscription updated accordingly

**Result**

-   Calendar feed is secure, functional, and UI-correct.

-   Unauthorized log noise eliminated.

-   This established a **pattern for global UI configuration via context
    processors**.

### 3. Buyer & Seller Profile Blank Data Bug (Root Cause Identified & Fixed)

**Symptoms**

-   Buyer and Seller sheets rendered but appeared blank after save.

-   No database errors initially.

**Root Cause**

-   Template variable mismatch introduced during earlier
    "simplification."

-   Templates expected legacy variables (`bp`, `sp`, `contact_id`), but
    routes were passing generic names (`profile`).

**Key Design Principle Reinforced**

*Templates define the contract. Routes must conform unless templates are
refactored simultaneously.*

**Fix**

-   Restored correct variable passing:

    -   Buyer: `bp`, `contact_id`, `contact_name`, etc.

    -   Seller: `sp`, `contact_id`, `contact_name`, etc.

```{=html}
<!-- -->
```
-   Maintained backward compatibility by also passing `profile` and
    `checklist`.

**Result**

-   Buyer and Seller profile data now persists and re-renders correctly.

-   Established the need for a **formal variable audit** before
    refactors.

### 4. Seller Profile Crash on Save (Critical Bug Fixed)

**Error**

    TypeError: not all arguments converted during string formatting

**Root Cause**

-   Mismatch between:

    -   Number of columns in `seller_profiles`

    -   Number of `%s` placeholders

    -   Number of values passed to psycopg2

**Fix**

-   Rebuilt the entire `seller_profile` POST logic:

    -   Explicit, ordered column lists

    -   Matching placeholder counts

    -   Safe handling of optional numeric fields

```{=html}
<!-- -->
```
-   Ensured `INSERT` and `UPDATE` statements were symmetrical and
    correct.

**Result**

-   Seller profiles save reliably.

-   Redirect flow restored.

-   Buyer profile logic confirmed stable by comparison.

### 5. Template Architecture Cleanup (Completed)

**Context**

-   Project fully transitioned from embedded templates in `app.py` to
    file-based templates under `/templates`.

**Issue**

-   `edit_contact.html` still contained legacy navbar/logo markup.

-   Resulted in a duplicated logo and hamburger menu on that page.

**Decision**

-   Navbar and branding must exist **only in `base.html`**.

-   Child templates must never duplicate layout elements.

**Action**

-   Removed logo and navbar markup from `edit_contact.html`.

**Result**

-   UI consistency restored.

-   Reinforced the design rule:

*`base.html` owns layout; child templates own content only.*

## Design Principles Established or Reinforced

1.  **Template Contracts Are Sacred**\
    Variable names used in templates are an API. They must not be
    changed casually.

2.  **Global UI Logic Belongs in Context Processors**\
    Navigation-level features (calendar feed, branding, auth state)
    should not be route-specific.

3.  **Security Changes Must Be Followed by Workflow Validation**\
    Authentication and environment hardening can expose latent coupling
    issues.

4.  **Avoid "Simplification" Without Structural Awareness**\
    Reducing variables without template audits causes silent failures.

5.  **Single Source of Truth for Layout**\
    `base.html` owns all global UI elements.

## Phase / Version Context

-   This work occurred during **Phase 6 (Workflow Completion & UX
    Maturity)**.

-   Specifically bridged late **Phase 6b → Phase 6c**.

-   No formal version bump was issued during this session, but stability
    and security were significantly improved.

-   This work lays the foundation for:

    -   Multi-user authentication (future phase)

    -   Reporting features

    -   Safer template refactors

## Deferred / Next Recommended Work

-   **Clean Variable Audit (Recommended Next Step)**

    -   Inventory all templates and their required context variables.

    -   Document the "view → template" contracts explicitly.

```{=html}
<!-- -->
```
-   Optional future improvements:

    -   CSRF protection

    -   Rate-limited login attempts

    -   Password hashing and user table

    -   Further template extraction and modularization

# Ulysses CRM --- Professionals Module & Buyer Sheet Fix

**Chat Summary for Project History & Evolution**

**Start date:** December 8, 2025 (evening)\
**End date:** December 9, 2025 (early morning)

## 1. Primary Goals of This Chat

-   Introduce a **Professionals module** to Ulysses CRM that allows:

    -   Centralized management of attorneys, lenders, inspectors, and
        other vendors

    -   Grading professionals from *core* to *blacklisted*

    -   Reuse of trusted professionals via dropdowns in Buyer and Seller
        Profiles

```{=html}
<!-- -->
```
-   Avoid premature UI complexity by **deferring the tabbed layout** to
    a future release

-   Ensure Buyer and Seller sheets remain clean, non-duplicative, and
    reliable

-   Resolve production errors caused by schema mismatches and SQL
    placeholder errors

## 2. Key Decisions Made

### A. Professionals Module Design

-   Implemented a **dedicated `professionals` table** rather than
    embedding vendors in buyer/seller tables.

-   Established a **grading system**:

    -   `core` -- always refer

    -   `preferred` -- frequent referrals

    -   `vetting` -- testing / client-selected

    -   `blacklist` -- never shown in dropdowns

```{=html}
<!-- -->
```
-   Decision: **Blacklisted professionals are excluded at the query
    layer**, not filtered in templates.

### B. UI / UX Decisions

-   Professionals appear:

    -   As a top-level **"Professionals"** section in the main
        navigation

    -   As **dropdown selectors** inside Buyer and Seller Profiles

```{=html}
<!-- -->
```
-   Auto-population behavior:

    -   Selecting a professional fills name, email, and phone fields

    -   Manual entry remains possible for one-off or external
        professionals

```{=html}
<!-- -->
```
-   Explicit decision to **remove duplicate / legacy lender fields**
    from the Buyer Profile to avoid confusion.

### C. Scope Control

-   Deferred:

    -   Tabbed layout refactor

    -   Advanced filtering, usage metrics, or reporting for
        professionals

```{=html}
<!-- -->
```
-   Focus kept strictly on:

    -   Core functionality

    -   Production stability

    -   Schema correctness

## 3. Features Added

### A. Database

-   New `professionals` table added to production PostgreSQL on Render
    via manual SQL (Option A).

-   Columns include:

    -   Identity and contact info

    -   Category (Attorney, Lender, Inspector, etc.)

    -   Grade

    -   Notes

    -   Timestamps

### B. Backend (Flask / app.py)

-   Added helper function to retrieve professionals for dropdowns,
    excluding blacklisted entries.

-   Added full CRUD routes:

    -   `/professionals`

    -   `/professionals/<id>/edit`

    -   `/professionals/<id>/delete`

```{=html}
<!-- -->
```
-   Wired professionals into:

    -   Buyer Profile route

    -   Seller Profile route

### C. Frontend (Templates)

-   New templates:

    -   `professionals.html`

    -   `edit_professional.html`

```{=html}
<!-- -->
```
-   Buyer and Seller Profiles updated to:

    -   Replace free-text professional fields with dropdown-driven
        inputs

    -   Auto-fill associated contact fields

```{=html}
<!-- -->
```
-   Removed redundant lender section from Buyer Profile (legacy
    remnant).

## 4. Bugs Encountered & Resolved

### A. 500 Error on `/professionals`

-   Cause: `professionals` table did not exist in production.

-   Resolution:

    -   Manual SQL execution via Render PostgreSQL using `psql`.

    -   Confirmed schema before retesting.

### B. 500 Error on Buyer Profile POST

-   Error: `IndexError: tuple index out of range`

-   Cause:

    -   Mismatch between SQL placeholders and provided values in
        `INSERT INTO buyer_profiles`.

    -   Extra `%s` placeholder left behind after form refactor.

```{=html}
<!-- -->
```
-   Resolution:

    -   Corrected placeholder count to exactly match columns (27).

    -   Verified UPDATE block already correct.

    -   Redeployed successfully.

## 5. Design Principles Reinforced

-   **Schema-first discipline**: UI changes must always be reflected in
    SQL statements.

-   **No silent duplication**: One logical place for each concept (e.g.,
    lenders only live in Professionals).

-   **Incremental evolution**: Large UI refactors (tabs) deferred in
    favor of shipping stable value.

-   **Production parity awareness**: Explicit handling of Render
    limitations (no in-browser SQL console).

-   **Explicit debugging**: Logs treated as authoritative; errors fixed
    at the root cause, not patched.

## 6. Phase / Version Context

-   Work occurred post--Phase 6 series, continuing iterative refinement
    toward v1.0.

-   Professionals module is now a **first-class system** within Ulysses
    CRM.

-   This work sets the foundation for future enhancements such as:

    -   Usage analytics per professional

    -   Preferred vendor exports

    -   Transaction-level professional linking

## 7. End State

By the end of this chat:

-   The Professionals module is live in production.

-   Buyer and Seller Profiles save and load correctly.

-   All 500 errors encountered during this session were fully resolved.

-   Scope was consciously controlled, with deferred features clearly
    identified.

**Session closed successfully.**

## Ulysses CRM Project

### Chat Summary: Template Structure Alignment & Safe Refactor Preparation

**Start date:** December 9, 2025

### 1. Primary Goal of This Chat

The goal of this chat was to **stabilize and formally document the
current file and folder structure** of the Ulysses CRM project while
preparing for a future, modular refactor. The emphasis was on **avoiding
regressions**, **protecting active functionality**, and **introducing
structure incrementally** rather than through a disruptive rewrite.

### 2. Key Decisions Made

#### A. Folder Structure Strategy

-   A **modular template structure** (buyers/, sellers/, contacts/,
    tasks/) was confirmed as the long-term direction.

-   **Active templates remain in the root `templates/` folder** for now
    to avoid breaking existing routes.

-   Only **unused placeholder templates** were moved into subfolders.

-   Subfolders were created proactively to support future refactors
    without requiring immediate route changes.

This established a **hybrid transition state** that balances cleanliness
with stability.

#### B. Explicitly Confirmed Current Template State

The following files were confirmed as **active and in use**, and
therefore intentionally left in the root `templates/` directory:

-   base.html

-   buyer_profile.html

-   contacts.html

-   dashboard.html

-   edit_contact.html

-   edit_professional.html

-   error.html (placeholder but wired)

-   followups.html

-   professionals.html

-   seller_profile.html

These files remain untouched until a deliberate refactor phase.

#### C. Placeholder Files Moved Safely Into Subfolders

The following files were confirmed as **placeholders only** and were
safely relocated into their respective subdirectories:

-   `templates/contacts/add_contact.html`

-   `templates/buyers/add_buyer_profile.html`

-   `templates/buyers/edit_buyer_profile.html`

-   `templates/sellers/add_seller_profile.html`

-   `templates/sellers/edit_seller_profile.html`

-   `templates/tasks/task_modal.html`

Because no active routes referenced these files yet, **no code changes
were required**.

### 3. Design Principles Reinforced

#### Stability First

-   No active template or route should be moved without updating
    `render_template` paths.

-   Placeholder files can be structured in advance with zero risk.

-   Refactors should be incremental, testable, and reversible.

#### Explicit State Tracking

-   The exact live structure of the project was documented and committed
    to memory to avoid future ambiguity.

-   "Assumed" structure was rejected in favor of **verified, current
    state**.

#### Future-Ready Without Premature Optimization

-   Subfolders were created early, but **adoption is deferred** until
    routes are intentionally migrated.

-   This avoids the common trap of breaking working software in pursuit
    of architectural purity.

### 4. Infrastructure Decisions Confirmed

-   `crm.db` remaining in the **top-level project folder** was confirmed
    as acceptable and appropriate for the current phase.

-   `requirements.txt` in the **top-level folder** was confirmed as
    correct and deployment-ready.

-   No database or environment migrations were introduced in this chat.

### 5. Features Added or Deferred

#### Added

-   Placeholder boilerplate files for helpers, CSS, JS, and future
    templates.

-   Subfolder structure for templates to support upcoming features.

#### Explicitly Deferred

-   Moving active templates into subfolders.

-   Updating Flask routes to new template paths.

-   Any functional changes to buyer, seller, contact, or professional
    workflows.

-   Any version bump or phase transition.

This chat intentionally focused on **structure and documentation**, not
new functionality.

### 6. Phase / Version Context

-   This work sits within **Phase 4.5 / v0.10.x continuity**, focused on
    stabilization and groundwork.

-   No new phase was entered.

-   No version number was changed.

-   This chat acts as a **pre-refactor alignment checkpoint** before
    deeper UI and routing changes.

### 7. Outcome

At the end of this chat:

-   The exact current structure of Ulysses CRM templates is known,
    documented, and saved.

-   The project is cleanly prepared for future modularization.

-   No existing functionality was disrupted.

-   A clear, shared understanding exists of what is active now versus
    what is planned.

This summary is suitable for canon inclusion in Ulysses CRM historical
documentation.

## Chat Summary: Git Identity Configuration Clarification

**Start Date:** December 7, 2025

### Goal of This Chat

To understand and document the meaning of a Git warning message related
to user identity configuration during commits, and to clarify best
practices for resolving it cleanly.

### Key Explanation Provided

-   Git automatically inferred the commit author's name and email using
    the local system's username and hostname because explicit identity
    settings were not configured.

-   Git issued a warning to prompt the user to explicitly define
    `user.name` and `user.email` to ensure correct attribution of
    commits, especially for platforms like GitHub.

### Key Actions Identified

-   Set a global Git identity using:

    -   `git config --global user.name "Your Name"`

    -   `git config --global user.email "you@example.com"`

```{=html}
<!-- -->
```
-   Optionally amend the most recent commit to correct the author
    metadata using:

    -   `git commit --amend --reset-author`

### Design Principles Reinforced

-   **Explicit configuration over defaults:** Avoid relying on
    auto-generated system values for commit metadata.

-   **Clean commit history:** Ensure commits are correctly attributed
    from the outset to prevent downstream confusion in repositories and
    collaboration tools.

-   **One-time setup mentality:** Git identity configuration is a
    foundational, environment-level setup step rather than a per-project
    task.

### Features Added or Deferred

-   No features were added or deferred in this chat.

-   This discussion supports foundational development hygiene rather
    than application functionality.

### Phase or Version Impact

-   No direct phase or version transition occurred.

-   This clarification supports ongoing development work by reducing
    future friction in Git workflows across all project phases.

## Ulysses CRM --- Reminder Notifications (Safari / Browser-Native)

**Session Focus:** Internal CRM reminders with browser notifications\
**Status:** Core infrastructure complete; UI deferred\
**Date:** December 9, 2025

## 1. Goal of This Work

The primary goal of this session was to determine whether **Ulysses CRM
could handle reminders internally**, including **active notifications**,
without relying on external systems such as Apple Reminders.

The secondary goal was to design this in a way that:

-   Avoids calendar clutter

-   Keeps reminders tightly bound to CRM interactions

-   Preserves future extensibility (exporting, push notifications, UI
    controls)

## 2. Key Design Decisions

### 2.1 Reminders vs Calendar Items (Conceptual Split)

A clear architectural distinction was established:

-   **Reminders**

    -   Internal CRM follow-ups

    -   No hard time-blocking requirement

    -   Agent-facing only

    -   Stored as part of the interaction lifecycle

```{=html}
<!-- -->
```
-   **Calendar Items**

    -   Real appointments

    -   Time-blocking required

    -   External-facing or multi-party

    -   Continue to live in calendar / iCal workflows

This reinforced the principle that **not everything deserves a calendar
entry**.

### 2.2 No Apple Reminders Dependency

After discussion, the decision was made to:

-   **Not** sync to Apple Reminders

-   **Not** require CalDAV or external task systems

-   Rely instead on **browser-native notifications** delivered directly
    by Ulysses

This keeps:

-   Ownership inside the CRM

-   Complexity lower

-   Portability higher across platforms

## 3. Feature Implemented

### 3.1 Reminder Infrastructure (Backend)

Instead of creating a new table, reminders were intentionally modeled as
part of the existing `interactions` table.

Confirmed schema:

-   `interactions.due_at TIMESTAMPTZ`

-   `interactions.notified BOOLEAN`

-   Existing `is_completed` used to suppress alerts

A new API endpoint was added:

    GET /api/reminders/due

Behavior:

-   Returns due interactions within a rolling window

-   Suppresses completed or already-notified interactions

-   Marks reminders as `notified = TRUE` once sent

-   Prevents duplicate notifications

This aligned with an existing design principle:

Interactions are the single source of truth for follow-ups.

### 3.2 Browser Notification Delivery (Frontend)

A polling-based notification system was added to `base.html`:

-   Uses the native `Notification` Web API

-   Polls `/api/reminders/due` every 60 seconds

-   Fires **system-level notifications** (Safari confirmed)

-   Requires the CRM tab to be open (foreground or background)

This achieved:

-   Real notifications without external services

-   No Apple, Google, or third-party task dependencies

-   Cross-platform behavior

## 4. Debugging & Platform-Specific Learnings

### 4.1 Safari 18.6 Notification Behavior

Key Safari-specific constraints were identified and resolved:

-   Safari does not appear in macOS Notifications until **any site
    requests permission**

-   Notification permissions may be silently blocked without UI feedback

-   Manual permission forcing via:

-   `Notification.requestPermission()`

was required

-   Once allowed, Safari notifications functioned correctly

### 4.2 Render / Flask Issue Resolved

A production bug was identified and fixed:

-   `/api/reminders/due` initially returned HTTP 500

-   Root cause: cursor returned **dict-style rows**, but code assumed
    tuples

-   Fix: switched to key-based row access (`row["id"]`, etc.)

-   Result: endpoint stabilized, no further errors

## 5. What Was Explicitly Deferred

### Deferred to a future session:

-   UI field for setting `due_at` in the "Save Interaction" form

-   Reminder date/time picker

-   Visual indicators for interactions with reminders

-   Background push notifications via service workers

-   Reminder preferences per user

This was an intentional decision to:

-   Lock the infrastructure first

-   Avoid scope creep

-   Keep Phase velocity controlled

## 6. Design Principles Reinforced

This session reinforced several core Ulysses CRM principles:

1.  **Internal-first architecture**\
    Reminders live inside the CRM, not outsourced to OS tools.

2.  **Minimal duplication**\
    No new reminders table; reuse interactions cleanly.

3.  **Separation of concerns**\
    Reminders ≠ calendar events.

4.  **Progressive enhancement**\
    Browser polling now; true push later.

5.  **Production realism**\
    All features validated on Render + Safari, not just locally.

## 7. Current Status

-   Reminder notifications: **LIVE and WORKING**

-   Backend: **Stable**

-   Frontend notification delivery: **Confirmed**

-   UI for setting reminders: **Deferred**

## 8. Recommended Next Step (When Resumed)

When continuing this work, the next logical task is:

Add a `due_at` datetime field to the Interaction form and persist it
through the existing save route.

No architectural changes are required to proceed.

### �� Ulysses CRM -- Template Safety & Refactor Strategy

**Date:** December 9, 2025\
**Context:** Ongoing Phase 6 / v0.10.x--v0.11.x development
stabilization

## �� Goal of This Discussion

To decide whether legacy or inline templates embedded in `app.py` should
be deleted now that a full filesystem-based `templates/` structure
exists.

## ✅ Key Decision

**Do not delete or refactor any templates in `app.py` at this time.**

This decision prioritizes **application stability over cleanup**,
especially while the CRM is actively being used and tested.

## �� Reasoning Behind the Decision

-   Some routes may still rely on:

    -   Inline HTML responses

    -   `render_template_string`

    -   Legacy template references not yet fully migrated

```{=html}
<!-- -->
```
-   Deleting template logic prematurely could cause:

    -   500 server errors

    -   Template-not-found failures

    -   Broken workflows in Contacts, Buyers, Sellers, Tasks, or
        Professionals

```{=html}
<!-- -->
```
-   The current `templates/` directory structure is valid and working,
    but full parity with `app.py` has not yet been explicitly audited
    route-by-route.

## �� Design Principles Reinforced

-   **Stability first, cleanup later**

-   **No silent refactors**

-   **Incremental, verifiable changes**

-   **Refactors should be reversible (branch-based)**

This aligns with existing Ulysses CRM practices of:

-   Phase locking

-   Deferred cleanup until behavior is proven stable

-   Using git branches for non-essential refactors

## �� Features Added or Deferred

### Added

-   No new features were added in this chat.

### Deferred

-   Cleanup and removal of inline or legacy templates in `app.py`

-   Formal audit of route-to-template mappings

This cleanup is explicitly deferred until:

-   The CRM has been used for several days without issues

-   A deliberate cleanup branch is created

-   Each route is reviewed and confirmed safe to refactor

## ��️ Agreed Future Path (When Ready)

When cleanup begins:

1.  Review `app.py` route by route

2.  Confirm each route renders a real template file

3.  Categorize legacy code as:

    -   KEEP

    -   SAFE TO DELETE

    -   REFACTOR LATER

```{=html}
<!-- -->
```
1.  Perform cleanup on a dedicated git branch (e.g. `cleanup-templates`)

## �� Phase / Version Status

-   No phase transition occurred in this chat

-   This discussion supports **Phase 6 stabilization** and prepares for
    future **post-v1.0 cleanup work**

-   The CRM remains in a **safe, non-destructive state**

**Summary Verdict:**\
This chat intentionally reinforced a conservative, professional
engineering approach. No code was deleted, no behavior changed, and
long-term maintainability was preserved by deferring cleanup until it
can be done safely and deliberately.

## Ulysses CRM --- Buyer Subject Properties & Offers

**December 11,2025**

**Project Evolution Summary**

### Timeframe

December 11, 2025. Local development and deployment session culminating
in a successful Render deploy.

## Primary Goal

Enhance the **Buyer Profile workflow** to support real-world buying
activity by allowing:

-   Multiple subject properties per buyer

-   Tracking offer status per property

-   Editing subject properties independently

-   Preserving a clean, desktop-friendly UI

-   Ensuring backward compatibility with existing buyer and seller
    workflows

## Key Features Added

### 1. Subject Properties & Offers (Buyer Profile)

-   Introduced a **Subject Properties and Offers** section on the Buyer
    Profile.

-   Each buyer can now have **multiple subject properties**, each with:

    -   Address

    -   City / State / Zip

    -   Offer status:

        -   Considering

        -   Accepted

        -   Lost

        -   Attorney Review

        -   Under Contract

### 2. Auto-Creation of Buyer Profile

-   When adding a subject property:

    -   If a buyer profile does not yet exist, it is **created
        automatically**

    -   Prevents blocking workflows and supports incremental data entry

### 3. Edit Subject Property Functionality

-   Added an **Edit** action per subject property row.

-   Implemented a dedicated edit route and template:

    -   `/buyer/property/<id>/edit`

```{=html}
<!-- -->
```
-   Editing a property:

    -   Does not interfere with the main Buyer Profile form

    -   Returns cleanly back to the Buyer Profile upon save

### 4. Desktop-Optimized UI

-   Subject property entry uses **single-row input layout** on larger
    screens.

-   Reinforces Ulysses CRM's design preference for:

    -   Density without clutter

    -   Fast scanning and data entry

    -   Desktop-first professional workflows

## Critical Bugs Identified & Resolved

### Buyer Profile Rendering Bug

-   Buyer profiles were rendering blank (name, email, phone missing).

-   Root cause:

    -   `buyer_profile` route was not passing required context
        variables.

```{=html}
<!-- -->
```
-   Fix:

    -   Properly wired `bp`, `contact_name`, `contact_email`,
        `contact_phone` into the template context.

```{=html}
<!-- -->
```
-   Seller profiles were unaffected.

### Subject Property Not Saving

-   Properties appeared to submit but never displayed.

-   Root cause:

    -   Conditional logic prevented inserts when buyer profile didn't
        yet exist.

```{=html}
<!-- -->
```
-   Fix:

    -   Auto-create buyer profile before inserting subject property.

### Form Submission Conflict

-   Single form contained both:

    -   Buyer profile fields

    -   Subject property fields

```{=html}
<!-- -->
```
-   Issue:

    -   HTML `required` attribute on subject property address blocked
        saving the buyer profile.

```{=html}
<!-- -->
```
-   Resolution:

    -   Removed `required` from HTML.

    -   Relied on server-side validation (`if address_line:`) instead.

### Jinja Template Nesting Errors

-   Encountered `endif` / `endfor` mismatch during template edits.

-   Resolution:

    -   Replaced the Subject Properties table block with a clean,
        validated Jinja structure.

### Missing Template Error

-   `TemplateNotFound: edit_buyer_property.html`

-   Root cause:

    -   Template created but not placed in `/templates`.

```{=html}
<!-- -->
```
-   Resolution:

    -   Corrected file location and Git tracking.

## Git & Deployment Decisions

-   Confirmed **laptop** as the authoritative development environment.

-   Synced laptop and iMac via Git to avoid timestamp confusion.

-   Used:

    -   `git pull --rebase` before pushing

    -   Manual Render deploy after verified local success

```{=html}
<!-- -->
```
-   Ensured new templates were explicitly tracked (`git add` for
    untracked files).

## Design Principles Reinforced

-   **Incremental data entry over forced completeness**

-   **No blocking UX** for partially known information

-   **Single-responsibility forms** (edit screens instead of nested
    forms)

-   **Desktop-first CRM ergonomics**

-   **Server-side validation over fragile HTML constraints**

-   **Backward compatibility first** (seller flows untouched)

## Phase / Version Context

-   This work fits cleanly into **post-v0.10.x / Phase 4.5--6c
    evolution**

-   No schema migrations were required for this iteration.

-   Feature is production-ready and safely deployed.

-   Sets groundwork for future enhancements:

    -   Subject property deletion

    -   Offer analytics

    -   Buyer activity summaries

    -   Reporting and exports

## Current Status

-   ✅ Fully functional locally and on Render

-   ✅ Buyer profile integrity restored

-   ✅ Subject properties add/edit flow complete

-   ✅ UI approved for desktop use

-   �� Optional enhancements intentionally deferred

## FlexMLS Contact Import into Ulysses CRM

**December 11, 2025**

**Historical & Project-Evolution Summary**

### Goal

Enable a clean, repeatable import of FlexMLS contacts into Ulysses CRM
while preserving data integrity, avoiding duplicates, and aligning with
existing schema constraints.

### Key Decisions & Actions

1.  **Import Strategy Selected**

    -   Chose **Option 1: Temporary Import Route** in `app.py` rather
        than direct database import.

    -   Rationale:

        -   Uses existing Ulysses DB connection logic (`get_db()`).

        -   Allows validation, duplicate checking, and safe rollback.

        -   Keeps import logic auditable and aligned with app behavior.

```{=html}
<!-- -->
```
1.  **CSV Reconfiguration**

    -   Reformatted FlexMLS export into a Ulysses-friendly CSV with
        fields:

        -   `first_name`

        -   `last_name`

        -   `email`

        -   `phone`

        -   `notes`

    ```{=html}
    <!-- -->
    ```
    -   Added a uniform note to all records:

        -   **"Imported from FlexMLS"**

    ```{=html}
    <!-- -->
    ```
    -   Re-ran configuration after the source file was refreshed and
        contacts were deleted upstream.

```{=html}
<!-- -->
```
1.  **Robust Import Route Design**

    -   Implemented a temporary `/import_flexmls` route with:

        -   Absolute file path resolution using
            `os.path.dirname(__file__)`.

        -   Email-based duplicate detection.

        -   Skipping of empty rows.

        -   Insert counters and browser-visible summary output.

        -   Explicit commit/rollback handling for safety.

```{=html}
<!-- -->
```
1.  **Schema Constraint Resolution**

    -   Encountered a production-relevant error:

        -   `contacts.name` is `NOT NULL`.

    ```{=html}
    <!-- -->
    ```
    -   Decision:

        -   Construct `name` dynamically during import:

            -   `First Last` if available

            -   fallback to email or phone

    ```{=html}
    <!-- -->
    ```
    -   This reinforced the importance of honoring **display-level
        fields** even during batch imports.

```{=html}
<!-- -->
```
1.  **Successful Import Outcome**

    -   Final execution result:

        -   **Imported:** 60 contacts

        -   **Skipped existing:** 1 (duplicate by email)

        -   **Skipped empty:** 0

    ```{=html}
    <!-- -->
    ```
    -   Verified correct population of name, contact fields, and notes
        inside Ulysses.

```{=html}
<!-- -->
```
1.  **Post-Import Cleanup**

    -   Reinforced best practice:

        -   **Delete the temporary import route after successful
            execution** to prevent accidental re-imports.

### Design Principles Reinforced

-   **Non-destructive data handling**

    -   No overwrites or silent updates.

    -   Explicit skipping of duplicates.

```{=html}
<!-- -->
```
-   **Schema-first imports**

    -   Import logic must respect required columns and application
        expectations, not just raw data availability.

```{=html}
<!-- -->
```
-   **Temporary tooling, permanent safety**

    -   One-off utilities live briefly, are auditable, and are removed
        once their purpose is fulfilled.

```{=html}
<!-- -->
```
-   **Operational transparency**

    -   Browser-visible summaries and terminal error output preferred
        over silent failures.

### Features Added (Temporary)

-   `/import_flexmls` route for controlled CSV import\
    *(explicitly temporary and removed after use)*

### Features Deferred / Not in Scope

-   UI-based CSV import tool

-   Persistent "source" column (notes used instead)

-   Bulk tagging or categorization during import

-   Automated scheduled imports

### Phase / Version Context

-   This work occurred during active **post-v0.10.x / Phase 4--5 era**
    development.

-   No version bump required.

-   Changes were operational and data-oriented, not core feature
    expansion.

### Net Impact

This chat established a **repeatable, schema-safe pattern for future
bulk imports** into Ulysses CRM and clarified how to reconcile
third-party data with Ulysses' internal data model without compromising
integrity or workflow discipline.

## �� CRM Project -- Contacts Navigation & UI Refactor

**Date:** December 11, 2025\
**Environment:** Local development (MacBook → synced to iMac via Git)

## �� Primary Goal

Improve usability and scalability of the **Contacts** section as the
dataset grows, without disrupting existing workflows such as inline
contact creation, buyer/seller commitment logic, or professional
separation.

## ✅ Key Decisions

### 1. Navigation Strategy Chosen

-   Adopted **Option D**:

    -   Tabs

    -   Search

    -   Pagination (50 per page)

```{=html}
<!-- -->
```
-   Explicitly **excluded Professionals** from Contacts tabs to preserve
    their independent module and future expansion (grading, activity
    tracking, memorialization of performance).

### 2. Tab Taxonomy (Option C)

Final tabs implemented:

-   All

-   Buyers

-   Sellers

-   Leads

-   Past Clients

Tabs are derived from existing schema:

-   `lead_type`

-   `pipeline_stage`

No new schema was introduced.

## �� Design Principles Reinforced

-   **Local-first development is mandatory** for structural UI and query
    changes.

-   **Do not infer or invent schema**: adapt logic to the existing
    database.

-   **Preserve workflows**: the inline "Add Contact" form remains
    intact.

-   **Professionals remain separate** from Contacts to avoid semantic
    dilution.

-   **Dict-based cursor usage (RealDictCursor)** must be respected
    end-to-end.

-   **Visual clarity over clever CSS**: structural fixes (cards) beat
    styling hacks.

## �� Features Added

### Contacts Page Enhancements

-   Tab-based filtering using existing fields:

    -   Buyers/Sellers via `lead_type`

    -   Leads and Past Clients via `pipeline_stage`

```{=html}
<!-- -->
```
-   Search across:

    -   name

    -   first_name / last_name

    -   email

    -   phone

    -   notes

```{=html}
<!-- -->
```
-   Pagination:

    -   50 contacts per page

    -   Count query using `COUNT(*) AS total`

```{=html}
<!-- -->
```
-   Clean table layout replacing legacy list-group view

### UI Improvements

-   Tabs + search + table unified into a **single white card panel**

-   Background image preserved for brand aesthetic

-   Resolved transparency issues by:

    -   Correcting invalid CSS nesting

    -   Moving UI elements into card containers instead of fighting
        background styles

## ��️ Technical Fixes & Learnings

-   Fixed `KeyError: 0` by aligning count query with dict-based cursor
    output.

-   Removed incorrect references to non-existent `contact_type` column.

-   Updated all templates to use dict-style access (`c["field"]`).

-   Identified and corrected invalid CSS caused by rules accidentally
    nested inside `body ``{``}`.

-   Confirmed that visual bugs were structural, not CSS specificity
    issues.

## �� Workflow & Version Control

-   Changes developed and tested **locally on MacBook**.

-   Successfully pushed to GitHub.

-   Clean **fast-forward `git pull`** on iMac confirmed:

    -   No conflicts

    -   All new templates and CSVs synced

```{=html}
<!-- -->
```
-   Reinforced Git as the authoritative sync mechanism across machines.

## �� Deferred / Explicitly Not Done

-   No sorting controls added yet (A--Z, recent activity).

-   No AJAX or live filtering (page reloads only).

-   No schema changes or migrations.

-   No changes to Professionals module.

-   No UI refactor of buyer/seller action buttons yet.

## �� Outcome

The Contacts page now:

-   Scales cleanly with large datasets

-   Maintains existing workflows

-   Uses consistent UI patterns

-   Is easier to navigate and reason about

-   Respects the long-term architecture of Ulysses CRM

This marks a **significant usability milestone** without advancing the
formal version number, and sets the stage for future enhancements like
sorting, saved views, and activity-based prioritization.

## Ulysses CRM -- Contacts UI & Workflow Enhancement

**December 11, 2025**

**Session Summary (Local → Production Ready)**

### Primary Goals

-   Improve usability and visual clarity of the **Contacts** page.

-   Reduce clutter while keeping full data capture intact.

-   Resolve newly introduced backend errors without regressions.

-   Align Contacts page UX with the rest of the application's page
    structure.

## Key Decisions & Outcomes

### 1. Contacts Page UX Refinement

-   **Add New Contact** was moved out of the main page flow and into a
    **Bootstrap modal**.

-   Decision was made explicitly to ensure:

    -   Zero backend or database changes

    -   Full reversibility (modal → tab → inline card)

```{=html}
<!-- -->
```
-   A persistent **"+ Add New Contact"** button was added to the page
    header.

**Design principle reinforced:**

Reduce visual noise while keeping high-frequency actions always
accessible.

### 2. Unified Page Heading Pattern

-   Contacts page was updated to match the heading structure used
    elsewhere:

    -   Primary page title

    -   Contextual subtitle that changes based on the active tab (All,
        Buyers, Sellers, Leads, Past Clients)

```{=html}
<!-- -->
```
-   Removed redundant headers and nested containers.

-   Ensured consistency with `base.html` container usage.

**Design principle reinforced:**

One clear page identity per view; no duplicate titles or containers.

### 3. Modal Form Enhancements

The Add Contact modal includes:

-   Full parity with the previous inline form.

-   Address fields.

-   Follow-up scheduling.

-   Notes.

-   All existing select lists (lead type, pipeline stage, priority,
    source).

**UX refinements added:**

-   "Follow Up Hour / Minute" labels simplified to **Hour / Minute**.

-   Follow-up fields grouped more tightly for visual clarity.

-   Modal size set to `modal-lg` with scroll support.

**Deferred but discussed enhancements:**

-   Auto-hide follow-up time unless a date is selected.

-   Additional micro-polish such as borders or section headers inside
    modal.

### 4. Pagination Update

-   Contacts list pagination was standardized to **10 contacts per
    page** across all tabs.

-   Pagination logic remained unchanged structurally, only the per-page
    limit was adjusted.

**Design principle reinforced:**

Favor faster scanning and reduced vertical density.

### 5. Backend Error Resolution (Add Contact)

Several backend errors surfaced during testing and were resolved:

#### Fixed:

-   `parse_follow_up_time_from_form` missing definition.

-   `parse_int_or_none` missing helper.

-   Ensured helper functions were defined **above route usage**.

Confirmed:

-   Contact creation works with partial or full form completion.

-   Follow-up fields safely return `None` when incomplete.

### 6. Follow-Up Dashboard Regression Fix

-   Encountered error:\
    `TypeError: 'function' object is not subscriptable`

-   Root cause: naming collision between a function and a variable
    (`buyer_profile`).

-   Resolved without impacting Seller workflows.

**Key validation:**

-   Seller functionality was confirmed unaffected before applying the
    fix.

### 7. Template Hygiene Improvements

-   Corrected Jinja quoting issues (e.g., `c['id']` vs `c["id"]`).

-   Removed redundant containers inside templates already wrapped by
    `base.html`.

-   Ensured modal markup lives inside {`% block content %``}` only.

## Phase / Version Context

-   No formal version bump declared in this session.

-   Changes are **UI/UX and stability improvements**, not
    schema-altering.

-   Safe for immediate production deployment.

-   All changes tested locally before live deployment.

## State at End of Session

-   Contacts modal fully functional.

-   Add Contact workflow stable.

-   Follow-up dashboard restored.

-   UI consistent across major sections.

-   Ready for Render production deploy from iMac environment.

## Ulysses CRM --- Development Session Summary

**December 12, 2025**

**Focus:** Environment sync, Contacts UI cleanup, and header alignment
refinement

### Goals

-   Re-sync development work performed on the iMac to the MacBook
    cleanly and safely.

-   Restore local development environment on the MacBook (virtual
    environment).

-   Remove legacy UI artifacts left behind after recent Contacts modal
    refactor.

-   Visually align the Contacts page header and primary action button
    with the table for consistency and clarity.

### Key Actions and Decisions

#### 1. Environment Sync and Recovery

-   Successfully pulled latest changes from `origin/main` on the MacBook
    using a fast-forward merge.

-   Confirmed updated files included `app.py` and
    `templates/contacts.html`.

-   Identified that the MacBook did not yet have a local Python virtual
    environment.

-   Created a new `.venv` locally, activated it, and reinstalled
    dependencies via `requirements.txt`.

-   Reinforced the principle that virtual environments are
    machine-specific and intentionally excluded from Git.

#### 2. Contacts Page UI Cleanup

-   Identified a **duplicate Contacts header** and legacy descriptive
    text ("Manage and filter all of your people") left over from a
    pre-modal layout.

-   Determined that the **new dynamic header** tied to tab state (All,
    Buyers, Sellers, etc.) was correct and should be preserved.

-   Removed the obsolete secondary header block entirely.

-   Retained the "Add New Contact" button but re-positioned it
    independently of the legacy heading.

#### 3. Header and Button Alignment Refinement

-   Observed that the Contacts header and Add New Contact button felt
    visually disconnected from the table.

-   Chose the **recommended approach**:

    -   Move the header inside the same container as the tabs and table.

    -   Use a single flex row to align:

        -   Contacts heading and dynamic sub-label on the left

        -   Add New Contact button on the right

```{=html}
<!-- -->
```
-   Implemented a clean, minimal flex layout immediately above the tabs
    for better hierarchy and proximity to data.

-   Upgraded the heading from `h4` to `h2` to maintain consistency with
    other primary pages (Dashboard, Professionals, etc.).

### Design Principles Reinforced

-   **Single source of truth for page headers**: eliminate duplicate or
    legacy UI elements after refactors.

-   **Visual hierarchy over absolute positioning**: headers and actions
    should belong to the data they control.

-   **Consistency across core pages**: shared header patterns and
    heading levels improve app coherence.

-   **Local safety first**: environment setup and Git operations should
    always favor non-destructive, reversible steps.

### Features Added or Modified

-   No new features introduced.

-   Contacts page UI refined:

    -   Removed legacy descriptive text.

    -   Unified header and action button.

    -   Improved spacing and visual alignment with tabs and table.

### Features Deferred

-   Global standardization of this header pattern across Buyers,
    Sellers, and Professionals (not yet applied, but identified as a
    logical next step).

### Phase / Version Context

-   This work represents **incremental UI polish and cleanup** following
    recent Contacts modal and tab updates.

-   No formal phase transition or version bump occurred during this
    session.

-   Changes are consistent with late-Phase 4 / early-Phase 5 UI
    stabilization and refinement work.

## Ulysses CRM --- Local Development Transition & Contact UI Refinement

**December 13, 2025**

**Session Summary (Canonical Record)**

### Primary Goals

-   Establish **reliable local machine development** on both iMac and
    MacBook

-   Eliminate confusion between local vs production environments

-   Refine **Contact → Interactions → Follow-ups** architecture and UI
    logic

-   Improve development workflow confidence and repeatability

## Key Decisions & Outcomes

### 1. Local Development Successfully Established (Both Machines)

**Decision**

-   Fully shift to **local-first development** using `.env`
    configuration files and local Postgres

-   Stop relying on production (Render) for routine development and
    testing

**Outcome**

-   `.env` files confirmed and synced correctly across iMac and MacBook

-   Hidden file visibility resolved on macOS

-   Virtual environments (`venv`) correctly activated

-   Python execution standardized on `python3`

-   Both machines now run **independent, fully functional local
    instances** of Ulysses CRM

**Design Principle Reinforced**

Local development is the authoritative workspace. Production is
deployment-only.

### 2. Environment & Tooling Hardening

**Decisions**

-   Add shell conveniences and guardrails:

    -   Aliases and PATH consistency via `.zshrc`

    -   Explicit use of `python3`

```{=html}
<!-- -->
```
-   Fix broken or malformed `.zshrc` entries

-   Install missing dependencies (`python-dotenv`, etc.)

**Outcome**

-   Stable, predictable startup flow

-   Reduced friction switching between machines

-   Clear distinction between:

    -   running server

    -   editing files

    -   observing logs

**Design Principle Reinforced**

Reduce cognitive load. The environment should be boring and predictable.

### 3. Edit Contact UI: "Last Contacted" Field Removed (Correctly)

**Initial Issue**

-   "Last Contacted" field persisted despite removal from
    `edit_contact.html`

**Root Cause Identified**

-   App was being run with `python` instead of `python3`

-   Template changes were correct; runtime was not

**Final Resolution**

-   Confirmed removal once correct interpreter was used

-   Verified that template edits are reflected immediately in local dev

**Design Principle Reinforced**

Always trust the code first. Then verify the runtime.

### 4. Strategic Shift: Follow-Ups Driven by Interactions

**Decisions**

-   Dashboard follow-ups should be **derived from interactions**, not
    static fields

-   Interactions become the **source of truth** for:

    -   current

    -   upcoming

    -   overdue activity

```{=html}
<!-- -->
```
-   Dashboard will evolve into a **unified activity/status table**

-   Contact-level fields:

    -   "Last Contacted"

    -   "Next Follow Up"

are candidates to:

-   either be auto-derived from interactions

-   or eventually removed to prevent duplication

**Status**

-   Architectural direction agreed

-   Implementation intentionally deferred to avoid rushed refactors

**Design Principle Reinforced**

One source of truth. No duplicated state.

### 5. Dashboard Evolution (Planned)

**Agreed Direction**

-   Dashboard will become a **cohesive operational surface**

-   Follow-ups, interactions, and future modules will live together

-   Status-based grouping:

    -   overdue

    -   today

    -   upcoming

    -   completed (historical)

**Status**

-   Design intent captured

-   No schema or UI changes committed yet

### 6. Remote Development Capability Identified (Future Enablement)

**Discovery**

-   NordVPN alone does not allow device-to-device access

-   NordVPN **Meshnet** enables secure peer-to-peer access between
    machines

**Potential Use**

-   Remote SSH from laptop to home iMac

-   Run CRM on iMac, work from laptop

-   Secure, no port-forwarding solution

**Status**

-   Not yet implemented

-   Marked as optional future enhancement

## Features Explicitly Deferred

-   Dashboard follow-up refactor

-   Removal or automation of contact follow-up fields

-   Meshnet-based remote dev workflow

-   Any production deployment changes

## Phase / Version Context

-   Work occurred during **v0.10.x → Phase 4.5 local-first development**

-   No schema migrations introduced

-   No production changes made

-   This session solidified **development discipline**, not feature
    scope

## Lasting Impact

-   Developer confidence significantly improved

-   Clear mental model established:

    -   edit → reload → verify locally

```{=html}
<!-- -->
```
-   Foundation laid for cleaner interaction-driven workflows

-   Reinforced rule: **local first, production last**

# CRM Project -- Historical & Project-Evolution Summary

**Date:** December 13, 2025

## Overview & Goals

The goal of this session was to **restore, standardize, and validate
Dennis's local development environment across machines**, specifically
focusing on:

-   Safely syncing code between GitHub, Render, iMac, and MacBook

-   Confirming which shell shortcuts (aliases/functions) existed

-   Resolving folder-name inconsistencies between machines

-   Ensuring a clean, repeatable one-command workflow for Ulysses CRM
    development

This session reinforced the principle that **environment consistency is
as critical as code correctness** for long-term project stability.

## Key Decisions Made

### 1. GitHub as the Single Source of Truth

-   Confirmed that **Render deploys only from GitHub**, not from local
    machines.

-   Established that syncing should always flow:

    -   *Active machine → GitHub → Other machine*

```{=html}
<!-- -->
```
-   Successfully fast-forwarded the iMac to match GitHub with no
    conflicts.

**Design principle reinforced:**

Never assume Render has newer code than GitHub. GitHub is canonical.

### 2. Validation of Existing Shell Shortcuts

Confirmed that the simplifying commands created earlier in the **"Email
Integration in Ulysses"** chat were indeed present on the iMac.

Installed and verified:

-   `runcrm` -- one-command CRM startup

-   `crmtest` -- dev/test run shortcut

-   `crmpull` -- one-command Git pull

-   `crmpush "message"` -- commit + push via a shell function

Key clarification:

-   `crmpush` is a **zsh function**, not an alias, so it does **not**
    appear in `alias | grep crm`. This was validated and confirmed
    working.

### 3. Folder Name Standardization

Discovered that the CRM project folder had **different names and
locations** across machines.

On the iMac:

-   Actual location identified as

## Ulysses CRM --- Domain Configuration & Canonical URL Decision

**Date:** December 13, 2025

### Goals

-   Transition Ulysses CRM from a Render-provided `.onrender.com` URL to
    a branded production domain.

-   Ensure a stable, secure, and canonical access point for the CRM.

-   Avoid session, CSRF, and cookie issues associated with multi-domain
    serving.

### Key Decisions

1.  **Primary Domain Established**

    -   `https://ulyssescrmpro.com` selected as the single canonical
        production URL for the CRM.

    -   Both root and `www` subdomain were successfully verified in
        Render and issued SSL certificates.

```{=html}
<!-- -->
```
1.  **Render DNS Configuration**

    -   Followed Render's updated instructions:

        -   Root domain (`@`) uses an **A record** pointing to Render's
            specified IP.

        -   `www` subdomain uses a **CNAME** pointing to the Render
            service URL.

    ```{=html}
    <!-- -->
    ```
    -   TTL set to **300 seconds** to allow fast propagation and easy
        correction during setup.

```{=html}
<!-- -->
```
1.  **SERVER_NAME Explicitly Not Used**

    -   Confirmed via codebase search and environment inspection that
        `SERVER_NAME` is **not set** in:

        -   `app.py`

        -   Any project files

        -   Render environment variables

    ```{=html}
    <!-- -->
    ```
    -   Decision reinforced to rely on Render's host handling rather
        than Flask-level domain enforcement.

```{=html}
<!-- -->
```
1.  **Secondary Domain Strategy**

    -   `ulyssescrm.pro` designated as a **redirect-only domain**, not
        an app-serving domain.

    -   Decision made to implement a **301 redirect at the registrar
        (GoDaddy)**:

        -   `ulyssescrm.pro` → `https://ulyssescrmpro.com`

        -   `www.ulyssescrm.pro` → `https://ulyssescrmpro.com`

    ```{=html}
    <!-- -->
    ```
    -   Explicitly avoided serving the app on multiple domains to
        prevent auth and session instability.

### Design Principles Reinforced

-   **Single Canonical URL**: One authoritative domain for app access to
    ensure clean sessions and future scalability.

-   **Infrastructure over App Logic**: Prefer DNS and platform-level
    solutions (Render, registrar redirects) over Flask configuration
    when appropriate.

-   **Stability First**: Avoid unnecessary complexity during production
    hardening.

-   **Future-Proofing**: Decisions made with future features in mind
    (email links, password resets, potential landing pages).

### Features Added / Deferred

-   **Added**

    -   Branded production domain with SSL.

    -   Registrar-level redirect strategy for alternate domains.

```{=html}
<!-- -->
```
-   **Deferred**

    -   Canonical-host enforcement in Flask.

    -   Locking down direct `.onrender.com` access.

    -   Landing page or marketing site on root domain.

    -   Email domain setup and outbound email features.

### Phase / Version Context

-   This work represents **production hardening and branding**, not a
    functional feature release.

-   No version number change triggered by this work.

-   Establishes a stable foundation for post--v1.0 features such as
    email workflows, multi-user access, and public-facing pages.

### Outcome

Ulysses CRM now operates under a professional, branded, HTTPS-secured
domain with a clean redirect strategy for alternate domains. The system
remains stable, unmodified at the Flask level, and well-positioned for
future expansion.

## Ulysses CRM --- Seller Profile & Listing Checklist Evolution

**Date:** December 13, 2025

### 1. Primary Goals

-   Introduce a **Seller Profile tab structure** that is scalable,
    readable, and consistent with the existing Contacts UI.

-   Implement a **New Listing Checklist** with:

    -   Per-item completion tracking

    -   Due dates

    -   Overdue visual cues

    -   In-place editing via modal

```{=html}
<!-- -->
```
-   Ensure checklist updates do **not interrupt workflow** (no page
    reloads, modal stays open).

-   Maintain visual clarity when using a **full-page background image**.

-   Preserve architectural separation between:

    -   Seller editable fields

    -   Checklist state and automation

    -   Contact-level navigation

### 2. Key Features Implemented

#### Seller Profile Tab Architecture

-   Introduced a **multi-tab Seller Profile**:

    -   Overview

    -   Professionals

    -   Notes

    -   Checklist

```{=html}
<!-- -->
```
-   Tabs persist their active state using `localStorage`.

-   Seller form fields are wrapped in a single form; checklist is
    intentionally **outside the form** to prevent unintended submits.

-   Professionals selection wired to auto-populate name, phone, and
    email fields from the Professionals table.

#### Listing Checklist System

-   Checklist stored in `listing_checklist_items` table with:

    -   `is_complete`

    -   `due_date`

    -   `completed_at`

```{=html}
<!-- -->
```
-   Checklist auto-initializes per seller via
    `ensure_listing_checklist_initialized(contact_id)`.

-   Checklist displayed in two contexts:

    -   **Read-only summary table** in the Checklist tab

    -   **Editable modal** for checking items and assigning due dates

```{=html}
<!-- -->
```
-   Updates occur via AJAX POST to:

-   `/api/listing-checklist/<item_id>/update`

-   Modal remains open while editing; visual "Saved" feedback provided
    per item.

-   Overdue items highlighted when `due_date < today` and not complete.

### 3. UI / UX Decisions & Lessons Learned

#### Consistency as a Design Principle

-   Decision reinforced to keep **Seller Profile UI consistent with
    Contacts page**:

    -   Header row with title + context

    -   Single card container

    -   Tabs inside card, not floating independently

```{=html}
<!-- -->
```
-   This consistency reduces cognitive load and prevents layout drift.

#### Background Image Interaction

-   Issue identified where tables and headers appeared transparent due
    to background image.

-   Root cause: CSS overrides applied only to `.contacts-table`.

-   Resolution path clarified:

    -   Tables must explicitly opt into solid backgrounds
        (`contacts-table`) **or**

    -   A global Bootstrap table background override should be applied
        later.

```{=html}
<!-- -->
```
-   Avoided fragile wrapper restructuring that caused layout breakage.

#### Safe Styling Changes Rule

-   Established a working rule:

Avoid changing structural wrappers (div nesting) unless absolutely
necessary.\
Prefer styling changes *inside* existing containers.

This prevented repeated regressions during header background
experiments.

### 4. Technical Corrections & Clarifications

-   Confirmed that **date comparisons in Jinja** must use `date`
    objects, not ISO strings.

-   Seller Profile render updated to pass:

-   `today = date.today()`

-   Acknowledged that `edit_contact.html` still uses `isoformat()`
    intentionally and does not participate in checklist logic.

### 5. Deployment & Versioning

-   Changes committed and pushed to `main`.

-   Render deployment completed successfully.

-   Commit message (noted for history):

Seller profile tab structure with checklist modal and due-date logic

### 6. Features Explicitly Deferred

-   Global table background refactor (site-wide CSS standardization)

-   Daily digest / checklist summary notifications

-   Sticky tab navigation

-   Seller status strip (Active / Under Contract / Closed)

-   Buyer Profile tab parity (acknowledged as next logical extension)

These were intentionally deferred to keep scope controlled and avoid
destabilizing the UI.

### 7. Design Principles Reinforced

-   **Consistency over novelty**: Match existing patterns before
    inventing new ones.

-   **Separation of concerns**:

    -   Forms vs. automation

    -   Display vs. edit

```{=html}
<!-- -->
```
-   **Non-interruptive workflows**: Modals and AJAX updates should never
    reset user context.

-   **Incremental refinement**: Visual polish should never come at the
    cost of structural stability.

### 8. Phase Context

This work represents a **mid-Phase evolution** toward a more modular,
CRM-grade interface, laying groundwork for:

-   Buyer/Seller dual-role contacts

-   Checklist-driven automation

-   Future reporting and digest features

No formal version bump occurred, but this materially advances the Seller
Profile feature set toward v1.0 readiness.

**Ulysses CRM -- Project Evolution Summary**\
**Date:** December 14, 2025

### Overall Goals

-   Refine the **Edit Contact** and **Seller Profile** user experience
    to reduce redundancy, improve clarity, and maintain user context.

-   Introduce **Special Dates** (birthdays, anniversaries, other key
    dates) as first-class CRM data tied to contacts.

-   Ensure save actions behave intuitively by keeping users on the page
    they are working on unless they explicitly choose to navigate away.

-   Maintain production stability while iterating on UI and data model
    enhancements.

### Key UI / UX Decisions

1.  **Edit Contact Header Standardization**

    -   Replaced the card header ("Edit Contact") with a consistent
        page-level header:

        -   Primary heading: *Contacts*

        -   Subhead dynamically reflecting the current contact's name,
            email, and phone.

    ```{=html}
    <!-- -->
    ```
    -   Reinforced the principle that **page headers provide context**,
        while cards should focus on content, not repeat the page title.

```{=html}
<!-- -->
```
1.  **Engagement Log Action Alignment**

    -   Action buttons (Complete / Edit / Delete) were reworked using
        flex containers inside `<td>` elements.

    -   Header `<th>` alignment left unchanged or optionally matched for
        visual consistency.

    -   Established a pattern: **alignment logic belongs in table cells,
        not headers**.

```{=html}
<!-- -->
```
1.  **Seller Profile Save Behavior**

    -   Confirmed that:

        -   Saving the Seller Profile should **remain on the Seller
            Profile page**.

        -   Navigation back to the Contact page should be explicit via a
            "Back to Contact" button.

    ```{=html}
    <!-- -->
    ```
    -   Header-level "Save and Back" buttons were deemed redundant and
        removed.

    -   Reinforced a UX rule: **saving should not imply navigation
        unless the user requests it**.

### New Feature Added: Special Dates

-   Added a new database table: `contact_special_dates`.

    -   Fields include label, date, recurring flag, notes, and contact
        association.

```{=html}
<!-- -->
```
-   Implemented:

    -   Backend loading of special dates in `edit_contact`.

    -   Frontend UI section within the Contact page to:

        -   Add birthdays, anniversaries, or custom dates.

        -   View and delete existing special dates.

```{=html}
<!-- -->
```
-   Design decision:

    -   Keep Special Dates **contact-centric**, not seller- or
        buyer-specific.

    -   Support future automation (e.g., reminders, campaigns) without
        over-engineering now.

### Backend / Code Decisions & Fixes

1.  **Render Deployment Errors Resolved**

    -   Fixed
        `SyntaxError: positional argument follows keyword argument`
        caused by a malformed `render_template` call.

    -   Fixed `SyntaxError: 'return' outside function` due to incorrect
        indentation.

    -   Fixed `NameError: c is not defined` by standardizing on:

    -   `c = contact`

and passing `c=contact` consistently to templates.

1.  **Contact Data Access Consistency**

    -   Confirmed the use of `RealDictCursor`, enabling safe `.get()`
        access.

    -   Hardened follow-up time parsing with:

    -   `t_str = contact.get("next_follow_up_time") if contact else None`

    -   Reinforced the rule: **never remove the primary contact SELECT
        query**; downstream logic depends on it.

```{=html}
<!-- -->
```
1.  **Redirect Scope Discipline**

    -   Acknowledged many handlers redirect to `edit_contact` by
        default.

    -   Decision made to **scope redirect changes incrementally**,
        starting only with Seller Profile behavior, to avoid cascading
        regressions.

    -   Broader redirect refactor deferred intentionally.

### Design Principles Reinforced

-   **Context Persistence:** Users should stay where they are working
    unless they choose otherwise.

-   **Single Source of Truth:** Use one canonical variable (`contact`)
    and pass it consistently (`c=contact`) to templates.

-   **UI Consistency:** Headers, actions, and card usage should follow
    the same mental model across Contacts, Buyers, and Sellers.

-   **Incremental Change Over Refactors:** Fix narrowly, deploy safely,
    then expand.

### Phase / Version Context

-   This work occurred post-v0.10.x, during ongoing UI and data-model
    refinement leading toward v1.0 readiness.

-   Special Dates introduced as a foundational feature, with automation
    and reminders intentionally deferred to a later phase.

**Status at End of Session**

-   Application successfully redeployed and live.

-   Seller Profile and Edit Contact flows stabilized.

-   Special Dates feature fully wired end-to-end.

-   Clear next steps identified without expanding scope prematurely.

## Ulysses CRM --- Open House Sign-In System

**Date:** December 15, 2025

### High-Level Goal

Design, implement, and deploy a **stand-alone, branded Open House
sign-in experience** that:

-   Captures structured visitor data

-   Integrates cleanly into Ulysses CRM

-   Operates independently of the internal CRM UI

-   Is suitable for real-world open house use (tablet, phone, QR code)

## Core Features Implemented

### 1. Public Open House Sign-In Page

-   Created a **public-facing sign-in route** accessed via a secure
    tokenized URL (`/openhouse/<token>`).

-   Page operates independently of CRM authentication.

-   Fully functional GET/POST lifecycle with validation, persistence,
    and feedback.

### 2. CRM Integration

Captured data is written directly into Ulysses CRM:

-   Contacts table (match or create logic)

-   Open house sign-ins table

-   Fields captured:

    -   First name, last name

    -   Email, phone

    -   Working with agent (yes/no)

    -   Agent name, phone, brokerage

    -   Buyer/seller intent flags

    -   Timeline

    -   Notes

    -   Consent to contact

```{=html}
<!-- -->
```
-   Contact records are tagged with:

    -   Lead source = "Open House"

    -   Last open house ID

### 3. Agent Relationship Enforcement

-   **Key business rule enforced**:

    -   If "Working with an agent = Yes," **Agent Name is required**

```{=html}
<!-- -->
```
-   Implemented at both levels:

    -   Client-side (HTML + JavaScript required toggle)

    -   Server-side (Flask validation with flash messaging)

## Branding & UX Decisions

### Stand-Alone Design Principle (Reinforced)

-   Public sign-in pages must **not inherit CRM navigation or chrome**.

-   Achieved by:

    -   Introducing `hide_nav` render context variable

    -   Conditionally suppressing navbar in `base.html`

    -   Passing `hide_nav=True` explicitly from Flask routes

```{=html}
<!-- -->
```
-   CSS hiding was deliberately avoided in favor of render-time control.

### Visual Design Choices

-   Background:

    -   Public sign-in pages use a **pure white background**

    -   Internal CRM pages retain existing branded background image

```{=html}
<!-- -->
```
-   Branding:

    -   Custom open house logo added (top-left)

    -   Logo scaled responsively (final width: \~300px)

```{=html}
<!-- -->
```
-   Form Presentation:

    -   Form panel styled with a subtle neutral gray (Sotheby's gray
        tone)

    -   Clear contrast between background and form elements

```{=html}
<!-- -->
```
-   Layout:

    -   House photo displayed **inline to the right** of the "Open House
        Sign In" heading

    -   Image constrained to \~200px width for balance and readability

### Privacy & Compliance

-   Dedicated **Open House--specific Privacy Policy** introduced

-   Linked directly from the public sign-in page

-   Designed for future legal/compliance refinement

## Technical & Architectural Decisions

### Template Architecture

-   Continued use of a **single shared `base.html`**

-   Public vs. private behavior controlled via:

    -   Explicit context variables (`hide_nav`)

    -   Body class (`openhouse-public`)

```{=html}
<!-- -->
```
-   Avoided template duplication or secondary base templates

### Database & Persistence

-   Confirmed correct use of:

    -   Connection lifecycle management (`conn.close()` on all paths)

    -   Safe contact matching (email first, phone fallback)

```{=html}
<!-- -->
```
-   CSV export capability agreed to and scoped, but deferred to a later
    step

### Error Handling & Stability

-   Identified and resolved:

    -   Jinja misuse (`block()` not valid as a function)

    -   Python indentation errors causing Gunicorn boot failure

```{=html}
<!-- -->
```
-   Reinforced discipline around:

    -   Indentation integrity

    -   Local compile checks (`py_compile`) before deploy

    -   Explicit handling of early returns in POST flows

## Deployment & Environment Notes

-   All work deployed successfully to Render

-   Confirmed behavior in Safari after cache hiccup

-   Gunicorn restarts observed were normal deployment behavior

-   Static asset serving confirmed for branding assets

## Features Explicitly Deferred

-   PDF / print-optimized sign-in sheet

-   Enhanced CSV export formatting

-   Thank-you / confirmation screen post-submit

-   Advanced analytics or reporting on open house traffic

-   Per-agent branding overrides (future enhancement)

## Design Principles Reinforced

1.  **Public ≠ Internal**

    -   Public-facing pages must be isolated from internal CRM UI and
        assumptions.

```{=html}
<!-- -->
```
1.  **Server-Side Authority**

    -   Client-side validation improves UX, but server-side rules are
        authoritative.

```{=html}
<!-- -->
```
1.  **Minimal Invasiveness**

    -   New features should not destabilize existing templates or
        workflows.

```{=html}
<!-- -->
```
1.  **Real-World First**

    -   UX decisions optimized for actual open house usage, not abstract
        forms.

## Phase Context

This work fits cleanly into:

-   **Phase 6 (Client Interaction & Lead Capture Enhancements)**\
    and establishes a strong foundation for:

-   Phase 6.5 (Exports, Print, Compliance)

-   Phase 7 (Client Experience & Automation)

**Project Evolution Summary -- Open House Privacy & UX Enhancements**\
**Date:** December 15, 2025

### Goal

The primary goal of this work session was to professionalize and harden
the **public Open House Sign-In experience** within Ulysses CRM by:

-   Ensuring legal compliance (privacy, trademark, Fair Housing,
    non-solicitation)

-   Preserving Sotheby's-only branding with no Ulysses exposure

-   Improving visitor UX across phone, tablet, and laptop

-   Avoiding friction or data loss during the sign-in process

This work was explicitly scoped to **public-facing open house flows
only**, not authenticated CRM pages.

### Key Decisions & Outcomes

#### 1. Separate Open House Privacy Page

-   Created a dedicated public route:\
    `/openhouse-privacy`

-   Implemented as a standalone page rendered from:\
    `templates/public/openhouse_privacy.html`

-   Privacy content is **open-house-specific**, not a generic site
    policy.

**Design principle reinforced:**\
Legal clarity should be contextual and purpose-built, not reused blindly
across unrelated user flows.

#### 2. Brand & Layout Consistency

-   Privacy page was reworked to **exactly match the open house sign-in
    page layout**, including:

    -   Same logo placement

    -   Same max-width container

    -   Same horizontal rule divider

    -   Same gray content panel styling

```{=html}
<!-- -->
```
-   Achieved by explicitly setting:

-   `{``% block body_class %``}``openhouse-public``{``% endblock %``}`

-   This resolved an issue where the privacy page was unintentionally
    inheriting the global "house background image" instead of the white
    open house background.

**Design principle reinforced:**\
Public-facing pages that are part of a single workflow must feel
visually continuous, even when technically separate routes.

#### 3. Footer Legal Enhancements on Sign-In Page

-   Retained the existing **Privacy Notice link** in the sign-in footer.

-   Added a **visible Sotheby's trademark, Fair Housing, and
    non-solicitation disclosure** directly below the link.

-   Disclosure is always visible to visitors and not hidden behind
    navigation.

**Compliance decision:**\
Trademark and Fair Housing disclosures should be visible at the point of
data collection, not buried in linked documents.

#### 4. Bidirectional Navigation Between Pages

-   Implemented a clean return path:

    -   Privacy page includes a **"Back to Open House Sign-In"** button.

    -   The button returns the user to the *exact* open house they came
        from.

```{=html}
<!-- -->
```
-   Achieved by:

    -   Passing `return=request.path` from the sign-in page to the
        privacy page.

    -   Reading that value in the privacy route and conditionally
        rendering the back button.

**UX principle reinforced:**\
Users should never be forced to rely on browser back buttons in
transactional flows.

#### 5. Form State Persistence (Major UX Improvement)

-   Implemented **sessionStorage-based draft persistence** for the open
    house sign-in form.

-   Behavior:

    -   If a visitor partially completes the form

    -   Clicks the Privacy Notice link

    -   Then returns to the sign-in page\
        → All previously entered fields are restored automatically.

```{=html}
<!-- -->
```
-   Draft is cleared only upon successful form submission.

**Key technical choices:**

-   Client-side only (no DB writes, no auth required)

-   Scoped per open house using `window.location.pathname`

-   Works consistently on mobile Safari, tablets, and desktops

**Design principle reinforced:**\
Public UX should be forgiving and resilient. Users should never lose
work due to reasonable navigation.

### Features Explicitly Deferred

-   Modal-based privacy display (kept navigation-based approach for
    simplicity and legal clarity)

-   Server-side draft persistence

-   Multi-step or wizard-style sign-in flows

These were consciously deferred to keep the open house flow fast,
robust, and low-risk.

### Architectural & Governance Notes

-   No Ulysses branding is exposed anywhere in the public open house
    flow.

-   Privacy, branding, and disclosure decisions are aligned with
    Sotheby's franchise expectations.

-   Open house public routes remain isolated from authenticated CRM
    functionality.

-   Changes are safe, additive, and do not alter existing data models.

### Status

-   **Complete**

-   Deployed to production

-   Verified on phone, tablet, and desktop

-   Ready for reuse across all future open houses

This session meaningfully elevated the professionalism, compliance
posture, and usability of the open house experience and established a
strong pattern for future public-facing workflows within Ulysses CRM.

**Ulysses CRM -- Feature Evolution Summary: "Add User"**\
**Date:** December 18, 2025

### Goal

The primary goal of this work session was to transition Ulysses CRM from
a single, hard-coded admin login to a **database-backed user
authentication system** that supports future multi-user expansion, while
keeping the current scope intentionally minimal and safe for production.

### Core Decisions & Rationale

1.  **Replace session-based admin auth with Flask-Login**

    -   Retired the legacy `ADMIN_USERNAME / ADMIN_PASSWORD`
        environment-based login and `session["logged_in"]` logic.

    -   Adopted Flask-Login as the single source of truth for
        authentication.

    -   Ensured all route protection relies on `@login_required` and
        `current_user`.

```{=html}
<!-- -->
```
1.  **Introduce a `users` table (single user, multi-user ready)**

    -   Created a proper `users` table with:

        -   `id`, `email`, `password_hash`

        -   optional profile fields

        -   `role`, `is_active`

        -   timestamps including `last_login_at`

    ```{=html}
    <!-- -->
    ```
    -   Established the pattern that all future data will be scoped by
        `user_id`.

```{=html}
<!-- -->
```
1.  **Create a local-only admin utility (`create_user.py`)**

    -   Implemented a one-time script to create users securely using
        password hashing.

    -   Explicitly decided **not** to expose user creation via any web
        UI.

    -   Designated this script as **local-only**, ignored via
        `.gitignore`, and excluded from production builds.

    -   Reinforced a security principle: administrative actions should
        be deliberate and non-public.

```{=html}
<!-- -->
```
1.  **Standardize password hashing**

    -   Explicitly set Werkzeug hashing to `pbkdf2:sha256` to ensure
        compatibility with the existing Python environment.

    -   Avoided newer defaults (e.g., `scrypt`) that caused runtime
        incompatibilities.

```{=html}
<!-- -->
```
1.  **Clean separation of concerns**

    -   Removed all custom auth decorators that conflicted with
        Flask-Login.

    -   Centralized auth behavior in:

        -   `LoginManager`

        -   `User` model

        -   `user_loader`

    ```{=html}
    <!-- -->
    ```
    -   Ensured templates rely on `current_user` instead of session
        flags.

### UI / UX Updates

-   Added a visible **Logout** control to the main navigation.

-   Used `current_user.is_authenticated` in templates for conditional
    display.

-   Resolved a template caching issue by restarting the Flask server,
    reinforcing the need to restart during template debugging.

-   Confirmed correct redirect behavior:

    -   Unauthenticated users → `/login?next=...`

    -   Successful login → intended destination

    -   Logout → `/login`

### Infrastructure & Workflow Improvements

-   **Local Postgres startup standardized**

    -   Created a reusable shell script to reliably start the correct
        Postgres version.

    -   Eliminated repeated environment friction during local
        development.

```{=html}
<!-- -->
```
-   **Git safety practices reinforced**

    -   Created and retained a `pre-user-auth` tag as a permanent
        rollback reference.

    -   Performed work on a feature branch (`add-user-auth`) and merged
        cleanly into `main`.

    -   Confirmed clean working tree prior to deployment.

```{=html}
<!-- -->
```
-   **Deployment discipline**

    -   Ensured local sanity checks before pushing to production.

    -   Confirmed Render deployment strategy relies on `main` branch.

    -   Explicitly validated production login behavior post-deploy.

### Design Principles Reinforced

-   **Local-first, production-safe**

    -   All schema and auth changes were tested locally before
        deployment.

    -   No risky shortcuts or live schema experimentation.

```{=html}
<!-- -->
```
-   **No silent magic**

    -   Avoided hidden behaviors, implicit auth, or dual systems.

    -   Ensured one clear path for authentication and authorization.

```{=html}
<!-- -->
```
-   **Future-ready, not overbuilt**

    -   Built only what was needed now (single user).

    -   Laid clean hooks for:

        -   multi-user support

        -   roles

        -   data ownership via `user_id`

    ```{=html}
    <!-- -->
    ```
    -   Deferred UI-based user management intentionally.

```{=html}
<!-- -->
```
-   **Security over convenience**

    -   No web-based user creation.

    -   No committed admin scripts.

    -   Clear separation between development utilities and runtime code.

### Resulting State (End of Session)

-   Ulysses CRM now uses **proper, database-backed authentication**.

-   The system is fully compatible with Flask-Login best practices.

-   A single production user is live and functioning.

-   The codebase is prepared for true multi-user support without
    redesign.

-   A clean historical checkpoint exists for pre-auth rollback or
    comparison.

### Next Logical Phase (Deferred)

-   Add `user_id` ownership columns to core tables:

    -   contacts

    -   buyer_profiles

    -   seller_profiles

    -   professionals

    -   tasks

```{=html}
<!-- -->
```
-   Scope all queries to `current_user.id`.

-   Introduce optional role-based behavior after v1.0.

This session represents a foundational architectural upgrade and marks a
clear transition from "single-admin tool" to "multi-user capable
system."

## Ulysses CRM -- Design Spec & Feature Map

**Date:** December 16, 2025

### Purpose of This Chat

This conversation was explicitly designated as the **official design
document and feature map** for the Ulysses CRM project. It is intended
to remain clean of implementation details and serve as a long-term
reference for product intent, architectural philosophy, and scope
control.

## Goals Established

-   Define a **feature map** (not a build backlog) that captures what
    *belongs* in Ulysses CRM.

-   Establish clear **timing and discipline** around UI consistency and
    polish.

-   Confirm that the introduction of a **Users system** is the correct
    inflection point for future multi-user capabilities.

-   Protect the CRM from scope creep while keeping it extensible.

## Key Decisions

### 1. Feature Map as Canon

-   The feature list discussed is now treated as a **north-star
    reference**, not a queue.

-   Features will be annotated conceptually as:

    -   Concept only

    -   Designed

    -   Implemented

    -   Deferred (intentionally)

```{=html}
<!-- -->
```
-   No feature should be built unless it aligns with this map.

### 2. Separation of Concerns

-   This chat is pinned and preserved as the **design/spec thread**.

-   All implementation work (including user setup) is intentionally
    moved to separate chats.

-   This mirrors real product management discipline and keeps design
    intent clean.

## UI Consistency Strategy

### Decision

UI consistency should **not** be addressed immediately.

### Rationale

-   Core workflows are still settling.

-   Structural changes are ongoing.

-   Premature UI standardization would cause rework.

### Correct Timing for UI Pass

UI consistency should occur when:

1.  Core templates are stable.

2.  No new page types are being introduced.

3.  Minor UI friction has been felt repeatedly.

### Agreed Approach

-   UI consistency will be handled as a **single, intentional phase**,
    not ongoing tweaks.

-   A "UI contract" or rulebook will define layout, spacing, headers,
    buttons, and form behavior.

-   A single pass across all templates will align the UI without
    functional changes.

## User System & Multi-User Readiness

### Key Decision

Adding the first real user (Dennis) is the **correct and intentional
moment** to introduce a `users` table and ownership model.

### Scope (Phase 1)

-   Single-user operation.

-   All records scoped by `user_id`.

-   No teams, roles, or permissions UI yet.

### Design Principle Established

Ownership lives on the record. Access lives in join tables.

This ensures:

-   Clean single-user behavior today.

-   Future support for:

    -   Multiple individual users

    -   User groups

    -   Shared records

    -   Role-based access

```{=html}
<!-- -->
```
-   No schema rewrites later.

### Explicitly Deferred

-   User groups UI

-   Permissions screens

-   Team collaboration workflows

-   Admin dashboards

-   Billing or role complexity

## Architectural & Product Principles Reinforced

-   Build foundations, not premature features.

-   Design for extension without committing to complexity.

-   UI polish follows functional stability.

-   One intentional refactor beats constant micro-adjustments.

-   Design intent is documented, referenced, and protected.

## Phase / Version Context

-   This discussion occurs during the **v0.10.x era**, as the CRM
    transitions from a single-owner tool to a future-ready platform.

-   The addition of the Users system is treated as a **foundational
    milestone**, not a feature expansion.

-   UI consistency is explicitly deferred to a later, named phase.

## Outcome

This chat is now:

-   Officially pinned

-   Treated as the authoritative design spec

-   Referenced for all future "should we build this?" decisions

Implementation work proceeds separately, governed by this document.

## Ulysses CRM --- Development Workflow Stabilization

**Date:** December 18, 2025

### Purpose of This Chat

This session was initiated to diagnose and prevent a recurrence of
confusion that arose during the **New Engagement Table** implementation,
specifically around accidental file deletion (`engagements.py`) and
uncertainty about file existence and ownership within a single
development session.

The broader goal was to **reduce cognitive load**, **eliminate
ambiguity**, and **formalize a safe, repeatable development process**
for Ulysses CRM.

## Key Problem Identified

-   A mismatch occurred between **chat memory** and **actual repository
    state**, leading to:

    -   Deletion of a file created earlier in the same session

    -   Confusion about whether the file had ever existed

```{=html}
<!-- -->
```
-   Root cause: lack of an explicit, shared "source of truth" for repo
    state during live development discussions.

## Major Decisions Made

### 1. Repo State Is the Single Source of Truth

A core design principle was established:

**We trust the repository, not memory and not chat history.**

All architectural and file-level decisions must be anchored to objective
repo output (`git status`, `git branch`, directory listings).

### 2. Explicit Responsibility Split

Responsibilities were clearly divided:

**Developer (Dennis):**

-   Paste objective repo output when starting sessions or after file
    changes

-   Create checkpoint commits before destructive actions

**Assistant (ChatGPT):**

-   Track branch and file state once anchored

-   Refer only to confirmed files and paths

-   Block destructive actions without checkpoints

This eliminated ambiguity around "who should remember what."

### 3. Mandatory Checkpoint Commit Rule

A non-negotiable rule was adopted:

-   Before deleting, moving, or refactoring files, a **checkpoint
    commit** must be created.

-   This guarantees reversibility and removes fear from refactoring.

### 4. Architecture Consistency Rule

A critical architectural safeguard was established:

-   At any given phase, **routes must live in exactly one place**:

    -   Either entirely in `app.py`

    -   Or entirely in a modular route file (e.g.,
        `routes/engagements.py`)

```{=html}
<!-- -->
```
-   Mixed approaches are explicitly disallowed during a phase.

This directly addresses the confusion that arose during the engagement
work.

### 5. Formal Documentation Added

A new documentation artifact was created and committed:

**New file added**

    docs/dev-workflow.md

This document codifies:

-   Session start checklist

-   Checkpoint rules

-   File architecture rules

-   Branch discipline

-   Repo reality checks

-   Experiment isolation

-   Golden "stop and verify" rule

The document was renamed for clarity and committed cleanly to `main`.

## Features Added or Deferred

### Added

-   Development workflow documentation (`docs/dev-workflow.md`)

-   Alias-based session anchoring (`crmstate`)

-   Standardized "Files Changed" declaration block for live work

### Deferred

-   No CRM features were built in this chat

-   Engagement UI and feature-map updates were intentionally deferred
    until workflow stability was achieved

This was a **foundational stabilization session**, not a feature
implementation session.

## Design Principles Reinforced

-   Repo truth over conversational memory

-   Explicit state anchoring before action

-   Minimal cognitive load for the developer

-   Reversible changes as a default posture

-   Written authority over implicit process

## Phase / Version Impact

-   No version bump occurred

-   No schema or feature phase advanced

-   This session serves as **infrastructure hardening** supporting all
    future CRM phases, including:

    -   Engagement UI work

    -   Route modularization

    -   Multi-user expansion

    -   Long-term maintainability

## Outcome

The session successfully eliminated a class of failure related to
file-state ambiguity and established a durable, documented workflow that
will guide all future Ulysses CRM development.

This chat marks the point at which **process discipline became a
first-class artifact** in the project, on par with schema and feature
design.

## Ulysses CRM --- Dashboard Re-Architecture Discussion

**Date:** December 18, 2025

### High-Level Goal

Reevaluate and redesign the Ulysses CRM dashboard to reflect the
system's maturation, shifting it from a basic follow-up reminder surface
to a **context-rich operational hub** grounded in meaningful
relationship data.

### Problems Identified

-   The original dashboard was designed early in the project and now
    **lags behind the data model**.

-   Follow-ups are displayed **without engagement context**, making them
    feel disconnected and low-signal.

-   The dashboard over-emphasizes dates and reminders while
    under-utilizing:

    -   Engagement history

    -   Active relationship state

    -   Buyer/seller intent

```{=html}
<!-- -->
```
-   Significant unused screen real estate exists, indicating structural
    rather than cosmetic issues.

### Key Conceptual Shift

**From "tasks and reminders" → to "relationship awareness and outreach
guidance."**

The dashboard should answer:

-   *Who should I be talking to?*

-   *Why are they active?*

-   *What is the current state of the relationship?*

Rather than:

-   *What dates are overdue?*

### Major Design Decisions

#### 1. Introduce "Active Contacts" as a Root Dashboard Concept

-   "Active" is **derived**, not manually assigned.

-   A contact is considered **Active (v1 definition)** if any are true:

    -   Engagement within the last 30 days

    -   Follow-up due or scheduled

    -   Buyer profile exists

    -   Seller profile exists

```{=html}
<!-- -->
```
-   Each active contact must clearly indicate **why** it is active.

This becomes the **primary outreach surface**.

#### 2. Reframe Follow-Ups as Contextual, Not Primary

-   Follow-ups remain important but are **subordinate** to relationship
    state.

-   Every follow-up must:

    -   Be tied to a contact

    -   Display last engagement type, date, and outcome

```{=html}
<!-- -->
```
-   Standalone, context-free overdue lists are explicitly rejected.

#### 3. Adopt a Tabbed Dashboard Structure

A structural decision was made to move toward **dashboard tabs with
widgets**, rather than a single scrolling page.

**Initial tabs (v1):**

-   **Outreach**

    -   Active Contacts

    -   Recent Engagements feed

```{=html}
<!-- -->
```
-   **Follow-Ups**

    -   Overdue (with engagement context)

    -   Upcoming (near-term)

This structure:

-   Preserves clarity

-   Avoids clutter

-   Scales cleanly as features grow

#### 4. Widgets as Future-Proofing

-   Dashboard components should evolve into reusable widget partials.

-   This establishes a maintainable pattern for future expansion
    (pipeline, insights, calendar, etc.).

### Calendar Discussion (Explicitly Deferred)

-   A visual calendar and `.ics` export were discussed as a strong
    future enhancement.

-   Consensus reached:

    -   Calendar functionality makes sense

    -   Existing `.ics` groundwork can be leveraged

```{=html}
<!-- -->
```
-   **Decision:** Calendar tab and exports are **explicitly deferred**.

-   A "pin" was placed on this feature for a later phase, preventing
    scope creep.

### Implementation Plan (Agreed, Not Yet Executed)

-   Dashboard v2 will be implemented in a **new working chat**.

-   Execution order:

    1.  Add Active Contacts query (engagement-aware)

    2.  Refactor dashboard route to support multiple data sections

    3.  Convert `dashboard.html` to Bootstrap tabs

    4.  Move and upgrade follow-ups into contextual lists

```{=html}
<!-- -->
```
-   Deployment planned as a **single, contained commit**.

### Design Principles Reinforced

-   Relationship state \> raw dates

-   No "magic" or opaque CRM logic

-   Every dashboard item must justify its presence

-   Context before automation

-   Structure before polish

### Phase / Version Context

-   This discussion marks the **transition point from Dashboard v1 →
    Dashboard v2 planning**.

-   No version bump occurred in this chat.

-   Calendar functionality formally moved to a **future phase**.

### Outcome

The dashboard is now treated as a **strategic surface**, not a reminder
list.\
Active Contacts and tabbed structure were established as foundational
concepts for the next evolution of Ulysses CRM.

**Ulysses CRM --- Engagement System Migration & Stabilization Summary**\
**Date:** December 18, 2025

### Goals

-   Migrate the legacy **interactions** system to a new, more structured
    **engagements** model without data loss.

-   Improve the quality, usability, and long-term extensibility of
    engagement logging.

-   Preserve historical engagement data while enabling richer future
    workflows (summaries, transcripts, editing).

-   Stabilize deployment and resolve environment and import
    inconsistencies during rollout.

### Key Decisions

1.  **Proceed with Engagements Migration (No Data Loss Confirmed)**

    -   Verified that all prior engagement data was successfully
        migrated and visible in the new engagement table.

    -   Confirmed via direct SQL queries that historical records
        remained intact.

```{=html}
<!-- -->
```
1.  **Adopt Engagements as the Canonical Communication Log**

    -   The new `engagements` table replaces the prior `interactions`
        model for logging calls, texts, emails, meetings, and notes.

    -   Engagements now support:

        -   `engagement_type`

        -   `occurred_at`

        -   `outcome`

        -   `notes`

        -   `transcript_raw`

        -   `summary_clean`

```{=html}
<!-- -->
```
1.  **Transcript Field Is Channel-Agnostic (Intentional Design)**

    -   Explicitly affirmed that **emails may be pasted into the
        Transcript field**.

    -   Transcript is defined as the *verbatim record of communication*,
        regardless of medium (call, email, meeting).

    -   Summary field is used for concise, CRM-ready synthesis.

    -   Decision made **not** to rename the field, preserving conceptual
        clarity and future automation flexibility.

```{=html}
<!-- -->
```
1.  **Dedicated Engagement Edit Page (Not Inline Editing)**

    -   Editing engagements is required functionality.

    -   Chose a **dedicated edit page** (`/engagements/<id>/edit`)
        rather than a modal for now:

        -   Simpler routing and state management

        -   More extensible for long-form transcripts and summaries

    ```{=html}
    <!-- -->
    ```
    -   Modal editing explicitly deferred.

```{=html}
<!-- -->
```
1.  **engagements.py Reintroduced as a First-Class Module**

    -   Resolved Render deployment failures caused by missing or
        mismatched imports.

    -   Finalized and restored `engagements.py` with:

        -   `list_engagements_for_contact`

        -   `insert_engagement`

        -   `delete_engagement`

    ```{=html}
    <!-- -->
    ```
    -   Aligned function names with imports used in `app.py`.

```{=html}
<!-- -->
```
1.  **Deployment and Branch Workflow Confirmed**

    -   Work completed on feature branch (`engagement-v1`) and merged
        cleanly into `main`.

    -   Render deployment succeeded after resolving:

        -   `.venv` accidentally tracked files

        -   `.gitignore` corrections

        -   Missing module imports

    ```{=html}
    <!-- -->
    ```
    -   Live production system verified functional.

### Features Added

-   New Engagement Log UI in `edit_contact.html`

-   Engagement creation with date + time parsing (hour/minute/AM--PM)

-   Transcript + Summary dual-field model

-   Engagement deletion

-   Dedicated engagement edit route and template

-   Modularized engagement data access (`engagements.py`)

### Features Explicitly Deferred

-   Modal-based engagement editing

-   Engagement tagging or categorization beyond type

-   Automated transcript parsing or AI summarization

-   UI enhancements for inline editing

### Design Principles Reinforced

-   **No silent data loss**: migrations must be verified at the database
    level.

-   **Source vs. synthesis separation**: transcript vs. summary is
    intentional and foundational.

-   **Incremental UX evolution**: correctness and stability before
    polish.

-   **Production parity matters**: local fixes must align with Render's
    Python/runtime behavior.

-   **Modularity over monolith growth**: logic extracted from `app.py`
    when scope justifies it.

### Phase / Version Context

-   This work represents a **post--v0.10.x structural enhancement**,
    laying groundwork for:

    -   Phase 4.5 engagement continuity

    -   Future AI-assisted summaries

    -   Cross-channel communication analytics

```{=html}
<!-- -->
```
-   No formal version bump occurred during this session, but
    functionality materially advanced.

### Current Status

-   ✅ Engagement system live in production

-   ✅ Historical data preserved

-   ✅ Editing supported

-   ⚠️ 500 errors acknowledged as possible edge cases; to be addressed
    if/when they arise

-   �� System considered stable and ready for normal use

**Summary Statement:**\
December 18, 2025 marked the successful migration and stabilization of
Ulysses CRM's engagement system, replacing legacy interactions with a
richer, more durable communication model while reinforcing core design
principles around data integrity, clarity, and extensibility.

**Ulysses CRM --- Engagement Logging Errors & Schema Hardening**\
**Date:** December 18, 2025

### Goals

-   Successfully log engagement records (emails, phone calls) in
    production without errors.

-   Resolve unexpected 500 errors encountered while saving engagements
    on Render.

-   Harden the engagements data model to better reflect real-world usage
    and prevent future production interruptions.

### Issues Encountered

1.  **500 error on engagement save (initial)**

    -   Root cause: `insert_engagement()` attempted to read
        `cur.fetchone()[0]` while using a dict-style cursor, causing
        `KeyError: 0`.

```{=html}
<!-- -->
```
1.  **500 error when logging a phone call**

    -   Root cause: PostgreSQL `StringDataRightTruncation` error due to
        `outcome` column being defined as `VARCHAR(80)` while longer
        text was being saved.

### Key Decisions & Fixes

-   **Cursor consistency enforced**

    -   Updated `insert_engagement()` to read returned IDs using dict
        access (`row["id"]`) rather than tuple indexing.

    -   Reinforced the design principle that all DB helpers should
        assume dict-style cursors.

```{=html}
<!-- -->
```
-   **Schema updates in production**

    -   Altered `engagements.outcome` from `VARCHAR(80)` to `TEXT` to
        support real-world descriptive outcomes.

    -   Widened `engagements.engagement_type` from `VARCHAR(30)` to
        `VARCHAR(80)` as a proactive safeguard against longer labels.

    -   Changes were applied directly in production via Render Shell and
        verified post-restart.

```{=html}
<!-- -->
```
-   **Deployment approach**

    -   Confirmed that Render-first deployment (via `crmput`) is
        acceptable and effective in certain situations, even when local
        workflows are bypassed.

    -   Used service restart and gunicorn process termination as valid
        operational restart methods when the UI restart option was not
        easily discoverable.

### Design Principles Reinforced

-   **Schema should reflect usage, not idealized constraints**

    -   User-entered or descriptive fields should favor `TEXT` unless
        there is a compelling reason not to.

```{=html}
<!-- -->
```
-   **Fail loudly and clearly**

    -   Insert helpers should be defensive and explicit when expected
        return values are missing.

```{=html}
<!-- -->
```
-   **Production stability over premature normalization**

    -   Widening columns was preferred over truncation or strict
        validation to avoid data loss and user friction during active
        use.

```{=html}
<!-- -->
```
-   **Consistency over cleverness**

    -   Dict-based cursors are now the assumed standard across the CRM
        codebase.

### Features Added or Deferred

-   **Added (implicitly)**

    -   More resilient engagement logging through schema hardening.

```{=html}
<!-- -->
```
-   **Deferred**

    -   Normalization of engagement types into a reference table.

    -   Additional server-side validation on engagement fields.

    -   Audit/history or soft-delete for engagements.

### Phase / Version Context

-   This work occurred during ongoing post--v0.10.x production
    refinement.

-   No formal version bump was made, but these changes are considered
    baseline for all future engagement-related development.

-   The engagement feature is now considered stable for daily production
    use.

### Outcome

-   Engagements (email, phone call, etc.) can now be created reliably in
    production.

-   The CRM withstood real-world usage and live-fire debugging,
    resulting in a more robust data model and clearer operational
    practices.

**Status:** Closed and stable\
**Next logical areas (optional, future):** dashboard surfacing of
engagements, engagement editing/history, type normalization

**Dashboard v2 --- Project & Design Evolution Summary**\
**Date:** December 18, 2025

### Goals

The primary objective of this work session was to design and ship
**Dashboard v2** in a controlled, low-risk manner that materially
improves usability without introducing schema risk or deployment
instability. The dashboard is being repositioned as an **intent-driven
workspace** rather than a raw follow-up list.

Key goals included:

-   Organizing the dashboard by user intent using tabs.

-   Making **Active Contacts** the primary outreach surface.

-   Ensuring all follow-ups display **engagement context**, not just
    dates.

-   Keeping the scope small enough to deploy confidently in a single
    commit.

### Key Design Decisions

#### 1. Dashboard Structure (v2)

-   Introduced **Bootstrap tabs** to organize content:

    -   **Outreach tab**

        -   Active Contacts (primary widget)

        -   Recent Engagements (compact feed)

    ```{=html}
    <!-- -->
    ```
    -   **Follow-ups tab**

        -   Overdue Follow-ups (with engagement context)

        -   Upcoming Follow-ups (next N days, with context)

```{=html}
<!-- -->
```
-   Explicitly deferred Pipeline and analytics widgets to a later phase.

#### 2. Active Contact Definition (v1)

A contact is considered *Active* if **any** of the following are true:

-   Last engagement within 30 days

-   Has a follow-up date (overdue or upcoming)

-   Has a buyer profile

-   Has a seller profile

Each active contact displays **why** it is active via derived badges.

#### 3. Engagement Context Everywhere

-   All follow-ups now include:

    -   Last engagement type

    -   Engagement date

    -   Outcome or summary snippet

```{=html}
<!-- -->
```
-   This reinforces the principle that *tasks without context are
    noise*.

### Implementation & Technical Decisions

#### 4. Query Architecture

-   Replaced multiple follow-up--only queries with a single, richer
    query set:

    -   One row per contact

    -   `LEFT JOIN LATERAL` used to fetch most recent engagement per
        contact

    -   `EXISTS` subqueries used for buyer/seller profile flags

```{=html}
<!-- -->
```
-   "Active reason" logic intentionally derived in Python for clarity
    and maintainability.

#### 5. Schema-Aware Safety Patch

-   A production 500 error revealed that the Render database did **not**
    yet include `user_id` on `contacts`.

-   Rather than forcing an immediate migration, a **schema-aware
    fallback strategy** was implemented:

    -   The dashboard route dynamically detects whether `user_id` exists
        per table.

    -   Queries scope to `current_user.id` only when the column exists.

```{=html}
<!-- -->
```
-   This allowed Dashboard v2 to ship safely without blocking on
    migrations.

-   A proper multi-user migration for `contacts.user_id` was explicitly
    deferred.

### UI / UX Refinements

#### 6. Density & Readability Improvements

-   Recent Engagements and "Last Engagement" content were consuming too
    much screen space.

-   Implemented **progressive disclosure**:

    -   Recent Engagements show the first 5 items by default with a
        **See more / See less** toggle.

    -   Individual engagement summaries collapse long text with per-item
        **See more / See less** controls.

```{=html}
<!-- -->
```
-   Active Contacts table now:

    -   Shows Buyer/Seller designation **beneath the contact name**, not
        mixed into "why" badges.

    -   Keeps "Why active" focused on behavior (engagement recency,
        follow-ups).

#### 7. Deferred Enhancements (Explicitly Not Done)

-   Buyer/Seller badges are **not yet clickable**.

-   No direct links yet to:

    -   Buyer profile

    -   Seller profile

    -   Engagement tab

```{=html}
<!-- -->
```
-   These were intentionally deferred to avoid scope creep and routing
    decisions mid-phase.

### Design Principles Reinforced

-   **Context over counts:** Dates and tasks are useless without
    interaction history.

-   **Progressive disclosure:** Default views should be scannable;
    details on demand.

-   **One-commit discipline:** Each dashboard evolution must be
    deployable atomically.

-   **Schema realism:** Production safety takes priority over
    theoretical model purity.

-   **UI clarity:** Visual hierarchy matters more than raw data density.

### Phase & Version Positioning

-   This work constitutes **Dashboard v2 (Phase 5.x)** within Ulysses
    CRM.

-   It replaces the original follow-up--centric dashboard entirely.

-   It establishes a stable foundation for future additions such as:

    -   Pipeline widgets

    -   Calendar views

    -   Linked buyer/seller navigation

    -   Analytics and KPIs

Dashboard v2 is now functionally complete, safely deployed, and
intentionally positioned for incremental enhancement rather than
redesign.

## Ulysses CRM --- Contact Save UX Fix

**Date:** December 18, 2025

### Goal

Improve the user experience when editing Contacts by ensuring that
saving a Contact does **not** exit the user back to the Contacts list.
The intended behavior is to keep the user within the active Contact
record unless they explicitly choose to navigate away.

This aligns with real-world CRM workflows where Contacts act as a
central working context for engagements, follow-ups, and related
profiles.

### Problem Identified

After saving a Contact, the application redirected users back to the
Contacts list view. This interrupted workflow, especially during
multi-step edits or when immediately continuing work on engagements or
follow-ups tied to that Contact.

### Key Decisions

1.  **Save should preserve context**

    -   The default "Save" action now keeps the user on the same Contact
        record.

    -   Navigation away from the record is handled exclusively through
        the main "Contacts" menu item.

```{=html}
<!-- -->
```
1.  **Minimal, explicit backend change**

    -   Only the redirect following a successful POST save in the
        `edit_contact` route was modified.

    -   Other redirects to `edit_contact` (used for navigation,
        defensive checks, or sub-actions) were intentionally left
        unchanged.

```{=html}
<!-- -->
```
1.  **Lightweight confirmation feedback**

    -   A non-intrusive "Contact saved" confirmation message was added.

    -   Implemented via a querystring flag (`saved=1`) rather than
        sessions or flash messages.

### Features Added

-   **Post-save redirect refinement**

    -   After saving a Contact, the app redirects back to the same
        Contact record instead of the Contacts list.

```{=html}
<!-- -->
```
-   **Inline save confirmation**

    -   A temporary success alert appears at the top of the Contact edit
        page when a save occurs.

    -   The alert naturally disappears on refresh or navigation.

### Features Explicitly Deferred

-   "Save & Return" secondary buttons

-   Global flash-message system

-   Applying the same pattern to Buyer, Seller, and Engagement edits
    (identified as future follow-ups)

These were intentionally deferred to keep the change small, targeted,
and low-risk.

### Design Principles Reinforced

-   **Context preservation:** Users should remain in the object they are
    actively working on.

-   **Explicit navigation:** Leaving a record should be a deliberate
    user action, not a side effect of saving.

-   **Minimal surface area changes:** Fix only what is broken; do not
    refactor unrelated logic.

-   **Consistency with professional CRMs:** Behavior mirrors established
    platforms like Salesforce and HubSpot.

### Process & Workflow Notes

-   Confirmed local repository was fully in sync with GitHub before
    making changes.

-   Scoped edits to exactly two locations:

    -   One redirect change in the `edit_contact` POST handler

    -   One UI alert addition in `edit_contact.html`

```{=html}
<!-- -->
```
-   Changes were reviewed with `git diff`, committed with a focused
    message, pushed, and deployed cleanly.

### Outcome

The Contact edit workflow now feels smoother, faster, and more
professional. This fix establishes a UX pattern that can be consistently
reused across other edit views in Ulysses CRM.

**Ulysses CRM --- Associated Contacts Feature**\
**Project Evolution Summary**\
**Date:** December 20, 2025

### Goal

Design and implement a first-class **Associated Contacts** system in
Ulysses CRM that:

-   Allows linking one contact to another (e.g., spouse, co-owner,
    attorney)

-   Supports inline creation of a new contact during association

-   Ensures associations are **reciprocal by design**

-   Is compatible with the emerging **multi-user architecture**

### Key Decisions

1.  **Replaced Legacy `related_contacts` Model**

    -   Deprecated the old, one-way `related_contacts` table.

    -   Introduced a new relational table: `contact_associations`.

    -   Associations are stored **once**, not duplicated per direction.

```{=html}
<!-- -->
```
1.  **Symmetric Relationship Design**

    -   A single association row represents A ↔ B.

    -   Query logic determines "the other contact" dynamically.

    -   Guarantees reciprocity without redundant data or sync risk.

```{=html}
<!-- -->
```
1.  **Canonical Ordering Rule**

    -   Associations stored with `(min(contact_id), max(contact_id))`.

    -   Prevents duplicate A--B / B--A rows.

    -   Enforced with a unique index and helper logic.

```{=html}
<!-- -->
```
1.  **Inline Contact Creation**

    -   If an associated contact does not exist:

        -   User can create it inline (first name, last name, email,
            phone).

        -   Contact is saved immediately and linked in the same action.

    ```{=html}
    <!-- -->
    ```
    -   Eliminates workflow friction and orphan records.

```{=html}
<!-- -->
```
1.  **User-Scoped Data Integrity**

    -   All association queries are scoped by `user_id`.

    -   Exposed a local schema mismatch when `contacts.user_id` existed
        in production but not locally.

    -   Reinforced the importance of **local--production schema
        parity**.

### Features Added

-   **New Database Table**

    -   `contact_associations`

    -   Includes constraints for:

        -   No self-association

        -   No duplicate pairs

        -   Cascading deletes

```{=html}
<!-- -->
```
-   **Helper Functions**

    -   `get_contact_associations()`

    -   `create_contact_association()`

```{=html}
<!-- -->
```
-   **New Routes**

    -   `/contacts/search` (AJAX typeahead search)

    -   `/contacts/<id>/associations/add`

    -   `/contacts/<id>/associations/create`

    -   `/contacts/<id>/associations/<assoc_id>/delete`

```{=html}
<!-- -->
```
-   **UI Enhancements**

    -   Replaced legacy Associated Contacts UI with:

        -   Modal-based workflow

        -   Search existing contacts

        -   Create new contact inline

        -   Remove association action

    ```{=html}
    <!-- -->
    ```
    -   Associations displayed with:

        -   Click-through navigation

        -   Relationship type

        -   Email and phone

### Design Principles Reinforced

-   **Single Source of Truth**

    -   One association row, many views.

```{=html}
<!-- -->
```
-   **No Silent Data Duplication**

    -   Canonical ordering + unique index.

```{=html}
<!-- -->
```
-   **Local-First Development**

    -   Errors surfaced immediately when local schema diverged from
        production.

```{=html}
<!-- -->
```
-   **Security-First Operations**

    -   Database credentials accidentally exposed during
        troubleshooting.

    -   Immediate credential rotation performed in Render.

    -   Reinforced practice: never paste secrets, always rotate on
        exposure.

### Operational Incident & Resolution

-   **Issue**

    -   `/contacts/search` returned 500 errors locally.

```{=html}
<!-- -->
```
-   **Root Cause**

    -   Local `contacts` table lacked `user_id`, while production had
        it.

```{=html}
<!-- -->
```
-   **Resolution**

    -   Added `user_id` column locally.

    -   Backfilled existing records.

    -   Reinforced schema-upgrade discipline.

```{=html}
<!-- -->
```
-   **Security Event**

    -   Production database URL briefly shared.

```{=html}
<!-- -->
```
-   **Mitigation**

    -   Render credential rotation using:

        -   "Create new default credentials"

        -   App environment updated

        -   Old credentials deleted

    ```{=html}
    <!-- -->
    ```
    -   No downtime, no data loss.

### Features Explicitly Deferred

-   Directional relationships (parent → child)

-   Household/group abstraction

-   Auto-suggested associations

-   Migration of legacy `related_contacts` data

-   UI surfacing beyond contact detail page (dashboard, reports)

### Phase / Version Context

-   This work fits into **Phase 4--5 continuity** of Ulysses CRM.

-   Builds directly on:

    -   Multi-user groundwork (`user_id` scoping)

    -   Engagement-centric contact design

```{=html}
<!-- -->
```
-   No version number bump declared yet, but functionally represents a
    **major CRM capability upgrade**.

### Outcome

Ulysses CRM now supports **CRM-grade relationship modeling**:

-   Clean

-   Reciprocal

-   Secure

-   Multi-user safe

-   Extensible for future household and trust structures

This feature marks a clear transition away from ad-hoc contact notes
toward a **relational contact graph**, aligning the system with
professional-grade CRM platforms while preserving local control and
simplicity.

**Ulysses CRM -- Contact Association Hotfix & Production Hardening**\
**Date:** December 20, 2025

### Overview / Goal

This session focused on diagnosing and resolving a production 500 error
occurring when creating and associating a new contact with an existing
contact ("Create and Link" flow). The goal was to restore production
stability quickly, harden the code path to prevent recurrence, and do so
without disrupting ongoing feature development in the listing and offer
statuses (v0.10.0) branch.

### Root Cause Identified

-   The production error was caused by a schema mismatch:\
    The `contacts` table in production did **not** have a `created_at`
    column, but the `create_and_associate_contact` INSERT explicitly
    referenced it.

-   This caused a `psycopg2.errors.UndefinedColumn` exception and a 500
    error on submit.

### Immediate Production Fix

-   Added missing `created_at` and `updated_at` columns to the
    production `contacts` table with safe defaults.

-   This immediately resolved the runtime exception at the database
    level.

### Code Hardening (Primary Feature Change)

-   Refactored the **Create and Link** contact INSERT logic to:

    -   **Stop explicitly inserting `created_at` / `updated_at`**

    -   Rely on database defaults instead

```{=html}
<!-- -->
```
-   Simplified and corrected cursor handling:

    -   Ensured only **one** `fetchone()` call is used with
        `RETURNING id`

    -   Leveraged `RealDictCursor` guarantees for clean `row["id"]`
        access

**Result:**\
The contact association path is now resilient to timestamp schema drift
and safer across environments.

### Validation & Defensive Improvements (Deferred but Noted)

The following improvements were identified and explicitly deferred for a
future hardening pass:

-   Add a defensive guard after `INSERT ``…`` RETURNING id` in case no
    row is returned

-   Wrap DB operations in `try/finally` or context-managed connections
    to guarantee `conn.close()`

-   Optionally validate or constrain `relationship_type` values before
    creating associations

These were intentionally **not** implemented now to keep the hotfix
minimal and low-risk.

### Git & Deployment Decisions

-   Although the work initially began on a hotfix branch, the final
    decision was:

    -   **Commit the fix directly to `main`**

    -   Push immediately and deploy to production

```{=html}
<!-- -->
```
-   Rationale:

    -   The fix was small, isolated, and clearly production-ready

    -   Local testing was blocked by environment and DB setup issues

    -   The production failure was already well-understood and validated

**Key Principle Reinforced:**\
For small, critical production bugs, a direct `main` hotfix is
acceptable and sometimes preferable.

### Branch & Phase Coordination

-   Explicitly noted and locked in:

    -   When returning to the **v0.10.0 listing and offer statuses
        branch**, `main` must be merged or synced first to ensure this
        production fix is included.

```{=html}
<!-- -->
```
-   This ensures no regression when that feature branch is eventually
    deployed.

### Local Environment Findings (Secondary)

-   Local development environment issues uncovered:

    -   No virtual environment existed in the repo initially

    -   `DATABASE_URL` was pointing to production

    -   No local Postgres server was running

    -   Port 5000 was occupied by an Apple AirTunes service on macOS

```{=html}
<!-- -->
```
-   These were diagnosed but intentionally deprioritized once the
    decision was made to proceed with a direct production deploy.

### Verification & Source-of-Truth Practice

-   Established and demonstrated the correct way to compare local vs
    production code:

    -   Use Git as the source of truth, not live filesystem inspection

    -   Verified with `git diff origin/main -- app.py` (clean)

```{=html}
<!-- -->
```
-   Reinforced that "production == deployed `main`", not local state.

### Optional Future Enhancement (Discussed, Not Implemented)

-   Add a lightweight `/version` endpoint so production can self-report
    version/commit

-   Requires:

    -   A `version.py` file

    -   Explicit Flask route registration

```{=html}
<!-- -->
```
-   Not required for current stability and intentionally deferred.

### Outcome

-   ✅ Production 500 error resolved

-   ✅ Contact association flow hardened

-   ✅ `main` is clean, deployed, and verified against GitHub

-   ✅ No disruption to ongoing v0.10.0 feature work

-   ✅ Clear handoff note established for future branch sync

### Phase / Version Context

-   This work is considered a **production hotfix** applied during the
    v0.10.0 development cycle.

-   No phase transition occurred, but a dependency was explicitly
    recorded:\
    **v0.10.0 branch must absorb this `main` change before deployment.**

**Status:** Closed and stable.

**Ulysses CRM -- Transactions v1 Rollout**\
**Historical & Project-Evolution Summary**\
**Date: December 21, 2025**

### Context & Goal

This conversation occurred during the rollout of **Transactions v1** in
Ulysses CRM, immediately after finalizing and applying the new database
migration `004_transactions_v1.sql`. The primary goal was to **wire
existing Flask routes and templates to the new MLS-aligned transactions
schema** without duplicating or undoing work completed the prior day.

### Key Schema Milestone

The new `transactions` table was confirmed live in the local database,
featuring:

-   MLS-aligned `transaction_type` (`listing`, `offer`)

-   A **single unified `status` column** (replacing `listing_status` /
    `offer_status`)

-   Required fields: `address`, `primary_contact_id`, `user_id`

-   Expanded pricing and key-date fields

-   `status_changed_at` for lifecycle tracking

-   Legacy `contact_id` still present but no longer conceptually primary

-   Tight user scoping and FK relationships (including cascading
    deadlines)

This schema marked a **clear version transition** from the earlier,
lighter transaction model to a production-ready, MLS-faithful structure.

### Discovery & Course Correction

Dennis identified that the assistant had begun proposing **new routes
and pages** that duplicated functionality already implemented and
discussed the day before. Upon review, it became clear that:

-   Existing routes already covered:

    -   Contact-scoped transaction creation

    -   Transaction edit

    -   Transaction delete

```{=html}
<!-- -->
```
-   Existing templates already supported a transaction form workflow
    tied to contacts

-   The correct path was **refactoring in place**, not parallel
    development

This was an important reset moment to avoid redoing or fragmenting work.

### Key Decisions Reinforced

1.  **Preserve existing endpoints and workflows**

    -   Especially `/contacts/<id>/transactions/new`

    -   Avoid breaking contact-centric UX already integrated into
        Contacts

```{=html}
<!-- -->
```
1.  **Refactor, do not replace**

    -   Update existing routes to write to the new schema

    -   Update templates to collect new required fields (`address`,
        unified `status`)

    -   Remove obsolete fields (`listing_status`, `offer_status`,
        `notes`) at the form and route level

```{=html}
<!-- -->
```
1.  **Incremental rollout strategy**

    -   First: ensure contact-scoped create/edit works cleanly on the
        new schema

    -   Only after that: add global transaction views (index, detail
        pages)

```{=html}
<!-- -->
```
1.  **Database constraints drive UX**

    -   Because `address` is `NOT NULL`, the form must collect it

    -   Draft or placeholder transactions without addresses are
        intentionally disallowed

```{=html}
<!-- -->
```
1.  **Git as the source of truth**

    -   Before proceeding, use git history to confirm what was already
        changed the prior day

    -   Avoid design drift by aligning next steps strictly with
        committed code

### Design Principles Reaffirmed

-   **Single source of truth**: schema defines behavior, not the other
    way around

-   **No parallel systems**: one transactions model, one set of routes

-   **Backward compatibility where helpful** (temporarily keeping
    `contact_id`)

-   **User-scoped safety everywhere** (`user_id` always enforced)

-   **Phase discipline**: finish refactor before adding new surface area

### Features Deferred (Explicitly)

-   Global `/transactions` index and detail views

-   Dynamic status dropdown behavior

-   Advanced pricing/date editing in the first refactor pass

-   Removal of legacy `contact_id` column (to be handled in a later
    migration)

### Outcome / State at Close

The conversation ended with a clear agreement to:

-   Pause new development

-   Inspect git history from the prior day

-   Resume work by **updating existing routes and templates only**,
    staying aligned with the Transactions v1 schema and the path already
    established

This summary documents a **course correction moment** that helped keep
Transactions v1 on a clean, incremental, and non-duplicative trajectory.

## Ulysses CRM --- Transactions Feature Design Formalization

**Date:** December 21, 2025

### Context and Goal

The primary goal of this session was to **formalize and preserve** the
design decisions for the **Transactions feature** (Listings and Offers)
in Ulysses CRM by converting a long, high-value exploratory chat into a
**canonical, authoritative feature design document**.

This was not a feature ideation session. The feature itself was already
conceptually complete. The objective was to:

-   Lock intent

-   Prevent future re-litigation of decisions

-   Create a durable reference to guide implementation and future phases

The Transactions feature is targeted for **v0.10.0**.

### Key Decisions Made

#### 1. Markdown Chosen as the Authoritative Format

-   Markdown was explicitly selected as the **primary and authoritative
    documentation format**

-   Rationale:

    -   Git-native and versionable

    -   Diff-friendly

    -   Treatable as a contract, not a presentation artifact

    -   Convertible later into Word/PDF if needed

```{=html}
<!-- -->
```
-   The document is intended to live in:

-   `docs/features/transactions.md`

#### 2. Transactions Confirmed as a First-Class Core Object

The session reaffirmed and locked the foundational architectural
decision that:

-   **Transactions**, not contacts, own:

    -   Status lifecycle

    -   Prices

    -   Milestone dates

    -   Deadlines

```{=html}
<!-- -->
```
-   Buyers and sellers *reflect* transactions

-   The dashboard *synthesizes* transactions

-   The dashboard never edits transactional data

This reinforced a key design principle:

Ulysses is a transaction-aware CRM, not a contact tracker with add-ons.

#### 3. Status Lifecycle Locked and Canonical

The shared status lifecycle for listings and offers was reaffirmed and
documented as **locked for v0.10.0**:

1.  Draft (default)

2.  Coming Soon

3.  Active

4.  Attorney Review

5.  Pending/UC

6.  Closed (terminal)

7.  Temporarily Off Market

8.  Withdrawn

9.  Canceled (Final)

10. Expired

Additional rules reinforced:

-   Draft is internal only

-   Closed is terminal

-   History is preserved

-   MLS-native terminology is mandatory

-   Internal storage uses snake_case

#### 4. Data Model Fully Formalized

The chat resulted in a clean, finalized schema specification being
preserved in Markdown, including:

**transactions table**

-   Supports both listings and offers

-   Includes:

    -   Pricing lifecycle fields

    -   Ordered core milestone dates

    -   Explicit mortgage commitment date

    -   Audit fields

**transaction_deadlines table**

-   Supports unlimited deal-specific deadlines

-   Includes reminder offsets and completion tracking

-   Uses ON DELETE CASCADE to avoid orphan data

This confirmed the guiding principle of:

-   **Core dates as columns**

-   **Variable dates as rows**

#### 5. Scope Control Explicitly Reinforced

The document clearly distinguishes between:

**Included in v0.10.0**

-   Transactions

-   Status lifecycle

-   Core milestone dates

-   Custom deadlines

-   Buyer/Seller sheet integration

-   Dashboard synthesis

**Explicitly deferred**

-   Commission calculations

-   MLS sync

-   Reporting and analytics

-   Buyer-seller linking on the same transaction

-   Advanced automation

This reinforced the discipline of **phase-locked delivery**.

#### 6. Design Principles Reaffirmed

The session reinforced several non-negotiable Ulysses design principles:

-   Transactions own truth

-   Dashboards mirror, never mutate

-   Preserve history over deletion

-   Flexibility without schema chaos

-   MLS realism over abstraction

-   "Do it right once"

These principles were codified in the document itself to prevent drift.

### Deliverable Created

A clean, ASCII-safe Markdown file was generated and made available for
download:

-   `ulysses_transactions_feature_design_v0100.md`

This file is intended to be:

-   Committed to the repository

-   Treated as authoritative

-   Used as the shared reference during implementation

### Phase and Version Impact

-   This session **did not advance the implementation phase**

-   It **completed the design-lock phase** for Transactions

-   v0.10.0 scope is now fully documented and frozen

-   Next logical step is **Session 2: migrations and first routes**,
    guided directly by the spec

### Overall Significance

This chat marks the transition from:

-   Exploratory design → **formal product specification**

It represents a maturation point for Ulysses CRM where features are no
longer just "built," but **designed, documented, and governed**.

**Ulysses CRM --- Engagement Save / Safari Error Investigation**\
**Date:** December 22, 2025

### Goals

-   Diagnose a reported **"Safari can't open page"** error occurring
    when saving an Engagement.

-   Determine whether the issue was a server-side failure, a data
    persistence issue, or a browser-side anomaly.

-   Decide on safe, low-risk actions that would not disrupt ongoing
    Transaction feature work.

### Findings

-   Server logs showed **successful POST → 302 → GET → 200** flows for:

    -   `/contacts/<id>/engagements/add`

    -   `/engagements/<id>/edit`

    -   Subsequent redirects back to `/edit/<contact_id>`

```{=html}
<!-- -->
```
-   This confirmed that:

    -   Engagements were being processed and pages rendered
        successfully.

    -   No HTTP 500, 502, 503, or timeout errors were present.

```{=html}
<!-- -->
```
-   The issue was determined to be **browser-side (Safari)** rather than
    an application failure, likely triggered by:

    -   Redirect chains after POST

    -   Minor connection/TLS hiccups

    -   Missing ancillary assets (notably `/favicon.ico` returning 404)

```{=html}
<!-- -->
```
-   Background requests (e.g., `followups.ics`) and bot traffic probing
    for WordPress were identified as unrelated noise.

### Code Review Insights

-   The `add_engagement` route was functionally correct in terms of
    business logic and redirect behavior.

-   Two technical concerns were identified for later remediation:

    1.  **Database connection not explicitly closed**, which could lead
        to intermittent issues under load.

    2.  **Lack of defensive error handling** around date parsing and
        insert operations.

```{=html}
<!-- -->
```
-   A hardened version of the route was proposed but **explicitly
    deferred** to avoid scope creep during active Transaction
    development.

### Key Decisions

-   **Do not modify `app.py` at this time.**

    -   Priority remains completing Transaction-related work.

    -   No functional regression or data loss was observed, so immediate
        refactor was not justified.

```{=html}
<!-- -->
```
-   **Add a `favicon.ico` file** as a low-risk, isolated improvement.

    -   Reduces Safari UI noise and log clutter.

    -   Requires no routing or logic changes.

    -   Can be committed independently.

### Design Principles Reinforced

-   Follow **PRG (Post/Redirect/Get)** pattern consistently and verify
    via logs.

-   Prefer **small, atomic changes** when stabilizing UX issues.

-   Defer structural or defensive refactors unless there is clear
    functional impact.

-   Maintain focus on current phase goals rather than opportunistic
    refactoring.

### Changes Made / Planned

-   **Planned (Immediate):**

    -   Add `static/favicon.ico`

    -   Optionally reference it in `base.html`

```{=html}
<!-- -->
```
-   **Deferred (Post-Transactions):**

    -   Add explicit DB connection closing and rollback safety

    -   Harden engagement routes with error handling and ownership
        guards

    -   Optionally add a `/favicon.ico` route for full browser
        compatibility

### Phase / Version Context

-   No phase or version transition occurred.

-   This work took place during ongoing **Transactions feature
    development**, with intentional scope control to avoid destabilizing
    unrelated areas of the codebase.

**Outcome:**\
The engagement save flow was confirmed stable. The Safari error was
treated as a cosmetic/browser-side issue, addressed incrementally via
favicon support, while preserving momentum on higher-priority
Transaction work.

## Ulysses CRM -- Transactions v1 Design & Migration Alignment

**Date:** December 23, 2025

### Overall Goal

Stabilize and finalize the **Transactions feature** so it accurately
reflects real-world MLS listing workflows, supports future reporting,
and is safe to deploy live. This phase focused on correcting schema
drift, aligning terminology with MLS practice, and designing a flexible
foundation for offers, deadlines, and analytics.

## Key Decisions & Outcomes

### 1. Transactions as the Core Deal Thread

-   **One transaction = one deal thread** (listing or buyer-side).

-   Offers are **not** embedded as fields on transactions.

-   Transactions hold:

    -   Listing lifecycle

    -   Core property info

    -   Key milestone dates

    -   Notes and narrative context

This resolved earlier confusion between listings vs offers and
eliminated brittle single-status models.

### 2. MLS-Aligned Listing Status Model (Finalized)

The following **listing_status** values were locked and approved:

-   Draft (default)

-   Coming Soon

-   Active

-   Pending/UC

-   Closed

-   Withdrawn

-   Temporarily Off Market

-   Canceled (Final)

-   Expired

**Important clarifications:**

-   "Active Under Contract / Continue to Show" is treated as
    **Pending/UC**, with nuance captured in notes rather than a separate
    enum.

-   Status values are intentionally tight to remain MLS-aligned and
    reportable.

### 3. Dates as First-Class Data

Dates were established as essential to making statuses meaningful and
reportable.

**On transactions:**

-   Inspection deadline

-   Financing contingency date

-   Expected close date

-   (Optional) actual close date

**On offers (future phase):**

-   Received, presented, best & final requested/received

-   Accepted, superseded, rejected, withdrawn timestamps

This enables later reporting on fallout points, timelines, and deal
health.

### 4. Offers Redesigned as a Separate Table (Approved, Deferred UI)

Key decision: **multiple offers must be supported**.

-   New table: `transaction_offers`

-   One row per offer

-   Supports:

    -   Best & Final tracking

    -   Accepted offers falling through

    -   Superseded offers (explicit state)

    -   Full offer history retention

**Acceptance behavior:**

-   Only one offer may be "accepted" at a time

-   Accepting a new offer automatically supersedes the prior accepted
    offer

-   Acceptance is reversible by design

UI for offers was **intentionally deferred** to avoid blocking go-live.

### 5. Agent & Brokerage Capture (Strategic)

Offers can optionally be associated with:

-   A **Professional** (agent) already in CRM (preferred)

-   Or a free-text agent name

This design:

-   Captures brokerage affiliation automatically when linked

-   Allows fast entry when the agent is not yet in the system

-   Enables future agent-level performance reporting

### 6. Flexible Deadlines (Retained)

A refined `transaction_deadlines` table was approved to support:

-   Arbitrary milestones

-   Completion tracking

-   Notes and reminders

This complements the fixed "key dates" on transactions.

## Migration Strategy Decisions

### Old Migrations (Dec 19) Reclassified

-   `004_transactions.sql` identified as **exploratory / obsolete**

-   Contained outdated assumptions:

    -   Single status column

    -   Offers embedded in transactions

    -   Monolithic address field

```{=html}
<!-- -->
```
-   Explicit decision made **not to re-run or reuse** it

### New Canonical Migration

-   A new **`004_transactions_v1.sql`** was created and approved

-   Represents the first production-ready transactions schema

-   Designed to be:

    -   MLS-aligned

    -   Reporting-ready

    -   Easy to evolve

### Bootstrap Schema

-   `000_bootstrap_min.sql` retained as valid

-   Minor hygiene improvement approved:

    -   Standardized timestamps to `NOW()` with `NOT NULL`

## Design Principles Reinforced

-   **MLS alignment over internal cleverness**

-   **Statuses are structure; notes capture nuance**

-   **Dates give meaning to states**

-   **Reversibility over hard constraints**

-   **Schema first, UI second**

-   **Data capture precedes reporting**

-   **Future changes should be cheap**

## Phase / Version Context

-   This work establishes **Transactions v1**

-   UI scope intentionally limited to ensure **live deployment
    viability**

-   Offers UI, advanced workflows, and reporting are deferred to a later
    phase

-   A clean checkpoint was reached, with agreement to continue
    implementation in a new chat due to thread size

## End State of This Phase

-   Transactions schema finalized

-   Listing lifecycle locked

-   Key dates approved

-   Offers architecture designed

-   Agent/brokerage capture strategy confirmed

-   Migration hygiene clarified

-   Ready to wire routes/templates and deploy

This phase successfully transitioned Transactions from an experimental
feature into a production-ready foundation.

## Ulysses CRM --- Transactions Feature

**Project Evolution Summary**\
**Date:** December 23, 2025

### 1. High-Level Goal

The objective of this work session was to **reset, stabilize, and
correctly implement Phase 1** of the Transactions feature for Ulysses
CRM, after earlier attempts suffered from schema drift, branch
confusion, and production/local mismatches. The broader goal was to
establish a **durable foundation** that future transaction tracking
phases can safely build upon without regressions.

### 2. Key Strategic Decisions

#### A. Authoritative Design Source Established

-   A curated design document,
    **`ulysses_transactions_feature_design_v0100.md`**, was explicitly
    designated as the **single source of truth**.

-   All schema, routing, and UI decisions were required to align with
    this document.

-   This document was committed to the repository to prevent future
    ambiguity.

**Design principle reinforced:**

No feature evolution without a written, versioned design spec.

#### B. Phase Reset and Clean Re-baseline

-   The existing `feature/transactions` branch was **archived and
    deleted**.

-   Work was restarted from `main`, which matched production.

-   A new, clearly named branch was created:\
    **`feature/transactions-v0100-phase1`**

**Design principle reinforced:**

When schema integrity is compromised, restart from a known-good baseline
rather than patching uncertainty.

### 3. Phase 1 Scope (Explicitly Locked)

Phase 1 was deliberately constrained to **status scaffolding only**.

#### Implemented in Phase 1:

-   Added `transactions.status` column

-   Enforced **check constraint** on allowed statuses

-   Added supporting index

-   Wired `status` into:

    -   New Transaction route

    -   Edit Transaction route

    -   Transaction form UI

```{=html}
<!-- -->
```
-   Ensured default value of `draft`

-   Confirmed schema parity between local and production

#### Explicitly Deferred:

-   Listing lifecycle logic

-   Offer lifecycle logic

-   Status transitions or guards

-   Business rules enforcing allowed state changes

-   Cross-field validation (status vs listing_status vs offer_status)

-   Reporting, dashboards, or automation

**Design principle reinforced:**

Phase isolation: schema first, behavior later.

### 4. Listing and Offer Statuses --- Key Clarification

-   **`listing_status` and `offer_status` were confirmed as NOT
    deprecated.**

-   They remain in the schema with safe defaults:

    -   `listing_status = 'lead'`

    -   `offer_status = 'none'`

```{=html}
<!-- -->
```
-   These fields are intentionally inert during Phase 1.

-   Their functional meaning is deferred to later phases.

This resolved earlier confusion about whether they should be removed or
replaced.

### 5. Routes and UI State (End of Phase 1)

#### Working and Verified:

-   `/contacts/<contact_id>/transactions/new`

-   `/transactions/<transaction_id>/edit`

-   Shared template: `transaction_form.html`

The screens:

-   Render correctly

-   Persist data correctly

-   Redirect correctly

-   Do not yet "lead anywhere" beyond basic CRUD (by design)

This was explicitly accepted as **complete for Phase 1**.

### 6. Database Integrity Outcomes

-   Local database was rebuilt to mirror production schema.

-   Environment variable confusion (`DATABASE_URL`, `.env`) was
    resolved.

-   Confirmed:

    -   Local development is using `realestatecrm_local`

    -   Production remains unaffected

```{=html}
<!-- -->
```
-   No Phase 1 changes were deployed to production yet.

**Design principle reinforced:**

Schema parity before feature work.

### 7. Versioning and Phase Transition

-   Phase 1 changes were committed with message:\
    **"Phase 1: add transactions.status with constraint + index"**

-   Phase 1 is now **frozen**.

-   A new branch was prepared for continuation:\
    **`feature/transactions-v0100-phase2`**

**Explicit transition:**

Phase 1 complete. Phase 2 to begin in a new chat and branch.

### 8. Process Improvements Reinforced

This session reinforced several lasting workflow rules:

1.  **Design documents precede code**

2.  **Phase boundaries must be respected**

3.  **Branches must reflect scope**

4.  **Local ≠ production unless verified**

5.  **When drift is detected, stop immediately**

### 9. Final State at Close of Session

-   Phase 1 complete and stable

-   No regressions introduced

-   Transactions can be created and edited

-   Status system is live but behavior-neutral

-   Clear handoff checklist prepared for Phase 2

-   Decision made to start Phase 2 in a **new chat** to preserve clarity
    and performance

**Status:**\
✅ Phase 1 locked\
➡️ Ready for Phase 2 planning and implementation

## Ulysses CRM --- Transactions Feature

### Phase 2 Completion & Phase 3 Transition Summary

**Date:** December 23, 2025

### 1. Primary Goal of This Chat

The primary objective of this session was to **complete Phase 2 of the
Transactions feature** for Ulysses CRM, stabilize it against the local
database, and prepare a **clean, disciplined transition into Phase 3**
with no scope creep or rework.

This chat intentionally focused on:

-   Finishing transactional data wiring

-   Resolving SQL and persistence issues

-   Improving contact-page transaction visibility

-   Locking Phase 2 scope

-   Preparing a formal Phase 3 handoff

### 2. Major Decisions & Outcomes

#### Phase Boundaries Reinforced

-   **Phase 1 and Phase 2 were explicitly declared complete and locked**

-   A strict "no rework" rule was reinforced for completed phases

-   Phase 3 will begin on a **new branch** and with a clean context
    reset

This reaffirmed the project's **phase-driven development discipline**.

### 3. Database Context Clarified and Locked

-   Confirmed that **all work is against the local Postgres database**,
    not Render

-   Local database name: `realestatecrm_local`

-   Environment variable pattern standardized:

-   `export`` DATABASE_URL=``"postgresql://dennisfotopoulos@localhost:5432/realestatecrm_local"`

-   A local helper script (`localdbstart`) was created to:

    -   Set `DATABASE_URL`

    -   Disable the pager (`PAGER=cat`)

    -   Launch `psql`

```{=html}
<!-- -->
```
-   `localdbstart` was added to `.gitignore`

This eliminated confusion between local vs production databases and
reduced friction during schema inspection.

### 4. Phase 2 Features Completed

#### Transactions: Data Model & Persistence

Phase 2 successfully wired and verified the following fields:

-   Address

-   List price

-   Offer price

-   Expected close date

-   Actual close date

-   Attorney review end date

-   Inspection deadline

-   Financing contingency date

-   Appraisal deadline

-   Mortgage commitment date

All fields were:

-   Properly persisted

-   Editable

-   Verified via direct SQL queries

#### new_transaction Route (Finalized)

-   Rewritten to use **explicit SQL + params**

-   Fixed placeholder mismatches that caused runtime errors

-   Insert now safely persists all milestone fields

-   Redirect flow confirmed:

    -   Create → return to contact page

#### edit_transaction Route (Finalized)

-   Updates all Phase 2 fields

-   Updates `updated_at`

-   Redirects back to the contact page via `next`

-   Confirmed working with live local DB edits

### 5. Contact Page Transactions Card Improvements

The Transactions card on the contact edit page was significantly
improved:

**Key changes:**

-   Removed non-meaningful ID column

-   Address is now the primary link

-   Added:

    -   List price

    -   Offer price

```{=html}
<!-- -->
```
-   Clean, readable layout:

-   `Address | ``Type`` ``| Status | List | Offer | Expected ``Close`` | ``View``/Edit`

**Query improvements:**

-   Ordering refined to prioritize meaningful timelines:

-   `ORDER`` ``BY`` ``COALESCE``(expected_close_date, updated_at) ``DESC`

-   Limited to most recent 5 transactions

-   Explicit acknowledgment that sortable columns will come later (Phase
    3+)

### 6. UX & Workflow Decisions

-   Creation workflow intentionally returns users to the **contact
    page**, not the edit screen

-   Editing is accessed explicitly via "View / Edit"

-   Reinforced principle:

"The dashboard and contact pages mirror transaction data, they do not
edit it"

This aligns with CRM best practices and the project's design philosophy.

### 7. Design Principles Reaffirmed

Several core principles were explicitly reinforced during this session:

-   **Transactions own truth**

-   **Statuses are MLS-realistic**

-   **Dashboard mirrors, never edits**

-   **Flexibility without schema chaos**

-   **Preserve history over deletion**

-   **Do it right once**

-   **No silent refactors**

-   **No phase drift**

The authoritative design document\
`docs/ulysses_transactions_feature_design_v0100.m``d`\
was reaffirmed as the governing contract.

### 8. Phase 2 Closure

Phase 2 was formally closed with:

-   Clean git state

-   Successful persistence verification

-   Commit message:

-   `Close`` Phase ``2``: wire ``transaction`` milestone dates ``and`` improve contact transactions ``table`

-   Changes pushed to:

-   `feature/transactions-v0100-phase2`

### 9. Phase 3 Transition Planning

A detailed **Phase 3 handoff outline** was created, specifying exactly
what must be brought forward:

-   Phase guardrail statement

-   Authoritative design spec reference

-   Local DB context

-   Helper script summary

-   Final versions of routes and queries

-   Relevant templates only

-   Verified DB output

-   Git state confirmation

Phase 3 will proceed on a **new branch**, with Phase 2 treated as
immutable.

### 10. Overall Assessment

This session marked a **clean, disciplined milestone** in the
Transactions feature:

-   Phase 2 achieved functional completeness

-   Technical debt was reduced rather than deferred

-   SQL and routing issues were resolved properly

-   The project's phase-driven methodology was reinforced

-   A calm, focused workflow replaced earlier churn

This sets up Phase 3 for **higher-level synthesis work** (dashboard
aggregation, sorting, visibility across contacts) without destabilizing
the foundation.

## �� Project Evolution Summary

**Date:** December 25, 2025\
**Project:** Ulysses CRM\
**Phase:** Phase 3 completion and transition planning to Phase 4\
**Version:** v0.10.0

## 1. Purpose of This Phase

This chat finalized **Phase 3 (v0.10.0)** and prepared a clean,
disciplined transition into **Phase 4**. The primary objective was to
complete the transaction-centric architecture defined in the v0.10.0
design spec, resolve UI and data integrity issues discovered during
implementation, and explicitly lock scope before moving forward.

A secondary goal was to preserve architectural discipline by avoiding
scope drift, clarifying what was completed versus deferred, and
maintaining a clean separation between **local development** and
**production deployment**.

## 2. Phase 3 North Star (Reaffirmed)

Phase 3 remained anchored to the original design intent:

-   Implement **exactly** what was defined for v0.10.0

-   Do not pull features forward from v0.11.0+

-   Treat transactions as the system's source of truth

-   Preserve historical integrity and avoid destructive operations

-   Avoid schema churn or speculative abstractions

This framing guided all decisions in the chat.

## 3. Features Completed in Phase 3 (v0.10.0)

### Transactions

-   Transactions table fully implemented and functioning locally

-   Transaction deadlines table implemented

-   Status lifecycle finalized and locked using MLS-realistic statuses

-   Buyer and seller transaction filtering implemented
    (`transaction_type = 'buy' | 'sell'`)

-   Transactions surfaced correctly on Buyer and Seller profile sheets

-   Seller transactions bug (uninitialized variable) identified and
    fixed by moving query outside POST block

### Buyer & Seller Sheets

-   Buyer and Seller profile integration with transactions completed

-   Transactions displayed in a dedicated **Transactions tab**

-   Transactions intentionally read-only from profile sheets (View/Edit
    only)

-   Correct scoping by `user_id` enforced

-   UI hierarchy clarified (Overview → Transactions → Professionals →
    Notes → Checklist)

### Checklist (Listings)

-   Checklist initialized automatically for seller profiles

-   Checklist displayed as read-only table on profile

-   Checklist editing moved to modal

-   AJAX updates implemented for checklist items

-   **Option A implemented:** page refresh after modal close using
    `checklistDirty` flag

-   Checklist state persistence after refresh via localStorage tab
    memory

-   Future enhancement explicitly deferred: completion date per
    checklist item

### UI / UX Improvements

-   Tab persistence across reloads using localStorage

-   Clarified that Save buttons appear **only** on editable tabs
    (intentional design)

-   Cleaned up tab-pane hierarchy and div nesting without
    over-optimizing prematurely

-   Rounded corner inconsistencies addressed

-   Clear separation between editable form content and read-only panels

## 4. Items Explicitly Deferred (Out of Phase 3)

The following were intentionally **not implemented** and confirmed as
out of scope for v0.10.0:

-   Dashboard synthesis (confirmed missing)

-   Commission calculations

-   MLS sync

-   Reporting or analytics

-   Buyer ↔ seller transaction linking

-   Automation beyond reminders

-   Checklist completion dates

-   Engagement semantic changes

This explicit deferral prevented silent scope creep.

## 5. Design Principles Reinforced

Several important architectural principles were reaffirmed and enforced:

-   **Transactions are the source of truth**

-   **Dashboard mirrors data, never edits**

-   **Statuses are locked once finalized**

-   **Preserve history over deletion**

-   **Avoid schema chaos**

-   **Do it right once, not twice**

-   **Local-first development discipline**

-   **No production changes during active phase work**

These principles were used repeatedly to evaluate whether a change
belonged in Phase 3 or should be deferred.

## 6. Phase and Version Transitions

-   Phase 3 was conclusively identified as **v0.10.0**

-   Phase 3 was declared **complete and locked**

-   Dashboard synthesis acknowledged as unfinished and formally deferred

-   Phase 4 defined as a **post-v0.10.0 synthesis and UX safety phase**

-   Clear production integration gate established:

    -   v0.10.0 must be merged and verified in production before Phase 4
        feature work

## 7. Phase 4 Planning Outcomes

### Phase 4 Scope (Approved)

-   Dashboard synthesis (read-only)

-   Engagement UX improvements (View/Edit, collapsible details)

-   Follow-up semantics tied to engagements

-   Contact safety fixes (delete, association editing, save behavior)

-   Phone number normalization

-   Pagination or limits on dashboard contact lists

### Phase 4 Non-Goals

-   Automation engines

-   Analytics

-   MLS integrations

-   Commission logic

Phase 4 was positioned as a **clarity, safety, and synthesis phase**,
not a feature explosion.

## 8. Development Context

-   All work performed against **local database
    (`realestatecrm_local`)**

-   No Render or production database connections active

-   Production integration explicitly deferred until Phase 4 planning is
    finalized

## 9. Final State

At the end of this chat:

-   Phase 3 (v0.10.0) is complete, documented, and locked

-   All known bugs discovered during Phase 3 were resolved

-   Deferred items were consciously acknowledged and scoped

-   A clean, repeatable handoff structure for Phase 4 was established

This chat successfully closed a major architectural phase while
preserving long-term maintainability and project momentum.

**Ulysses CRM -- Project Evolution Summary**\
**Date:** December 26, 2025

## 1. Context & Goals

This work session focused on stabilizing and advancing **Ulysses CRM**
during an active transition period involving:

-   Introduction of **multi-user support** (`user_id` scoping)

-   Continued development of **Contacts, Engagements, Interactions, and
    Transactions**

-   Reconciling **schema drift** between intended design and the actual
    PostgreSQL database

-   Restoring functional application flow after multiple 500-level
    errors

The overarching goal was **not to add new features**, but to **reconcile
architecture, schema, and code paths** so the system can move forward
safely.

## 2. Core Problems Encountered

### 2.1 Schema Drift (Primary Issue)

The majority of failures were caused by **code assuming columns or
tables that did not exist**, or had evolved under different names.

Examples:

-   `contacts.user_id` missing in some environments

-   `transactions.contact_id` referenced in code but not originally
    present

-   `interactions.due_at` assumed but missing

-   Confusion between **engagements** vs **interactions** tables

-   Queries referencing `lead_type`, `pipeline_stage`, `price_min`, etc.
    before schema parity

This led to cascading `UndefinedColumn`, `UndefinedTable`, and
`NotNullViolation` errors.

## 3. Key Decisions Made

### 3.1 Stop Dynamic Schema Guessing

Earlier attempts used patterns like:

-   `has_column()`

-   `column_exists()`

-   Conditional SQL fragments

**Decision:**\
These approaches introduced fragility, confusion, and debugging
complexity.

**Direction Chosen:**\
Adopt **explicit schema alignment** rather than runtime guessing.

### 3.2 Explicitly Normalize the Schema

Rather than altering queries to match whatever schema existed, the
session shifted to:

-   **Adding missing columns** directly to the database

-   Aligning tables with the intended long-term data model

Concrete actions taken:

-   Added `due_at`, `is_completed`, `notified` to `interactions`

-   Added `contact_id` to `transactions`

-   Indexed newly added columns

-   Verified schema using \\`d` and \\`dt`

This was a pivotal shift from defensive coding to **schema authority**.

### 3.3 Clarified Table Roles

A critical conceptual clarification was reinforced:

-   **engagements**

    -   Rich communication log

    -   Supports transcripts, summaries, outcomes

    -   Scoped by `user_id` and `contact_id`

```{=html}
<!-- -->
```
-   **interactions**

    -   Lightweight task/reminder/follow-up system

    -   Supports due dates and completion state

    -   Powers reminders and ICS feeds

This distinction resolved confusion and explained why both tables
legitimately exist.

### 3.4 Cursor Consistency

Multiple cursor factories were being mixed:

-   `RealDictCursor`

-   `DictCursor`

-   default cursors

**Decision:**\
Normalize cursor usage to avoid subtle runtime errors and missing-key
issues.

Result:

-   Standardized cursor creation

-   Confirmed compatibility with dictionary-style row access
    (`row["column"]`)

## 4. Feature Status

### Added / Enabled

-   Engagement logging UI (calls, texts, emails, transcripts)

-   Transactions displayed and editable within Contact view

-   Schema support for reminders via `interactions`

-   Contact-to-transaction relationship made explicit

### Deferred / Not Touched

-   Dashboard reminders UI polish

-   ICS/calendar enhancements beyond schema support

-   Any refactoring for performance or abstraction

-   New feature work (explicitly avoided)

## 5. Design Principles Reinforced

This session strongly reinforced several core project principles:

1.  **Schema-first development**

    -   The database is the contract

    -   Code should not "guess" structure

```{=html}
<!-- -->
```
1.  **No silent refactors**

    -   Changes must be explicit and inspectable

    -   Verified via `psql`, not assumptions

```{=html}
<!-- -->
```
1.  **Single source of truth**

    -   One canonical schema per environment

    -   Avoid conditional logic for production data models

```{=html}
<!-- -->
```
1.  **Phase discipline**

    -   This work was corrective, not expansive

    -   Feature velocity paused to regain stability

## 6. Phase / Version Implications

-   This work represents a **stabilization checkpoint**, not a formal
    new phase

-   It bridges earlier experimental multi-user work into a
    **production-safe foundation**

-   Sets the stage for resuming planned phases (Dashboard evolution,
    Tasks, Phase 5+)

No version bump was finalized during this session, but the system now
supports moving forward cleanly.

## 7. End State at Pause

At the stopping point:

-   Database schema was verified and corrected

-   Core tables exist and align with code intent

-   Remaining errors are now **predictable and fixable**, not structural

-   The system is no longer in a cascading-failure state

Pause was appropriate and intentional.

## 8. Clear Next Steps (When Resuming)

1.  Remove any remaining schema-detection helpers (`column_exists`,
    etc.)

2.  Audit remaining queries against actual schema

3.  Verify `/api/reminders/due` end-to-end

4.  Resume Phase roadmap with confidence

**Summary Judgment:**\
This session was difficult but necessary. It transformed a fragile,
assumption-driven system into a schema-grounded platform ready for
continued development.

The pause was the right call.

**Ulysses CRM --- Project Evolution Summary**\
**Date:** December 26, 2025

## 1. Overall Context and Goals

This work session focused on **stabilizing and completing Phase 4 of
Ulysses CRM**, with particular emphasis on:

-   Protecting **production data integrity**

-   Completing and validating **Transactions (v0.10.0)**

-   Resolving **Seller Profile → Transactions workflow issues**

-   Finalizing **versioning discipline for production builds**

-   Preparing a **clean handoff into Phase 4.5 / Phase 5 planning**

A recurring theme throughout the session was *deliberate, step-by-step
execution* to avoid regressions, silent data corruption, or ambiguous
workflow behavior.

## 2. Production Safety & Environment Discipline

### Key Decisions

-   **Explicit separation of LOCAL vs PROD databases** was enforced and
    repeatedly verified using:

    -   `SELECT current_database(), current_user;`

```{=html}
<!-- -->
```
-   All schema changes affecting production were:

    -   Verified before execution

    -   Run manually and deliberately

    -   Confirmed via \\`d+` inspection afterward

### Design Principle Reinforced

**Production data is sacred.**\
No shortcuts, no assumptions, no "it should be fine."

## 3. Interactions Table: user_id Migration (Completed)

### What Was Done

-   Added `user_id` to `interactions`

-   Backfilled `user_id` from `contacts`

-   Enforced:

    -   `NOT NULL`

    -   Foreign key constraint to `users(id)`

    -   Index on `(user_id, happened_at DESC)`

### Result

-   Interactions are now fully scoped per-user

-   Query performance and data isolation improved

-   Migration executed successfully in production

### Deferred

-   Refactoring all legacy interaction insert/select code paths was
    intentionally deferred once core integrity was achieved and
    verified.

## 4. Transactions Feature (v0.10.0) --- Finalized

### Major Issue Identified

**Seller Profile → New Transaction → Save**

-   Transaction was being created

-   Transaction appeared on Contact page

-   **Did NOT appear in Seller Profile Transactions tab**

### Root Cause

-   Transactions created from Seller Profile were defaulting to
    `transaction_type = 'buy'`

-   Seller Profile query explicitly filtered:

-   `transaction_type = 'sell'`

-   This mismatch caused valid transactions to be excluded from the
    Seller view

## 5. Transaction Type Flow Fix (Completed)

### Fix Implemented

1.  **Explicit propagation of `transaction_type=sell`** from Seller
    Profile:

2.  `href="``{``{`` url_for('new_transaction', contact_id=contact_id, transaction_type='sell', next=request.path) ``}``}``"`

3.  **Default handling in `new_transaction` route**:

4.  `default_tx_type = request.args.get("transaction_type")`

5.  `transaction_type = form_value or default_tx_type or "sell"`

6.  **Transaction form UI updated** to respect:

    -   Existing transaction type (edit mode)

    -   Passed default (new mode)

    -   Sensible fallback (`sell`)

### Outcome

-   Transactions created from Seller Profile now:

    -   Persist correctly

    -   Display immediately in Seller Profile

```{=html}
<!-- -->
```
-   This fix was verified in production

-   User confirmed success

## 6. Seller Profile Transactions Tab (Stabilized)

### Confirmed Working

-   Transactions render correctly

-   "+ New Transaction" preserves context and returns properly

-   Badge count reflects correct number of seller transactions

-   No unintended side effects on Buyer flows

## 7. Versioning System (Resolved & Locked)

### Problem Encountered

-   Production deploy failed due to:

-   `ModuleNotFoundError: No module named 'version'`

-   Caused by incorrect file placement and Git tracking confusion

### Resolution

-   `version.py` placed at project root

-   Imported cleanly by `app.py`

-   Footer displays correct version string

-   Production deploy succeeded

### Policy Established

**From this point forward, every production build must increment the
version number.**

This policy is:

-   Explicit

-   Agreed upon

-   Considered "already set up and enforced"

## 8. Phase Status & Version Transitions

### Clarified

-   Work was **already inside Phase 4**

-   Therefore:

    -   Next work is **Phase 4.5** or **Phase 5**

    -   Not a new Phase 4

### Version Mapping

-   **v0.10.0**\
    ✅ Transactions feature complete and stable

-   **v0.11.0 (planned)**\
    �� Dashboard + Tasks / Follow-ups rework

## 9. Dashboard & Follow-Up Conceptual Rework (Planned, Not Implemented)

### Issues Identified

-   "Overdue Follow-ups" lack context

-   `next_followup` field is ambiguous

-   Follow-ups vs Tasks vs Engagements are blurred

### Conceptual Direction Agreed

-   Engagements are the **source of truth**

-   Proposed enhancements:

    -   Follow-up checkbox on engagement

    -   Completed checkbox on engagement

    -   Ability to record:

        -   Ad-hoc calls

        -   Incoming calls

        -   Non-task-based interactions

```{=html}
<!-- -->
```
-   Dashboard should emphasize:

    -   Upcoming actions

    -   Recently completed work

    -   Context-rich activity, not raw dates

### Status

-   **Explicitly deferred**

-   To be addressed in **v0.11.0**

-   Requires clean handoff and focused design session

## 10. Handoff Preparation

### What Was Requested for the Next Chat

-   A **project folder / file tree** (preferred via local terminal)

-   Clean continuity into:

    -   Phase 4.5 / Phase 5

    -   v0.11.0 planning

### Tooling Recommendation

    tree -L 3 -I ".venv|__pycache__|.git"

## 11. Key Principles Reinforced

-   No silent refactors

-   No production guesses

-   Context must flow through URLs and forms

-   Engagements should tell the story, not just dates

-   Version numbers matter and must be truthful

-   Phase boundaries are respected and documented

**End of Summary --- December 26, 2025**

## Ulysses CRM -- Project Evolution Summary

**Date:** December 27, 2025\
**Phase:** Phase 4.5\
**Release:** v0.10.5 (production)

### Primary Goals of This Session

-   Improve **UI consistency** across core application views.

-   Finalize and deploy **Transactions split-view enhancements**.

-   Normalize page structure across Contacts and Open Houses.

-   Reduce layout drift caused by inconsistent container usage.

-   Prepare the codebase for disciplined, checklist-driven UI evolution
    going forward.

### Key Decisions Made

1.  **Transactions Split View Finalized**

    -   Left pane intentionally reduced to:

        -   Address

        -   Type

        -   Status

        -   Select action

    ```{=html}
    <!-- -->
    ```
    -   All monetary and timeline details moved to the **right pane**,
        which is now the primary detail surface.

    -   "Open" column confirmed obsolete and removed.

    -   Selected transaction styling refined (left border highlight).

    -   Right pane explicitly positioned as the expandable future
        surface for transaction intelligence.

```{=html}
<!-- -->
```
1.  **Layout Consistency Standardized**

    -   Removed nested `.container` wrappers from `edit_contact.html`,
        resolving margin and alignment issues.

    -   Confirmed that base layout should control global spacing, not
        individual templates.

    -   Adopted consistent page headers:

        -   Clear page title (`h2`)

        -   Muted descriptor line beneath (with controlled indentation
            when appropriate).

    ```{=html}
    <!-- -->
    ```
    -   Scripts confirmed safe to remain within content blocks as long
        as structure remains consistent.

```{=html}
<!-- -->
```
1.  **Open Houses Views Brought Into Alignment**

    -   Updated:

        -   `openhouses/list.html`

        -   `openhouses/detail.html`

        -   `openhouses/new.html`

    ```{=html}
    <!-- -->
    ```
    -   Removed standalone containers in favor of shared layout
        structure.

    -   Unified heading language ("Open House Details", "Create a New
        Open House").

    -   Standardized card usage and spacing.

    -   Confirmed this approach should be applied to remaining legacy
        views.

```{=html}
<!-- -->
```
1.  **Versioning Decision**

    -   Changes qualify as a **minor but meaningful UI/UX release**.

    -   Version incremented and pushed as **v0.10.5**.

    -   Phase remains **4.5**, with additional scoped work still
        pending.

### Features Added or Improved

-   Transactions split view (refined and stabilized).

-   UI consistency across Contacts and Open Houses.

-   Cleaner transaction navigation and selection behavior.

-   Improved visual hierarchy and spacing throughout affected templates.

-   Clearer page identity through improved headings and descriptors.

### Features Explicitly Deferred

-   Follow-ups tab content expansion.

-   Additional transaction intelligence fields in the right pane
    (planned next).

-   Broader engagement UX refinements.

-   Commission engine and other post-v1.0 features (unchanged deferral).

### Design Principles Established or Reinforced

-   **Consistency over cleverness**: shared structure matters more than
    per-page tweaks.

-   **One container rule**: layout containers belong in base templates,
    not child views.

-   **Split views must have a clear hierarchy**:

    -   Left = navigation / selection

    -   Right = detail / context / future expansion

```{=html}
<!-- -->
```
-   **UI debt must be prevented, not repaid later**.

-   Versioning should reflect user-visible improvements even when schema
    is unchanged.

### New Guardrails Identified

-   A formal **UI Consistency Checklist** is now required to prevent
    drift.

-   Future UI work must be evaluated against established layout patterns
    before merging.

-   Contacts should default to **Engagements**, not Transactions, when
    opened (to be implemented next).

### State at Close of Session

-   All changes committed and pushed to production.

-   v0.10.5 live.

-   Codebase materially more consistent and easier to extend.

-   Clear direction set for Phase 4.5 continuation and next-chat handoff
    documentation.

This session represents a **structural cleanup milestone**, not just a
cosmetic pass. You reduced future friction and created a UI language
worth defending.

**Ulysses CRM -- Project Evolution Summary**\
**Date:** December 27, 2025

### Context and Goal

This discussion focused on whether Ulysses CRM could ever be marketable
beyond personal use and, more importantly, what architectural and
ethical guardrails would be required to protect user data if additional
agents were allowed onto the platform. The intent was not to pivot
Ulysses into a product, but to ensure that current decisions do not
close the door on future optional sharing or limited commercialization.

### Key Conclusions

#### 1. Marketability Is Possible, but Not the Goal

-   Ulysses is being built as a personal, agent-first system, not as a
    SaaS product.

-   Ironically, this personal-first approach is what makes it
    potentially marketable.

-   No immediate changes to roadmap or scope were made to support
    commercialization.

-   Any future sharing would likely begin informally with trusted
    colleagues rather than public distribution.

**Decision:**\
Marketability is acknowledged as a future possibility, not a present
objective. No productization work begins now.

#### 2. Core Design Principle Established: Absolute Data Ownership

A foundational principle was clearly articulated and locked in:

-   Each user fully owns their contacts and data.

-   User data is fully isolated at the application level.

-   Even the platform administrator does not browse, review, or use
    another agent's contact list.

-   Admin authority exists solely for system integrity, recovery, and
    user-directed offboarding.

This principle was formalized in a written **Privacy and Data Ownership
Promise** to ensure long-term consistency between intent and
implementation.

#### 3. Admin Role Defined as "Escrow," Not Visibility

A clear distinction was established between system administration and
data access:

-   Admins manage infrastructure, uptime, billing, and account
    lifecycle.

-   Admins do not have routine UI or query access to user contacts or
    records.

-   Legitimate admin actions are limited to:

    -   Triggering user exports

    -   Restoring data after accidental deletion

    -   Permanently deleting user data on request

```{=html}
<!-- -->
```
-   Any recovery or intervention is explicit, logged, and
    user-initiated.

This protects both users and the platform owner ethically and
professionally.

#### 4. Data Lifecycle Standards Reinforced

Future-facing but conceptually locked principles include:

-   Soft deletes with a recovery window to protect against accidental
    loss.

-   Easy, user-initiated full data export at any time.

-   Clean exit path allowing users to download and permanently delete
    their data.

-   Audit logging for admin recovery or deletion actions.

These standards were defined conceptually but deferred for
implementation.

#### 5. Team Concept Identified and Explicitly Deferred

The need for a future "team" model was acknowledged, along with its
complexity.

Key open questions identified:

-   Who owns contacts in a team context: the lead, the agent, or both?

-   How shared visibility should work without compromising trust or
    portability.

Three potential models were outlined:

-   Agent-owned with optional sharing

-   Team-owned (brokerage-style)

-   Dual ownership (acknowledged as complex and risky)

**Decision:**\
Team functionality and data ownership rules are explicitly deferred to a
future design phase and will not be bolted onto the current system.

### Phase and Roadmap Impact

-   No phase transition occurred.

-   No version number changes were made.

-   Current development continues uninterrupted along the existing path
    defined in the parallel development chat.

-   This conversation serves as a **conceptual guardrail**, not a scope
    expansion.

### Lasting Impact

This discussion:

-   Reinforced Ulysses' ethical foundation.

-   Established non-negotiable data privacy principles.

-   Ensured future scalability without compromising trust.

-   Protected the project from accidental product drift.

Ulysses remains a personal-first system, with optional future paths kept
intentionally open but firmly controlled.

# Ulysses CRM -- Phase 4.5 Progress & Decisions

**Date:** December 29, 2025\
**Phase:** Phase 4.5 (in progress)\
**Version Context:** 0.10.8 (paused / rolled back in production)

## 1. Primary Goals of This Session

-   Advance **Phase 4.5 UX refinements**, especially around:

    -   Engagements vs Follow-ups clarity

    -   Contact-centric follow-ups

    -   Transactions split-view improvements

```{=html}
<!-- -->
```
-   Resolve navigation consistency issues across tabs

-   Prepare the system for **safe iteration** before further production
    releases

-   Explicitly avoid locking in premature schema changes

## 2. Features Implemented or Stabilized (Local)

### Engagements

-   Engagement create/edit/delete confirmed stable.

-   Follow-up fields fully functional:

    -   `requires_follow_up`

    -   `follow_up_due_at`

    -   `follow_up_completed`

```{=html}
<!-- -->
```
-   Navigation fixes:

    -   Save/Cancel from Edit Engagement reliably returns to the correct
        Contact tab using `next`, `return_tab`, and `return_to`.

    -   Hash-based tab routing respected over query parameters.

```{=html}
<!-- -->
```
-   Engagements tab behavior finalized for Phase 4.5.

### Contacts → Follow-ups Tab

-   Follow-ups tab now renders correctly per contact.

-   Follow-ups display only engagements that:

    -   Are marked as follow-ups

    -   Have a due date

```{=html}
<!-- -->
```
-   "Open" actions route correctly to Edit Engagement and back to the
    Follow-ups tab.

-   UI intentionally kept simple while mental model is evaluated.

### Contacts → Transactions (Split View)

-   Transactions tab significantly enhanced:

    -   Left panel: recent transactions selector.

    -   Right panel: Transaction Details with a defined row structure:

        1.  Title + View/Edit button

        2.  Address

        3.  Type \| Status (color-coded: Active green, Pending yellow,
            Closed blue)

        4.  List / Offer / Closed prices

        5.  Expected Close + next 1--2 milestones

```{=html}
<!-- -->
```
-   Transaction milestones surfaced from `transaction_deadlines`.

-   UX deemed acceptable for Phase 4.5.

### Navigation & UI Consistency

-   Hash-based tab activation prioritized over `tx_id`.

-   Transactions tab auto-opens when `tx_id` is present.

-   Minor UI polish applied (e.g., logo height increased from 50px to
    60px).

## 3. Key Decisions Made

### Follow-ups vs Engagements

-   **Intentional pause** on expanding follow-ups logic.

-   Confirmed mental model:

    -   Engagements = historical record

    -   Follow-ups = actionable items with due dates

```{=html}
<!-- -->
```
-   Not all engagements marked as follow-ups must appear unless they
    have a due date.

-   Decision deferred to allow real-world usage feedback.

### Production Safety

-   **Production deployment rolled back** via Render.

-   No further production changes until schema/code divergence is
    resolved.

-   Phase 4.5 work continues **locally only**.

## 4. Schema & Data Model Findings (Critical)

### Engagement Follow-ups

-   `engagements.follow_up_due_at` is correct and consistent across
    local and production.

-   No immediate action required.

### Transaction Deadlines (Problem Area)

-   Local database was modified to include:

    -   `label`

    -   `due_at`

```{=html}
<!-- -->
```
-   Production database still uses:

    -   `name`

    -   `due_date`

```{=html}
<!-- -->
```
-   Codebase currently references **both** styles in different places.

-   This mismatch makes a production release unsafe.

### Decision

-   Do **not** resolve this during this session.

-   Explicitly defer schema reconciliation to a focused follow-up
    session.

## 5. Deferred Work / Next Logical Steps

-   Decide schema strategy for `transaction_deadlines`:

    -   **Option A (preferred):** Revert local DB to match production
        (`name`, `due_date`)

    -   **Option B:** Forward-migrate production (explicitly deferred)

```{=html}
<!-- -->
```
-   Remove mixed references (`label`, `due_at`) once a decision is made.

-   Re-test Transactions milestones after reconciliation.

-   Only then consider a new production release (likely ≥ 0.10.9).

## 6. Phase & Version Status

-   **Phase 4.5 remains active**

-   **v0.10.8 deployment paused and rolled back**

-   No Phase 5 work started

-   No production schema changes approved

## 7. Design Principles Reinforced

-   Production safety over speed.

-   Schema changes require explicit migration strategy.

-   UX iteration before locking data models.

-   Clear separation of:

    -   Engagement history

    -   Follow-ups (actionable)

    -   Transaction milestones (deal-centric)

## 8. Outcome

This session successfully:

-   Advanced Phase 4.5 UX meaningfully

-   Clarified mental models without premature decisions

-   Prevented a risky production deployment

-   Set up a clean, focused next step for schema reconciliation

**Status:** Stable stopping point, safe to resume in a new chat.

## Ulysses CRM -- Phase 4.5 Close-Out & Transition Summary

**Date:** December 30, 2025

### 1. Goals of This Phase

The primary goal of this work was to **stabilize and complete Phase
4.5** before moving into Phase 5, ensuring that:

-   Production and local schemas were reconciled safely

-   Engagements and transaction workflows behaved predictably

-   The Transactions split-view UI was functional and intuitive

-   No production schema changes were introduced late in the phase

-   The system was left in a clean, deployable, and extensible state

A secondary goal emerged mid-phase: clarifying the long-term
**relationship between Engagements, Follow-ups, Deadlines, and Tasks**
without prematurely implementing Phase 5 features.

### 2. Key Decisions Made

#### 2.1 Transaction Deadlines Schema Reconciliation

-   **Decision:** Revert Phase 4.5 to use `transaction_deadlines.name`
    and `due_date` only.

-   **Rationale:**

    -   Production did not contain `label` or `due_at`

    -   Forward-migrating production was deemed too risky for Phase 4.5

```{=html}
<!-- -->
```
-   **Outcome:**

    -   Local schema was aligned with production

    -   All code paths standardized on:

        -   `name`

        -   `due_date`

```{=html}
<!-- -->
```
-   **Design principle reinforced:**\
    *No late-phase production schema changes without explicit migration
    strategy and approval.*

#### 2.2 Next Milestones Logic (Critical Fix)

-   **Problem identified:**\
    Built-in transaction milestone fields (inspection, appraisal,
    financing, etc.) did not appear in "Next Milestones," while manually
    added deadlines did.

-   **Decision:**\
    Do **not** duplicate built-in milestones into
    `transaction_deadlines`.

-   **Solution implemented:**

    -   Merge two sources at runtime:

        1.  User-entered `transaction_deadlines`

        2.  Derived milestones from `transactions` date fields

    ```{=html}
    <!-- -->
    ```
    -   Sort combined list by date

    -   Display top 1--2 upcoming items

```{=html}
<!-- -->
```
-   **Outcome:**

    -   Manual and system deadlines now coexist cleanly

    -   No schema changes required

```{=html}
<!-- -->
```
-   **Design principle reinforced:**\
    *Derived data belongs in code, not the database.*

#### 2.3 Engagements vs Follow-ups Conceptual Clarification

-   **Acknowledgement:**\
    The existing Follow-ups implementation is serviceable but not final.

-   **Intentional pause:**\
    No refactor was performed in Phase 4.5.

-   **Key insight:**

    -   Engagements are the **source of truth** for interactions

    -   Follow-ups and Tasks should emerge from Engagements, not compete
        with them

```{=html}
<!-- -->
```
-   **Decision:**\
    Defer structural changes to Phase 5.

### 3. Features Added or Stabilized in Phase 4.5

#### Engagements

-   Stable create, edit, delete

-   Follow-up fields functioning as designed

-   Tab routing and return navigation fixed

-   Engagements tab reliably opens by default

#### Transactions (Split-View UI)

-   Left panel: transaction selector

-   Right panel: transaction detail view

-   "Next Milestones" now correctly displays:

    -   Manual deadlines

    -   Built-in transaction milestones

```{=html}
<!-- -->
```
-   Deadline add/edit/toggle/delete fully functional

#### Navigation & UX

-   Hash-based tab routing works correctly

-   `tx_id` selection respected without forcing redirects

-   Cancel vs Save behavior fixed in transaction forms

### 4. Production Deployment & Safety

-   Auto-deploy was temporarily disabled and manually re-enabled

-   Production rollback was confirmed before redeployment

-   A **safety stop** in `get_db()` correctly prevented misconfigured
    environments from connecting to production

-   Final deployment succeeded after correcting environment variable
    assumptions

**Outcome:**\
Phase 4.5 deployed cleanly with **low production risk** and no data
loss.

### 5. Items Explicitly Deferred to Phase 5

-   Full re-architecture of Follow-ups into Tasks

-   Task associations with:

    -   Engagements

    -   Transactions

    -   Professionals

```{=html}
<!-- -->
```
-   Document attachment strategy (Drive / iCloud / link-based)

-   Outbound messaging (SMS / email) and opt-out compliance

-   Transaction-level context or narrative notes field

These were documented separately in Phase 5 design documents.

### 6. Design Principles Reinforced

1.  **Phase discipline matters**\
    Late-phase changes must be stabilization, not expansion.

2.  **Schema conservatism**\
    Code should adapt before databases do.

3.  **Separation of concerns**

    -   Engagements = historical record

    -   Deadlines = date-driven checkpoints

    -   Tasks (future) = actionable work

```{=html}
<!-- -->
```
1.  **Derived data belongs in code**\
    Avoid duplicating canonical fields across tables.

2.  **Production safety over convenience**\
    Guardrails preventing accidental prod access are working as
    intended.

### 7. Phase & Version Transition

-   **Phase 4.5:** Functionally complete and production-stable

-   **Recommended version:** v0.10.9 (or equivalent final Phase 4.5 tag)

-   **Next phase:** Phase 5

    -   Focus: Tasks, follow-ups re-conceptualization, outbound
        messaging, document linking

    -   To be started in a **new chat with a clean scope reset**

### 8. Overall Outcome

Phase 4.5 successfully closed with:

-   No unresolved schema mismatches

-   No blocking UX defects

-   A clear architectural runway into Phase 5

The system is now in a **strong, intentional state** for higher-level
workflow features without needing to undo or refactor Phase 4.5 work.

**Ulysses CRM -- MLS / IDX / Listing Distribution Discussion**\
**Date:** December 30, 2025

### Purpose of this conversation

The goal of this discussion was to explore whether and how Ulysses CRM
could support sending MLS listings to clients, with specific reference
to existing IDX usage, third-party platforms like Ylopo, and long-term
architectural direction for the CRM.

## Key Questions Explored

-   Can Ulysses send MLS listings directly to clients?

-   How does Ylopo handle MLS listings and automation?

-   Is API integration with Ylopo feasible?

-   Does existing IDX access through the local MLS and website widgets
    change what is possible?

-   Should this capability be implemented now or deferred?

## Key Findings & Decisions

### 1. MLS and IDX Reality Check

-   MLS data redistribution is contractually restricted.

-   Platforms like Ylopo succeed because they are MLS-licensed,
    IDX-native systems where listings live inside approved environments.

-   Ulysses CRM is intentionally MLS-agnostic and relationship-centric,
    not a listings engine.

**Decision:**\
Ulysses will not attempt to ingest, query, or replicate MLS listing data
directly.

### 2. Ylopo Integration Feasibility

-   Ylopo does **not** expose MLS or listing APIs for external CRMs.

-   Limited integrations are available for:

    -   Lead/contact syncing

    -   High-level behavioral signals

```{=html}
<!-- -->
```
-   Listings, searches, and alerts remain locked inside Ylopo's IDX
    ecosystem.

**Decision:**\
A deep or bidirectional listing integration with Ylopo is not realistic
or desirable.

### 3. Impact of Existing IDX Subscription & Website Widgets

-   The user already has MLS-approved IDX access via their local MLS.

-   Listings are displayed on the user's own website through IDX
    widgets/iframes.

-   Compliance, disclaimers, and attribution are already handled by the
    IDX provider.

**Key Insight:**\
While IDX widgets are data black boxes, they enable a compliant
**link-based strategy** where Ulysses can reference listings without
touching MLS data.

### 4. Strategic Middle Path Identified

Rather than full IDX replication or MLS ingestion, a **hybrid approach**
was defined:

-   IDX remains the **display and compliance layer**

-   Ulysses becomes the **intelligence, memory, and relationship layer**

This approach avoids MLS risk while still supporting meaningful "send
listings" workflows.

## Features Explicitly Deferred (Pinned for Phase 6)

The following were **intentionally deferred** and pinned for **Phase 6**
development:

### Phase 6 Concept: IDX + Email Integration

-   Introduce a **"Listing Share" engagement type**

    -   Store IDX listing URLs

    -   Capture address, price snapshot, notes, and client reaction

```{=html}
<!-- -->
```
-   Pair listing shares with **outbound email integration**

    -   Send IDX links directly from Ulysses

    -   Automatically log sent emails as engagements

```{=html}
<!-- -->
```
-   Support **client-specific IDX links**

    -   Saved searches or filtered IDX pages tied to contacts

```{=html}
<!-- -->
```
-   Maintain strict MLS/IDX compliance

    -   No MLS data stored or queried inside Ulysses

This pairing was identified as a natural, high-value enhancement once
the core CRM and engagement workflows are fully mature.

## Design Principles Reinforced

-   **Compliance first:** No shortcuts with MLS or IDX rules.

-   **Separation of concerns:**

    -   IDX handles listings and compliance

    -   Ulysses handles relationships, context, and continuity

```{=html}
<!-- -->
```
-   **Human context over raw analytics:**\
    Tracking why a client liked or rejected a listing is more valuable
    than raw click data.

-   **Phased development discipline:**\
    Listing distribution is an amplifier feature, not a foundation
    feature, and belongs in a later phase.

## Phase & Version Implications

-   No immediate version change.

-   No Phase 5 scope expansion.

-   Clear pin placed for **Phase 6** to revisit IDX-linked listing
    sharing combined with email workflows.

## Final Outcome

This conversation clarified that Ulysses does not need to become a
Ylopo-style listings platform to deliver value. By leveraging existing
IDX access and deferring a clean, compliant listing-share + email
feature to Phase 6, Ulysses preserves its core identity while opening a
strong future enhancement path.

**Status:** Documented, pinned, and intentionally deferred.

## Ulysses CRM --- Layout & Footer Debugging Summary

**Date:** January 2, 2025

### Context & Goal

This session focused on diagnosing and correcting a layout issue in
**`edit_contact.html`** where the footer did not span full width and
appeared visually constrained compared to other pages (e.g., Contacts
list). The goal was to identify whether the issue stemmed from
`base.html`, `edit_contact.html`, or improper interaction between the
two, and to establish a durable pattern to prevent similar regressions.

### Root Cause Identified

The footer issue was **not caused by `base.html`** and **not by a
missing {`% endblock %``}`**, but by **misaligned closing `<div>` tags
inside the `pane-transactions` tab** of `edit_contact.html`.

Specifically:

-   The **Transactions tab** (`pane-transactions`) opened multiple
    nested containers:

    -   A Transactions card (`.card`)

    -   Its card body (`.card-body.p-0`)

```{=html}
<!-- -->
```
-   The closing tags at the bottom incorrectly closed the card and card
    body but **failed to explicitly close the tab pane itself**

-   This caused the browser to perform **DOM repair**, effectively
    nesting the footer inside a container (`.card` / `.container`),
    breaking its full-width layout

### Key Fix Implemented

The Transactions section was corrected to ensure **explicit, correctly
ordered closures**:

**Required closure order:**

1.  Close `.card-body.p-0`

2.  Close `.card.mt-3` (Transactions card)

3.  Close `.tab-pane#pane-transactions`

4.  Close `.tab-content`

5.  Close outer `.card-body` and `.card`

This restored the correct DOM hierarchy and allowed the footer to render
as a direct child of `<body>`.

### Structural Improvement Adopted

A key architectural decision was made and implemented:

#### ✅ Separation of concerns between layout and scripts

-   {`% block content %``}` now contains **only HTML layout**

-   All page-specific JavaScript was moved into
    {`% block extra_scripts %``}` (defined in `base.html`)

-   This prevents scripts from obscuring visual inspection of container
    boundaries and reduces the risk of accidental layout corruption

**Canonical pattern established:**

    </div>  <!-- final layout container -->

    {% endblock %}

    {% block extra_scripts %}

    <script>...</script>

    {% endblock %}

### Design Principles Reinforced

-   **Explicit container closures are mandatory** in complex tabbed
    layouts

-   **Browser DOM repair is a silent failure mode** that must be guarded
    against

-   **Base layout integrity (`base.html`) should be trusted and
    preserved**

-   Page templates should:

    -   Close all structural markup before ending
        {`% block content %``}`

    -   Never interleave scripts with layout containers

### Features Added or Deferred

-   No new features were added

-   No functionality was deferred

-   This was a **stability and correctness fix** with architectural
    implications

### Phase / Version Notes

-   No phase transition occurred

-   This work reinforces **Phase 4.5 UI stability and layout
    correctness**

-   The fix is compatible with current and future versions (including
    post-v1.0 work)

### Outcome

The footer now renders correctly across pages, layout integrity is
restored, and a safer, repeatable template structure has been
established for complex views such as Contacts with tabs and split-pane
layouts.

This session materially improved the **long-term maintainability and
reliability** of Ulysses CRM's UI architecture.

# Ulysses CRM --- Phase 5 Development Summary

**Date:** January 2, 2025\
**Phase:** Phase 5 (Tasks & Workflow Integration)\
**Version context:** v0.10.9 (LOCAL)

## 1. Primary Goals of This Phase Segment

The goals addressed in this session were:

1.  **Complete Phase 5 Tasks feature foundations**

2.  **Integrate Tasks cleanly into the Contact workflow**

3.  **Eliminate numeric ID--based UX in favor of human-readable,
    searchable selectors**

4.  **Ensure layout, container, and tab behavior remained stable while
    extending functionality**

5.  **Prepare the codebase for further Phase 5 expansions without
    regressions**

## 2. Key Features Implemented and Verified

### 2.1 Tasks Feature (Core CRUD)

The Tasks system is now fully functional and stable, including:

-   Task listing with status filters

-   Task creation, viewing, editing

-   Task completion, snoozing, reopening, and cancelation

-   Ownership and permission enforcement

-   Flash messaging and safe redirects

This confirmed Tasks as a **first-class workflow object** within Ulysses
CRM.

### 2.2 Contact → Task Integration (Major Phase 5 Win)

A major Phase 5 milestone was achieved:

-   The **numeric "Contact ID" input** in the Task form was fully
    replaced with a:

    -   Search-as-you-type contact selector

    -   Live dropdown results

    -   Click-to-select behavior

    -   Hidden `contact_id` storage

    -   Clear/reset option

This implementation:

-   Reuses the existing `/contacts/search` endpoint

-   Matches the UX pattern used in **Associated Contacts**

-   Supports **prefill when launching Tasks from a Contact page**

-   Eliminates the "Contact #n" problem in task creation

This work is **complete and stable**.

### 2.3 Tasks List Display Polishing

Tasks list rendering was improved to display **contact names instead of
numeric IDs** by:

-   Building a `contact_id ``→`` display_name` map in the route

-   Using safe fallbacks only when a name cannot be resolved

This reinforced the design principle that **IDs should never leak into
user-facing UI**.

## 3. Debugging and Stability Work

### 3.1 Container / Layout Issues

During this session:

-   A broken `<div>` nesting issue in `edit_contact.html` caused layout
    and scroll problems

-   The issue was traced to overlapping container assumptions

-   Resolution confirmed:

    -   `base.html` owns the primary `.container`

    -   Child templates must not re-wrap improperly

```{=html}
<!-- -->
```
-   Tabs, cards, and engagement views were restored to stable behavior

This reinforced the rule:

**Layout structure must be owned at one level only.**

### 3.2 Script Organization Discipline

The project's JS organization was reaffirmed:

-   Global JS belongs in `base.html`

-   Page-specific JS belongs in {`% block extra_scripts %``}`

-   No inline duplication or implicit execution

This kept new Task-related JS isolated and predictable.

## 4. Design Principles Reinforced

Several important design principles were reaffirmed:

1.  **Human-first UI**

    -   Users search by names, not IDs

    -   IDs remain an internal implementation detail

```{=html}
<!-- -->
```
1.  **Pattern reuse**

    -   The Contact search selector became the canonical model

    -   Future selectors should follow the same structure

```{=html}
<!-- -->
```
1.  **No regression tolerance**

    -   Completed work must not be re-opened unless broken

    -   The chat explicitly identified areas that were *done* and
        off-limits

```{=html}
<!-- -->
```
1.  **Incremental phase discipline**

    -   Phase 5 work stayed scoped

    -   Deferred items were clearly identified rather than
        half-implemented

## 5. Deferred / Remaining Phase 5 Work

The following items were **intentionally deferred** to the next session:

### 5.1 Replace Numeric Selectors for Other Relationships

The following Task fields are still numeric and need the same
live-search UX:

-   `transaction_id`

-   `engagement_id`

-   `professional_id`

Planned approach:

-   Create search endpoints for each entity

-   Reuse the Contact selector JS pattern

-   Optionally generalize into a reusable "entity search selector"
    component

No work on these fields was started yet, by design.

## 6. Phase Status at Close of This Chat

-   Phase 5 is **actively in progress**

-   Tasks + Contact integration is **complete**

-   Codebase is stable at **v0.10.9 LOCAL**

-   The session concluded with a **formal handoff decision** to start a
    new chat to avoid context pollution

## 7. Transition Note

This chat was intentionally ended due to length and context saturation.\
A formal **Phase 5 handoff document** was created to ensure continuity
in the next chat.

The next session will resume Phase 5 by extending the search-based
selector pattern to Transactions, Engagements, and Professionals.

## Ulysses CRM Phase 5 Tasks UX and Modal Work

**Date:** January 3, 2025

### Goals

-   Improve Tasks UX consistency across the app (button styling,
    placement, actions).

-   Add "contextual wildcard display" on the Task view page so related
    data is shown even when not explicitly selected.

-   Convert Task create/edit from full-page forms to modal-based forms,
    similar to the "Add New Contact" modal pattern.

-   Resolve modal-specific issues around scripts, initialization, and
    dynamic field population.

### Key Decisions

-   **Contextual wildcard display (kept for now):**\
    In Task view, if a specific Transaction/Engagement/Professional is
    linked, show it. If not, show a recent list based on Contact
    (Transactions/Engagements) or a small global list (Professionals).
    This provides useful context without forcing explicit selection.

-   **Modal approach for Tasks (adopted):**\
    Task creation and editing moved toward modal rendering using a
    global Task modal in `base.html`, loaded via fetch
    (`openTaskModal()`).

-   **Dropdown defaults for Transaction/Engagement (adopted):**\
    Because the search-based selectors did not behave reliably inside
    the modal and had UI clipping/visibility issues, Transaction and
    Engagement selectors were redesigned as `<select>` dropdowns that
    populate based on selected Contact.

-   **Keep search/typeahead approach as a backup (explicitly
    deferred):**\
    The populate/search selector design is intentionally preserved as an
    alternative option for later reconsideration.

### Features Added or Updated

-   **Task view contextual display implementation:**

    -   Task view route expanded to fetch related Transaction(s),
        Engagement(s), and Professional(s) conditionally.

    -   Recent lists shown when no specific selection exists.

```{=html}
<!-- -->
```
-   **Global modal infrastructure in `base.html`:**

    -   Added global Task modal markup (`#taskModal`) and a reusable
        `openTaskModal(url, title)` loader.

    -   Fixed a crash caused by accidentally referencing a JS variable
        name (`resp`) inside Jinja rendering (Jinja tried to interpret
        it, causing `UndefinedError: 'resp' is undefined`).

```{=html}
<!-- -->
```
-   **Tasks list UX updates:**

    -   "+ Add New Task" button triggers the modal (`tasks_modal_new`).

    -   "Edit" button triggers modal edit (`tasks_modal_edit`).

    -   Title links were updated to behave more like link-buttons for
        consistency and better click targets.

```{=html}
<!-- -->
```
-   **Dropdown population endpoint:**

    -   Added `/tasks/options` to return JSON lists of recent
        Transactions and Engagements for a Contact.

    -   Modal routes (`tasks_modal_new`, `tasks_modal_edit`) also
        preloaded transactions/engagements when contact_id is known.

```{=html}
<!-- -->
```
-   **Selector initialization rework:**

    -   Introduced `window.initTaskFormEnhancements()` to allow scripts
        to bind after modal HTML is injected.

    -   Confirmed that the modal loader calls this initializer after
        loading HTML.

### Bugs and Debugging Outcomes

-   **500 errors caused by template variable misuse:**

    -   `resp` was referenced inside a Jinja template block (should only
        exist in JS runtime), breaking any page extending `base.html`.

```{=html}
<!-- -->
```
-   **Tasks list error due to undefined `c`:**

    -   Tasks list template mistakenly referenced `c['id']` (contact
        context that did not exist on the Tasks page). Corrected to call
        modal without `c`.

```{=html}
<!-- -->
```
-   **Modal field population not triggering fetch:**

    -   Contact search fetch worked, but
        Transaction/Engagement/Professional search did not reliably
        fetch in modal.

    -   Result: pivoted to dropdown defaults for Transaction and
        Engagement, driven by Contact selection and `/tasks/options`.

```{=html}
<!-- -->
```
-   **Layout blow-ups in modal:**

    -   Found issues caused by invalid HTML attributes (duplicate
        `class` or malformed `<div>`), and by dropdown result containers
        being constrained by modal scroll/overflow.

    -   Reinforced the rule: modal content must use valid, minimal
        markup and dropdowns should not rely on absolute-positioned
        lists near bottom of scrollable modal.

### Design Principles Reinforced

-   **Consistency of top-level page headers and CTA buttons**: favor a
    unified pattern like Contacts page ("+ Add New ...").

-   **No fragile UI in constrained modal space**: avoid complex
    typeahead result panes that may clip; prefer dropdown defaults when
    relationships are contact-scoped.

-   **Client-side initialization must support dynamic HTML**: scripts
    should not rely solely on DOMContentLoaded when content is injected
    after load.

-   **Avoid mixing runtime JS variable names into server-side
    templates**: Jinja will evaluate them and crash.

### Scope Control and Versioning Notes

-   Work is iterative and "polish-driven," but scope changes were
    explicitly acknowledged:

    -   Search/typeahead selectors were attempted and then deferred in
        favor of dropdown defaults.

    -   Contextual wildcard display remains a temporary solution, with a
        known future plan to shift to true multi-select relationships
        (Option 2) later.

```{=html}
<!-- -->
```
-   No explicit phase/version transition was declared in this segment,
    but changes align with ongoing Phase 5 Tasks refinement and UX
    stabilization.

### Current State at End of This Segment

-   Task modal opens and loads forms.

-   Contact search works inside modal.

-   Transaction and Engagement fields have been converted to dropdowns
    in `form_modal.html`.

-   Routes for modal new/edit and `/tasks/options` exist and are
    consistent with dropdown strategy.

-   Next step is to finalize `task_form.js` so Contact selection
    triggers `/tasks/options` fetch and reliably repopulates the
    dropdowns (and decide whether Professional remains typeahead or
    becomes dropdown).

**Ulysses CRM --- Local Database Safety & Startup Workflow**\
**Date:** January 4, 2025

### Goal

Establish a **safe, repeatable, and unambiguous local development
startup workflow** that prevents accidental connections or migrations
against the production database while working on Ulysses CRM.

### Core Problem Addressed

-   The terminal was defaulting to `$DATABASE_URL`, which in some cases
    resolved incorrectly or ambiguously.

-   Postgres errors revealed:

    -   Default DB fallback to OS username

    -   Assumptions about a `postgres` role that did not exist locally

```{=html}
<!-- -->
```
-   Risk identified: accidental production access during schema or
    migration work.

### Key Decisions Made

1.  **Local-first override strategy**

    -   Explicitly bind:

    -   `DATABASE_URL = LOCAL_DATABASE_URL`

    -   This ensures all tooling (Flask app, migrations, `psql`,
        helpers) consistently targets local DB during development.

```{=html}
<!-- -->
```
1.  **Explicit local role usage**

    -   Confirmed local Postgres role is `dennisfotopoulos`, not
        `postgres`.

    -   Standardized local connection string accordingly.

```{=html}
<!-- -->
```
1.  **Session-scoped safety (intentional)**

    -   Environment variables are set **per terminal session**, not
        globally via `.zshrc`.

    -   This reinforces deliberate intent and avoids silent context
        bleed across projects or environments.

```{=html}
<!-- -->
```
1.  **Project-scoped startup script**

    -   Created `scripts/local-shell.sh` inside the repo to:

        -   Activate the virtual environment

        -   Set and align DB environment variables

        -   Provide clear, masked visual confirmation of DB targets

### Features Added

**`scripts/local-shell.sh`**

-   Canonical local dev entry point.

-   Responsibilities:

    -   Activate `venv`

    -   Define `LOCAL_DATABASE_URL`

    -   Map `DATABASE_URL` → `LOCAL_DATABASE_URL`

    -   Echo both values (masked) for human verification

    -   Reinforce visual safety messaging

This script becomes the **standard starting step** for local Ulysses
development.

### Design Principles Reinforced

-   **Explicit over implicit**

    -   No reliance on defaults, fallbacks, or hidden shell config.

```{=html}
<!-- -->
```
-   **Human-readable safety**

    -   Clear echo output beats silent correctness.

```{=html}
<!-- -->
```
-   **Fail-safe mindset**

    -   Local dev should be easy.

    -   Production access should be intentional, noisy, and hard.

```{=html}
<!-- -->
```
-   **Repeatability**

    -   Same commands, same outcome, every session.

```{=html}
<!-- -->
```
-   **No silent prod foot-guns**

    -   Especially critical during schema and migration phases.

### Verification Standards Established

-   Always verify DB identity before migrations or schema work:

-   `psql "$DATABASE_URL" -c "SELECT current_database(), inet_server_addr();"`

-   Expect:

    -   `realestatecrm_local`

    -   `localhost` (`127.0.0.1` or `::1`)

### Phase / Version Context

-   This work supports **ongoing Phase 5 development** of Ulysses CRM.

-   No version bump occurred, but this establishes **infrastructure
    hygiene** critical for:

    -   Phase 5 continuations

    -   Phase 6+ features

    -   Safer parallel local vs production workflows

### Outcome

By the end of this session, Ulysses CRM gained a **rock-solid local
startup and DB safety model** that:

-   Eliminates accidental production access

-   Clarifies developer intent

-   Scales cleanly as the system grows more complex

This workflow is now considered **best practice and canonical** for
future development sessions.

**Ulysses CRM --- Project Evolution Summary**\
**Date:** January 4, 2025

## Context & Goals

This session focused on stabilizing and finalizing the **Tasks modal
workflow** and related UI behaviors as part of the **Phase 5
workstream**, culminating in a production release. The primary goal was
to ensure that Tasks could be reliably created and edited from multiple
entry points (Contacts, Tasks list, Tasks view) without UI conflicts,
DOM duplication, or accessibility regressions.

A secondary goal was to improve **engagement readability** and overall
usability while laying groundwork for the next refinement phase (Phase
5c).

## Key Issues Identified

1.  **Conflicting Task Modal Loaders**

    -   Two independent modal-loading mechanisms existed:

        -   `openTaskModal()` (used by Tasks list/view pages)

        -   `show.bs.modal` handler in `task_form.js` (used by Contacts
            `+ Task`)

    ```{=html}
    <!-- -->
    ```
    -   These were both firing in some cases, causing:

        -   Duplicate task forms rendered outside the modal

        -   Modal appearing "below" the main page

        -   Unintended fetches with empty `contact_id` and `next` values

```{=html}
<!-- -->
```
1.  **Duplicate Script Inclusions**

    -   `static/js/task_form.js` was included more than once (in
        `base.html` and again elsewhere), amplifying side effects and
        re-binding logic.

```{=html}
<!-- -->
```
1.  **Accessibility Warning**

    -   Browser console warning regarding `aria-hidden` and focus
        retention when closing the Task modal.

## Key Decisions & Fixes

### 1. Task Modal Ownership Model (Critical)

A **clear ownership rule** was established:

-   **Contacts page** owns modal loading **only when opened via a
    trigger element** (`data-bs-toggle`, `data-contact-id`)

-   **Tasks pages** own modal loading via `openTaskModal()`
    (programmatic open)

**Implementation decision:**

-   Guard the `show.bs.modal` handler in `task_form.js` so it **only
    runs when `event.relatedTarget` exists**.

-   If the modal is opened programmatically (no trigger), the
    Contacts-specific loader does nothing.

This decisively eliminated modal collisions while preserving both
workflows.

### 2. Script Loading Discipline

-   `task_form.js` is now included **once**, centrally via `base.html`.

-   No duplicate includes in child templates.

-   Reinforced a design rule: **JS behavior files should be
    single-loaded and context-aware**, not re-injected per template.

### 3. Accessibility Improvement

-   Added a **focus-return fix** on modal close:

    -   Track the last trigger element

    -   Restore focus when the modal closes

```{=html}
<!-- -->
```
-   This resolved the `aria-hidden` console warning and aligned with
    assistive technology best practices.

## Features Added / Improved

-   **Task modal stability** across Contacts and Tasks sections

-   **Prefilled Tasks from Contacts** fully working and production-safe

-   **Engagement log "See more / See less" clamping**

    -   Long engagement descriptions are truncated by default

    -   Expandable inline without navigating away

```{=html}
<!-- -->
```
-   Improved confidence in modal lifecycle management

## Features Deferred

-   Full Phase 5c usability and polish items (to be selected next)

-   Engagement display polish beyond clamping (layout refinements)

-   Broader Tasks model enhancements (independent/non-contact tasks,
    etc.)

These are intentionally deferred to **Phase 5c (v0.11.2)**.

## Version & Phase Transitions

-   **v0.11.1** was successfully published to production.

-   This release is considered **stable and complete** for Phase 5b.

-   Next planned release:

    -   **Phase 5c**

    -   **Target version: v0.11.2**

    -   Focus: stability, usability polish, and targeted cleanup items.

## Design Principles Reinforced

-   **Single responsibility for modal loaders**

-   **Event-driven guards over conditional branching**

-   **One-time JS inclusion**

-   **Modal behavior must be context-aware**

-   **Stability before expansion**

## Operational Notes

-   Confirmed need to **rotate Render Postgres production credentials**
    after publish.

-   Step-by-step, non-URL-printing credential rotation workflow to be
    followed separately.

**Status at Close:**\
Production stable, modal conflicts resolved, accessibility warning
addressed, and groundwork laid for Phase 5c refinement work.

# Ulysses CRM --- Project Evolution Summary

**Date:** January 4, 2025\
**Phase Context:** Phase 5c completion → Phase 6 planning\
**Release:** v0.11.2

## High-Level Goal of This Work

This sequence of work focused on **closing Phase 5c** with a strong
emphasis on **stability, data safety, and UX clarity**, while
deliberately avoiding risky or irreversible changes. The outcome was a
clean, production-ready release (v0.11.2) and a well-defined path
forward toward v1.0.

## Key Decisions & Principles Reinforced

### 1. Stability Over Feature Expansion

-   Phase 5c was treated as a **stability and correctness pass**, not a
    feature phase.

-   Any change that risked data loss, schema churn, or ambiguous
    behavior was either:

    -   redesigned (e.g., archiving vs deletion), or

    -   explicitly deferred to Phase 6.

### 2. Explicit Scope Locking

-   Items were classified clearly as:

    -   **Completed**

    -   **Deferred**

    -   **Reframed**

```{=html}
<!-- -->
```
-   No silent refactors or surprise changes were allowed.

-   Every schema change required explicit approval and documentation.

### 3. Data Safety First

-   Strong preference established for **reversible actions**.

-   Hard deletion of contacts was deemed too risky and removed from
    near-term plans.

-   **Contact archiving** was selected as the correct long-term
    solution.

## Phase 5c --- What Was Completed (v0.11.2)

### Engagements

-   Fixed a bug where editing **only engagement date/time** did not
    persist.

-   Confirmed engagement edits now save partial changes reliably.

-   Added **"See more / expand"** behavior for long engagement
    descriptions across views.

### Contacts & Forms

-   Added guardrails to prevent accidental contact data loss when
    multiple save actions exist.

-   Clarified save behavior across contact-related forms.

-   Phone numbers standardized on save:

    -   Normalized to `+1##########` where possible

    -   Displayed consistently across the UI

    -   Legacy formats preserved until edited

### Buyer & Seller Sheets

-   Removed inappropriate NOT NULL constraints where full addresses are
    not always known.

-   Buyer "properties of interest" can now be created without an
    address.

-   Subject properties (actual deal targets) **intentionally still
    require an address**.

-   Label clarity added to reinforce that requirement.

### Dashboard

-   "Recent Engagements" redesigned to:

    -   Show **only the most recent engagement per contact**

    -   Display up to **10 unique contacts**

    -   Eliminate duplicate contact noise

```{=html}
<!-- -->
```
-   Active contacts logic already using lateral joins was confirmed as
    correct.

### Database

-   One minor, approved schema change:

    -   `buyer_properties.address_line` made nullable

```{=html}
<!-- -->
```
-   Change was:

    -   Documented via migration file

    -   Applied manually to production (Render)

    -   Verified for parity

## Release Outcome

-   **v0.11.2** was committed, tagged, and deployed.

-   Production database updated manually to maintain parity.

-   Phase 5c formally closed as a **stability milestone**.

-   System now operates on a clean, predictable baseline.

## Phase 6 --- Strategic Reframing

### Major Decision: Replace Deletion with Archiving

-   Hard deletion of contacts was deemed too risky given deep relational
    dependencies.

-   **Contact archiving** selected as the correct model approaching
    v1.0:

    -   Safe

    -   Reversible

    -   Preserves historical data

    -   Cleans dashboards and workflows

This decision significantly reduces v1.0 risk.

## Phase 6 Scope (Established, Not Yet Implemented)

Phase 6 will focus on **workflow completion and UX maturity**, not
experimental features. Key items include:

-   Contact archiving and restore (P0)

-   Engagement log button rename ("View / Edit")

-   Follow-up logic redesign

-   Independent (non-contact) tasks

-   Per-square-foot commercial pricing

-   Listing & offer statuses branch

-   Associated contacts UX improvements

-   Past client isolation rules

-   Imported contacts activation flow

-   Seller-side showing feedback

-   Checklist auto-save indicator polish

Hard deletion, major schema redesigns, and external integrations remain
out of scope.

## Phase / Version Transition

-   **Phase 5c:** Complete

-   **Current Release:** v0.11.2 (stability checkpoint)

-   **Next Phase:** Phase 6 (workflow completion)

-   **Trajectory:** Toward a v1.0 release candidate with reduced risk
    and higher confidence

## Overall Assessment

This work marked a turning point where Ulysses CRM shifted from
"building" to **finishing**. The emphasis on data safety, explicit scope
control, and reversible decisions establishes a strong foundation for
Phase 6 and positions the project responsibly as it approaches v1.0.

**Ulysses CRM -- Integration & Ecosystem Canon Summary**\
**Date:** January 6, 2025

## Context and Goal of This Discussion

This conversation focused on defining the long-term ecosystem around
**Ulysses CRM**, specifically how it should integrate with:

-   WordPress-based websites

-   Gravity Forms for lead capture

-   SEO tooling (Yoast)

-   IDX (via FBS Products / MOMLS)

The primary goal was to make clear, disciplined architectural decisions
that preserve Ulysses as a durable, agent-centric system rather than
allowing it to drift into portal or IDX territory.

## Core Strategic Goals Established

-   Build Ulysses as an **agent-facing intelligence and workflow
    system**, not a client destination.

-   Support best-in-class website, SEO, and IDX tools without attempting
    to replace them.

-   Ensure all integrations are **repeatable, secure, and boring by
    design**, so they scale to other users later.

-   Maintain a strict separation between **client-facing experiences**
    and **agent-facing reasoning and memory**.

## Canonical Decisions (Locked)

### 1. Ulysses Is Not an IDX

-   Ulysses will not render listings.

-   Ulysses will not store or sync MLS listing datasets.

-   Ulysses will not compete with IDX vendors on search, alerts, or
    browsing UX.

### 2. Ulysses Is Also Not a Client Portal

-   No client login for browsing, saved searches, or listing alerts.

-   No client-facing dashboards that resemble portals.

-   Avoid all implicit IDX gravity that portals create (permissions, MLS
    compliance exposure, alert logic).

**Canon rule established:**

*Clients do not "go" to Ulysses.*\
*Agents use Ulysses to understand, remember, and act.*

This rule is explicitly locked as canon.

## Clean Separation of Responsibilities (Architectural Rule)

**Client-facing layer**

-   WordPress for content, SEO, and authority

-   Yoast for SEO mechanics

-   FBS IDX for compliant listing search and display

-   Gravity Forms for identity capture and intent confirmation

**Agent-facing layer**

-   Ulysses CRM for:

    -   Contacts as people

    -   Engagements as meaningful events

    -   Tasks as commitments

    -   Transactions as narratives

    -   Attribution as cause-and-effect history

**Directional rule**

-   Data and events flow **into** Ulysses.

-   Ulysses does not push listings or browsing experiences outward.

## Gravity Forms Integration -- Confirmed Direction

-   Gravity Forms selected as the standard lead capture tool.

-   Gravity Forms will function as the **secure intake valve**, not a
    CRM.

-   Ulysses will replicate and exceed typical "CRM feed" integrations
    by:

    -   Deduplicating contacts

    -   Creating engagements automatically

    -   Triggering tasks based on form type

    -   Capturing attribution (UTMs, landing page, referrer)

This integration is considered **well-scoped and deterministic**.

## IDX (FBS Products / MOMLS) Integration -- Scoped and Constrained

### What IS in scope

-   IDX **event and intent logging**, not data ingestion:

    -   Listing views

    -   Showing requests

    -   Saved searches

    -   Listing inquiries

```{=html}
<!-- -->
```
-   Anonymous activity that can later be merged once identity is known.

-   IDX behavior translated into engagements and workflow signals inside
    Ulysses.

### What is explicitly OUT of scope

-   Rebuilding IDX UI

-   Pulling or storing MLS listing datasets

-   Two-way IDX sync

-   Generating MLS alerts from Ulysses

-   Any client-facing IDX portal behavior

This distinction was reinforced as critical to long-term sustainability.

## Phase and Versioning Decisions

### Phase 7 Direction (Confirmed)

Phase 7 may include:

1.  **Gravity Forms Intake API**

    -   Secure API keys

    -   Source site attribution

    -   Contact + engagement + task creation

```{=html}
<!-- -->
```
1.  **IDX Signal Capture**

    -   Event logging only

    -   Identity resolution

    -   Engagement creation from IDX behavior

### Versioning Guidance

-   Gravity Forms integration aligns with approximately **v1.2--v1.3**

-   IDX signal capture aligns with approximately **v1.4--v1.6**

-   Any deeper IDX or portal-like functionality is explicitly deferred
    toward **v2.0 or later**, and only if ever justified

## Website / IDX UX Improvements (Deferred)

-   Current FBS IDX implementation on WordPress sites is acknowledged as
    clunky and underperforming.

-   Agreement reached to revisit IDX usage **after Phase 6 deployment**.

-   IDX improvements will focus on:

    -   Narrative-first pages

    -   Hyper-local SEO

    -   Curated listing blocks

    -   Contextual IDX usage

```{=html}
<!-- -->
```
-   This work is explicitly **out of scope for Phase 6** and
    intentionally deferred.

## Design Principles Reinforced

-   Restraint is a feature, not a weakness.

-   Ulysses should optimize for **memory, reasoning, and next-best
    action**, not access.

-   IDX and SEO volatility should not infect CRM architecture.

-   Boring, stable integrations scale better than flashy ones.

-   The system should answer *why deals happen*, not just *what
    happened*.

## Canon Statement (Final)

\*\*Ulysses is not an IDX.\
Ulysses is not a portal.\
Ulysses is the

## Ulysses CRM --- Project Evolution Summary

**Date:** January 6, 2025\
**Phase Context:** Phase 6a (close-out) → Phase 6b transition

### High-Level Goal of This Session

The primary objective of this work session was to **stabilize core CRM
workflows** before advancing feature scope. The focus was on eliminating
destructive patterns, resolving production-critical bugs, and converting
fragile workflows into **editable, durable, and auditable systems**.

This session ultimately **closed Phase 6a** and prepared a clean
transition into Phase 6b.

## Key Decisions & Design Principles Reinforced

### 1. Non-Destructive First Philosophy (Reaffirmed)

-   Hard deletes are avoided wherever possible

-   Archiving, editing, and reversible actions are preferred

-   Data integrity and historical accuracy take precedence over
    convenience

This principle directly informed:

-   Contact handling

-   Task deletion UX

-   Associated contact relationships

### 2. Single Source of Truth Enforcement

-   Semantic duplication was removed where it caused ambiguity

-   Fields with overlapping meaning were consolidated

**Key example:**

-   "Past Client" designation is now driven **only** by `pipeline_stage`

-   "Past Client" removed from `source` dropdown to prevent
    misclassification

## Features Added or Completed

### ✅ Dashboard Layout Refactor

-   Dashboard converted to a **2-column widget system**

-   Current structure:

    -   Left column: Active Contacts → Past Clients

    -   Right column: Engagements → Professionals

```{=html}
<!-- -->
```
-   Layout intentionally future-proofed for additional widgets

### ✅ Past Clients Handling

-   Past clients isolated cleanly in Contacts view

-   Past Client badge added to Engagements widget

-   New Past Clients dashboard widget added

-   Pipeline-stage driven designation confirmed as canonical

### ✅ Tasks System --- Critical Bug Fix & Hardening

**Problem Identified**

-   Editing a task in production created a duplicate task instead of
    updating

**Resolution**

-   Corrected create vs edit routing

-   Ensured edit forms always hit update logic

-   Redirect after edit now returns to **Tasks list**, not task detail

**Additional Improvements**

-   Delete task option added:

    -   Non-prominent placement

    -   Confirmation modal

    -   Explicit ownership validation

```{=html}
<!-- -->
```
-   Tasks are now:

    -   Idempotent

    -   Safe to edit

    -   Production-stable

### ✅ Associated Contacts --- Major Architectural Upgrade

This was the most significant change of the session.

#### Previous State

-   Associations were effectively immutable

-   Editing required deleting and recreating relationships

-   Notes and relationship context were fragile

#### New Architecture

-   Associations are:

    -   Stored once (canonical ordering)

    -   Symmetric between contacts

    -   Fully editable

#### Data Model Enhancements

-   `contact_associations` now properly stores:

    -   `relationship_type`

    -   `notes`

```{=html}
<!-- -->
```
-   Changes propagate correctly to **both contacts**

#### UI Improvements

-   Associated Contacts table now shows:

    -   Name (linked)

    -   Relationship

    -   Email

    -   Phone

```{=html}
<!-- -->
```
-   Second row added per association:

    -   Displays relationship-specific notes

```{=html}
<!-- -->
```
-   Each association supports:

    -   Edit (modal)

    -   Remove (explicit action)

#### Editing Workflow

-   Inline edit modal implemented

-   Relationship and notes editable without deletion

-   Ownership and scope validation enforced

-   Confirmed working bi-directionally

This replaced a destructive workaround with a **durable, correct
relationship model**.

## Issues Encountered & Resolved

-   Template resolution errors (`TemplateNotFound`) fixed by correcting
    include paths

-   Association update bugs caused by mismatched field names
    (`relationship` vs `relationship_type`) resolved

-   SQL type errors traced to form field mismatch and corrected

-   Confirmed edits reflect correctly across all associated records

## Explicitly Deferred / Out of Scope

The following were intentionally tabled to avoid scope creep:

-   Independent (non-contact) tasks

-   IDX / listing share integrations

-   Listing & offer statuses branch

-   Follow-up overdue logic redesign

-   Checklist auto-save polish

-   Past-client automation rules

-   Association role presets or enforcement

These remain candidates for future phases.

## Phase Transition

### Phase 6a

**Status:** Closed\
**Focus:** Stability, data integrity, removal of destructive patterns\
**Outcome:** Successful

### Phase 6b (Next Phase)

**Intent:**

-   Build on 6a stability

-   Improve workflow intelligence and UX maturity

-   No schema-breaking or destructive changes

-   Incremental enhancements only

A formal Phase 6b transition document was produced and is ready for use
in the next chat.

## Canonical Takeaway

This session marked a shift from "making features work" to **making
systems safe, editable, and future-proof**. Core CRM primitives
(contacts, tasks, relationships) are now stable enough to support
higher-level automation and intelligence in subsequent phases.

**Ulysses CRM + ChatGPT Integration Discussion**\
**Date:** January 7, 2025

### Purpose of Discussion

This conversation explored whether and how ChatGPT could be utilized in
the **daily use of Ulysses CRM**, with a specific focus on **Engagement
logging**, workflow efficiency, and long-term architectural fit.

## Goals Identified

-   Evaluate whether ChatGPT can directly enter data into Ulysses

-   Determine the appropriate role of AI within the CRM ecosystem

-   Avoid premature or unsafe automation

-   Align any AI usage with Ulysses' phased development approach

-   Preserve user judgment, data integrity, and compliance standards

## Key Decisions Made

### 1. ChatGPT will not directly write to the Ulysses database (current or near-term)

-   ChatGPT does **not** automatically create or save engagements today

-   This behavior is intentional and desirable at the current stage

-   Manual review and user intent remain mandatory before data becomes
    official

### 2. ChatGPT's role is defined as a drafting and reasoning layer

-   ChatGPT prepares:

    -   Engagement summaries

    -   CRM-ready notes

    -   Suggested follow-ups

    -   Optional emails or talking points

```{=html}
<!-- -->
```
-   Ulysses remains the **system of record**

-   The user explicitly decides what is saved and when

### 3. Engagements are the first and primary AI integration target

-   Voice notes, calls, texts, and ad-hoc notes are the highest-value
    use case

-   AI assistance should reduce friction without replacing judgment

## Features Explicitly Deferred to Phase 6

The following items were **intentionally deferred** and not implemented
now:

-   Direct ChatGPT → database writes

-   Automatic engagement creation

-   Fully automated voice-to-CRM pipelines

-   Background or unsupervised AI actions

-   Chatbot-style UI embedded into Ulysses

All of the above are considered **future-capable**, but not appropriate
prior to Phase 6.

## Design Principles Established or Reinforced

-   **Draft, never decide**: AI suggests; the user confirms

-   **No silent automation**: Nothing enters the CRM without user action

-   **Human judgment first**: AI supports, never overrides

-   **Auditability and control** over convenience

-   **Phased discipline** over feature creep or "AI theater"

Mental model adopted:

ChatGPT is a senior assistant who drafts everything but never files
anything without approval.

## Phase and Version Implications

-   **Phase 6** is now the canonical phase for:

    -   ChatGPT integration

    -   Engagement drafting workflows

    -   Structured prompt + response schemas

    -   UI-level "Generate Draft" or "Insert Draft" patterns

```{=html}
<!-- -->
```
-   No Phase or version numbers were incremented during this discussion

-   Phase 6 scope was clarified, not expanded prematurely

## Outcome / Status

-   ChatGPT integration acknowledged as valuable and inevitable

-   Implementation **intentionally paused**

-   User explicitly chose to revisit during **Phase 6**

-   Conversation closed cleanly with no pending technical actions

## Standing Note for Future Phase 6 Work

When Phase 6 begins, the next logical artifacts will be:

1.  Engagement draft schema (structured output)

2.  Canonical ChatGPT prompt for Ulysses

3.  UI workflow for draft → review → save

This conversation serves as the **foundational rationale** for AI usage
within Ulysses CRM.

**Status:** Deferred by design\
**Next Touchpoint:** Phase 6 kickoff

**Ulysses CRM --- Production Diagnostics Summary**\
**Date:** January 8, 2025

### Context and Goal

This discussion focused on diagnosing a series of production 404 errors
observed in server logs, initially suspected to be Safari-specific
issues. The goal was to determine whether these errors indicated a
functional problem in Ulysses CRM or merely benign browser behavior, and
to decide whether corrective action was warranted.

### Key Findings

-   The only true 404 errors occurring in production were requests to
    `/favicon.ico`.

-   All other requests in the log were behaving as expected:

    -   Authentication-related 302 redirects (`/` → `/login`,
        `/followups` → `/login`) are correct and intentional.

    -   Static assets (`CSS`, `JS`, images, SVGs) were returning
        `304 Not Modified`, confirming proper caching behavior.

    -   The `/followups.ics` endpoint returned `200` and was correctly
        accessed by Apple system services (`dataaccessd`) for calendar
        subscriptions.

```{=html}
<!-- -->
```
-   Safari (macOS and iOS) was identified as more aggressive than other
    browsers in automatically requesting `/favicon.ico`, even when no
    explicit favicon link is defined, making the issue appear
    Safari-specific when it is not.

### Decisions Made

-   The 404s were determined to be **non-critical and cosmetic**, not
    indicative of application bugs or routing failures.

-   A small, production-safe fix was recommended and accepted to
    eliminate log noise and improve polish:

    -   Add a real favicon file to the static assets.

    -   Explicitly declare the favicon in `base.html`.

    -   Optionally add a Flask route for `/favicon.ico` to guarantee a
        non-404 response regardless of browser behavior.

### Design Principles Reinforced

-   **Log hygiene matters:** Eliminating avoidable 404s helps keep
    production logs meaningful and reduces false alarms during
    diagnostics.

-   **Browser behavior should be normalized server-side:** When common
    clients (Safari, iOS) exhibit predictable but noisy behavior, the
    application should accommodate it rather than treat it as an error
    condition.

-   **Minimal, low-risk fixes preferred in production:** The chosen
    solution avoids schema changes, logic refactors, or user-facing
    risk.

### Features Added or Deferred

-   **Added (minor infrastructure polish):**

    -   Explicit favicon handling via static assets and optional route.

```{=html}
<!-- -->
```
-   **Deferred:**

    -   No functional features were added or deferred as part of this
        discussion.

    -   No phase or version changes were triggered.

### Phase / Version Impact

-   No new phase initiated.

-   No version bump required.

-   This change is considered a small production-hardening improvement
    suitable for inclusion in the next routine deployment or hotfix
    without affecting roadmap sequencing.

**Outcome:**\
The issue was fully understood, scoped, and resolved at a diagnostic and
design level. The application behavior was confirmed to be correct, with
a minor enhancement identified to improve production cleanliness and
cross-browser completeness.

## Ulysses CRM -- Inline Help / UI Guidance Discussion

**Date:** January 10, 2025

### Goal

To explore whether Ulysses CRM should include built-in, contextual help
to guide users through fields, concepts, and workflows without requiring
external documentation or training.

### Key Decisions

-   **Inline help ("?" explanations) is a confirmed future feature**,
    not speculative.

-   The feature is **intentionally deferred**, not abandoned.

-   Help content will be **contextual and UI-embedded**, not a separate
    manual or knowledge base at first.

-   The authoritative source of truth for what needs help will be
    **organically discovered friction**, identified during real usage
    rather than pre-designed assumptions.

### Agreed Feature Scope (Future Implementation)

-   Small **"?" icons** next to confusing fields or labels.

-   Hover or tap reveals **concise, plain-language explanations**.

-   Optional "Learn more" expansion via modal or drawer for complex
    topics.

-   No workflow logic changes, data model changes, or behavioral side
    effects.

### Design Principles Reinforced

-   **User-driven discovery:** Help is added where confusion is
    observed, not guessed.

-   **No one-off UI hacks:** Help will be implemented via a reusable,
    centralized pattern.

-   **Centralized content management:** Help text will live in a single
    source (map/config), not scattered across templates.

-   **Minimal UI clutter:** Help is present but unobtrusive.

-   **Legal and compliance awareness:** Language must be safe around
    agency, archiving, and client status concepts.

-   **Phase discipline:** No partial or piecemeal rollout.

### Process Established

-   Dennis will maintain a **running list of fields/pages** that appear
    to need clarification.

-   That list will serve as the **official backlog** for the help
    feature.

-   Implementation will occur only when deliberately scheduled, in a
    single cohesive pass.

### Phase / Version Positioning

-   Candidate for **Phase 6c** if implemented pre-v1.0 polish.

-   Otherwise targeted for **early Phase 7** alongside onboarding and
    usability enhancements.

-   No immediate phase transition triggered by this discussion.

### Outcome

-   Feature concept is **pinned and canonized** in project direction.

-   No code changes initiated.

-   Clear agreement on timing, scope control, and implementation
    standards.

**Ulysses CRM -- Phase 6a / 6b Development Summary**\
**Date:** January 11, 2025

## Overview & Goals

This work session focused on completing and stabilizing **Phase 6a and
Phase 6b** of Ulysses CRM, with an emphasis on:

-   Finalizing **Contacts Archiving** (Phase 6a)

-   Introducing the **Templates Hub** with preview and variable support
    (Phase 6b)

-   Maintaining **local vs production safety**, schema parity, and
    deployment discipline

-   Cleaning up legacy UI elements that no longer reflect current
    workflow philosophy

## Key Features Implemented

### Phase 6a -- Contacts Archiving

-   Added `archived_at` column to `contacts`

-   Introduced supporting indexes for archived filtering

-   Updated queries and UI to support:

    -   Active contacts vs archived (past clients)

    -   Non-destructive lifecycle management (no deletes)

```{=html}
<!-- -->
```
-   Enforced **ON DELETE RESTRICT** on most contact-related foreign keys
    in production to prevent accidental cascades

-   Explicitly validated and documented production FK behavior vs local

**Design Principle Reinforced:**\
Contacts are durable records. Archiving is preferred over deletion.
Referential integrity must protect data even at the cost of convenience.

### Phase 6b -- Templates Hub

-   Introduced new `templates` table with:

    -   Category

    -   Delivery type

    -   Body, notes

    -   Locked state

    -   Archiving support (`archived_at`)

```{=html}
<!-- -->
```
-   Implemented:

    -   Templates index, view, and preview flow

    -   Safe preview rendering with placeholder values

    -   Variable substitution system (initial variables):

        -   {{`client_name``}``}`

        -   {{`agent_name``}``}`

        -   {{`brokerage_footer``}``}`

```{=html}
<!-- -->
```
-   Added archiving support for templates instead of deletion

-   Confirmed DB migrations ran successfully in production

-   Ensured queries properly excluded archived templates where
    appropriate

**Design Principle Reinforced:**\
Templates are long-lived assets. They should be versionable, archivable,
and previewable without requiring live data.

## UI / UX Decisions

### Contacts Search & Template Preview

-   Implemented contact search-driven preview population

-   Identified scaling issue with expanding contact cards during search

-   Chose floating / constrained result behavior to avoid UI expansion
    as contact volume grows

### Preview UX Refinement

-   "Previewing As" indicator moved into the Preview block header

-   Indicator styled with a **conforming accent color**, not muted text

-   Reinforced visual hierarchy and clarity without adding clutter

## Dashboard Adjustments

-   Decided to limit dashboard widgets for clarity:

    -   Active Contacts: limit to 10

    -   Past Clients: limit to 5

    -   Professionals (future): limit to 10

```{=html}
<!-- -->
```
-   Reduced cognitive load and improved scanability

## Legacy Field Deprecation (In Progress)

-   Identified that `next_follow_up` and `last_contacted`:

    -   Were manual fields

    -   No longer reflect the true engagement-driven workflow

```{=html}
<!-- -->
```
-   Removed these fields from:

    -   `contacts.html`

    -   `edit_contact.html`

    -   `dashboard.html`

```{=html}
<!-- -->
```
-   Left database schema intact for now

-   Acknowledged remaining references (e.g. `followups.html`) and
    planned full UI cleanup

-   Deferred schema removal to a future phase

**Design Principle Reinforced:**\
UI should reflect truth in the data model. Manual or misleading fields
should be retired before they cause confusion.

## Production Safety & Deployment Learnings

-   Discovered local shell was accidentally operating in `APP_ENV=PROD`

-   Confirmed all DB URLs (`DATABASE_URL`, `LOCAL_DATABASE_URL`,
    `PROD_DATABASE_URL`) were set simultaneously

-   Reinforced rule:

    -   **Production migrations must be run from Render shell**

    -   Local shell should never point to production DB

```{=html}
<!-- -->
```
-   Performed:

    -   Full schema dumps (local vs prod)

    -   FK diff analysis

    -   Constraint validation queries

```{=html}
<!-- -->
```
-   Identified and corrected missing column
    (`contact_associations.notes`) causing production errors

**Design Principle Reinforced:**\
Environment clarity is critical. Guardrails matter. Always verify
APP_ENV before executing migrations.

## Versioning & Release State

-   Application version bumped to **v0.11.4**

-   Phase 6a and 6b considered functionally complete, pending:

    -   Final UI cleanup of deprecated follow-up fields

    -   Verification passes after deployment

```{=html}
<!-- -->
```
-   All migrations explicitly tracked and documented

## Deferred / Future Work

-   Full removal of `next_follow_up` / `last_contacted` from schema

-   Follow-ups to be fully engagement- or task-driven

-   Professionals table enhancements

-   Continued dashboard refinements

-   Phase 6c / Phase 7 planning

## Meta Observation

-   Code quality improved with clearer structure and more intentional
    commenting

-   Commenting practice explicitly acknowledged as positive and
    encouraged

-   Development cadence continues to emphasize **clarity, reversibility,
    and safety over speed**

**Status:** Phase 6a + 6b effectively complete, stable, and
production-aligned.\
**Next Step:** Final UI cleanup + verification, then proceed to next
phase.

**Project Evolution Summary -- Ulysses CRM**\
**Date:** January 11, 2025

### Context & Goal

This session focused on fixing a production-blocking error in the
**public Open House sign-in flow** within Ulysses CRM. The immediate
goal was to restore functionality for public visitors signing in while
maintaining the integrity of the multi-user data model introduced in
recent phases.

### Problem Identified

Public sign-ins were failing with a `500` error due to a **NOT NULL
constraint violation on `contacts.user_id`**. The Open House public
route (`/openhouse/<token>`) operates without authentication, so it was
attempting to create or update contacts without assigning a user owner.

A follow-up error revealed an incorrect assumption about schema
structure: the `open_houses` table does **not** have a `user_id` column.

### Key Findings

-   **`contacts.user_id` is now mandatory**, consistent with multi-user
    isolation rules.

-   **`open_houses` ownership is defined by `created_by_user_id`**, not
    `user_id`.

-   The public sign-in flow must infer ownership from the Open House
    itself.

-   Contact lookups during public intake were previously **not scoped by
    user**, risking cross-user data contamination.

### Key Decisions

1.  **Ownership Resolution Strategy**

    -   Use `open_houses.created_by_user_id` as the authoritative owner
        for:

        -   Creating new contacts

        -   Matching existing contacts

        -   Updating contact records

    ```{=html}
    <!-- -->
    ```
    -   This preserves clean ownership boundaries without requiring
        authentication.

```{=html}
<!-- -->
```
1.  **Scoped Contact Matching**

    -   All email and phone lookups in the public route are now scoped
        by `user_id`.

    -   Prevents accidental matches to another agent's database.

```{=html}
<!-- -->
```
1.  **Schema Consistency**

    -   No schema changes required for `open_houses`; existing
        `created_by_user_id` column is canonical.

    -   Reinforces principle that every public token must resolve to a
        single owning user.

```{=html}
<!-- -->
```
1.  **Bug Fix Identified**

    -   `agent_phone` was incorrectly populated from visitor phone
        fields.

    -   Corrected to read explicitly from the agent phone form input.

### Features Added / Modified

-   **Public Open House Sign-In**

    -   Contacts created via public sign-in are now correctly associated
        with the Open House owner.

    -   Existing contacts are safely updated only if they belong to the
        same user.

```{=html}
<!-- -->
```
-   **Data Safety Enhancement**

    -   Public routes now fully respect multi-user isolation rules.

### Design Principles Reinforced

-   **Explicit Ownership Everywhere**

    -   Any public or unauthenticated intake must still resolve to a
        user owner.

```{=html}
<!-- -->
```
-   **No Cross-User Data Leakage**

    -   All queries touching user-owned tables must be scoped by
        `user_id`.

```{=html}
<!-- -->
```
-   **Schema as Source of Truth**

    -   Route logic must align with actual schema, not inferred or
        assumed columns.

```{=html}
<!-- -->
```
-   **Public ≠ Anonymous Ownership**

    -   Public access does not mean unowned data.

### Tooling & Workflow Notes

-   Clarified how to disable pagers in:

    -   `psql` (\\`pset pager off`)

    -   Shell / Git / general CLI usage

```{=html}
<!-- -->
```
-   Clean Git workflow followed:

    -   Changes isolated to `app.py`

    -   Commit created with a focused, descriptive message

### Phase / Version Impact

-   No formal phase transition.

-   This work is a **stabilization fix within the current phase**,
    ensuring:

    -   Public Open House features remain compatible with Phase 4+
        multi-user architecture.

```{=html}
<!-- -->
```
-   Reinforces readiness for future production deployments involving
    public links.

### Status

-   Open House public sign-in flow corrected.

-   Ownership and contact creation now compliant with current data
    model.

-   Changes committed to `app.py`.

**Ulysses CRM -- Phase 6b Progress & Continuity Summary**\
**Date:** January 12, 2025

### Context & Goal

This chat focused on stabilizing and completing **Phase 6b** of Ulysses
CRM, with particular attention to the **Edit Contact experience**,
**Engagements**, and **Follow-ups**, while ensuring **local and
production parity**. The overarching goal was to finish Phase 6b
cleanly, avoid scope creep, and resolve blocking production issues
before moving on to adjacent work (Templates Hub for Clients).

### Key Accomplishments

#### 1. Engagements UI & Behavior (Completed)

-   Fixed **Engagements table action column width**.

-   Ensured **Engagement action buttons are consistently grouped**.

-   Confirmed **Delete Engagement modal returns the user to the
    Engagements tab**.

-   All changes tested locally and confirmed working.

These changes were explicitly validated and marked **DONE**.

#### 2. Follow-ups Tab Debugging & Resolution (Major Win)

-   Encountered a critical UI issue where the **Follow-ups tab rendered
    as white space**, despite data existing.

-   Deep inspection revealed:

    -   The Follow-ups DOM was present.

    -   Content was being rendered but was **visually inaccessible** due
        to markup / structural issues.

    -   Footer and other elements appeared nested incorrectly, strongly
        indicating a **div imbalance / tab-pane structure issue**.

```{=html}
<!-- -->
```
-   Confirmed symptoms included:

    -   Clicking into blank space revealed hidden form fields.

    -   Follow-ups appeared in rendered HTML but not visually.

```{=html}
<!-- -->
```
-   Resolution:

    -   Cleaned up the `edit_contact.html` structure.

    -   Ensured **proper tab-pane containment and closure**.

    -   Follow-ups tab now renders correctly and consistently.

```{=html}
<!-- -->
```
-   Final confirmation: **"It's working now."**

This reinforced the importance of **structural HTML integrity** in
complex, tabbed layouts.

#### 3. Phase 6b Scope Discipline

-   Explicit decision to **hold off on additional enhancements** that
    were discussed but not required to close 6b.

-   Confirmed that **Templates Hub for Clients** work will live in
    **Phase 6b**, but be handled in a **separate chat** to avoid
    contamination and confusion.

Design principle reinforced:

Phase discipline matters more than speed. Do not pile new work into a
chat once stability is reached.

### Production Issue & Database Parity

#### 4. Production Error: Buyer Sheet Save Failure

-   Production error encountered when saving a Buyer Profile:

    -   Missing column: `preapproval_letter_received` in
        `buyer_profiles`.

```{=html}
<!-- -->
```
-   Investigation steps:

    -   Verified **local database schema** using \\`d+ buyer_profiles`.

    -   Confirmed the column (and related fields) **existed locally**.

    -   Root cause identified as **schema drift between local and
        production**.

#### 5. Database Parity Validation

-   Confirmed `$PROD_DATABASE_URL` was correctly pointing to production.

-   Performed **schema-only dumps** of local and production databases.

-   Diff analysis revealed:

    -   Boolean fields present in both, but with **default
        differences**.

    -   Minor constraint formatting differences (array syntax, CHECK
        constraints).

    -   No destructive or data-risk discrepancies.

```{=html}
<!-- -->
```
-   Buyer sheet functionality confirmed **working again in production**
    after corrective action.

This reinforced a standing architectural principle:

**Local schema is the source of truth. Production must be brought into
parity deliberately and visibly.**

### Code & Version Control

-   Four template files modified and pushed:

    -   `templates/contacts.html`

    -   `templates/dashboard.html`

    -   `templates/edit_contact.html`

    -   `templates/followups.html`

```{=html}
<!-- -->
```
-   Changes successfully committed and pushed to `main`.

### Design Principles Reinforced

-   **HTML structure correctness is non-negotiable**, especially with
    Bootstrap tabs.

-   **Phase isolation** prevents regression and confusion.

-   **Schema parity checks** should be routine before and after
    production issues.

-   **Debugging rendered HTML** (not just templates) is essential when
    UI behavior contradicts data.

### Phase Status

-   **Phase 6b is functionally complete and stable**.

-   Buyer Sheet production issue resolved.

-   Follow-ups fully operational.

-   Next work (Templates Hub for Clients) intentionally deferred to a
    new chat while remaining within Phase 6b scope.

### Next Step

-   Transition to a **new chat** focused exclusively on **Templates Hub
    for Clients (Phase 6b)** with a clean context and no legacy
    debugging noise.

**Ulysses CRM --- Phase 6 Reference Summary**\
**Date:** January 12, 2025

### Context & Purpose

This chat establishes the authoritative reference for **Phase 6** of
Ulysses CRM development. It serves as a historical and project-evolution
checkpoint following the stabilization achieved in **v0.11.2 (Phase
5c)** and defines the scope, intent, and structure for work leading
toward a **v1.0 release candidate**.

### Baseline Established

-   **v0.11.2** is explicitly designated as a **stability baseline**,
    not merely a release note.

-   Core workflows for contacts, engagements, dashboard behavior, and
    data handling are considered **predictable, safe, and correct** as
    of this version.

-   Phase 6 is framed as a transition from fixing issues to **completing
    and maturing workflows**.

### Phase 6 Objective

Phase 6 is defined as **Workflow Completion & UX Maturity**, with the
following priorities:

-   Data safety over destructive actions

-   Workflow clarity over feature expansion

-   UX maturity appropriate for a v1.0 product

-   Closing provisional or deferred workflows rather than introducing
    new concepts

By the end of Phase 6, Ulysses CRM should feel **complete, intentional,
and release-candidate ready**.

### Core Design Decision (Canon)

-   **Hard deletion of contacts is permanently excluded.**

-   **Contact Archiving replaces deletion** as a foundational design
    choice.

-   Rationale includes:

    -   Preservation of interconnected data (engagements, tasks,
        transactions, profiles)

    -   Reversibility and safety

    -   Reduced risk approaching v1.0

```{=html}
<!-- -->
```
-   This decision is treated as non-negotiable unless revised in this
    reference thread.

### Phase 6 Scope (High-Level)

Phase 6 explicitly includes:

-   Contact archiving and lifecycle controls

-   Follow-up logic redesign

-   Independent (non-contact) tasks

-   Listing and offer status finalization

-   Per-square-foot commercial pricing

-   Associated contacts UX improvements

-   Past client isolation rules

-   Imported contacts activation flow

-   Seller-side showing feedback (manual)

-   Checklist auto-save UI polish

-   Engagement log UX clarity improvements

Explicitly **out of scope**:

-   Hard deletion

-   Major schema redesigns

-   Client portals or external access

-   Automated email workflows

-   IDX / MLS integrations

-   Reporting or analytics dashboards

### Structural Decision: Phase 6 Subdivision

Phase 6 is formally subdivided into three controlled execution phases:

-   **Phase 6a --- Data Safety & Lifecycle Controls (P0)**

    -   Contact archiving

    -   Past client isolation rules

    -   Imported contacts activation flow

```{=html}
<!-- -->
```
-   **Phase 6b --- Workflow Completion & Logic Alignment (P1)**

    -   Follow-up logic redesign

    -   Independent tasks

    -   Listing and offer statuses

    -   Per-square-foot commercial pricing

```{=html}
<!-- -->
```
-   **Phase 6c --- UX Maturity & Confidence Polish (P2)**

    -   Engagement log UX polish

    -   Associated contacts UX

    -   Seller-side showing feedback

    -   Checklist auto-save indicators

This subdivision is adopted to reduce risk, prevent scope bleed, and
allow disciplined progression toward v1.0.

### Process & Continuity Decisions

-   This chat is designated as the **"reference of truth"** for Phase 6.

-   Future chats will be **execution-scoped only** (Phase 6a, 6b, 6c
    separately).

-   Phase execution chats must not redefine scope or design decisions
    set here.

-   Revisions to Phase 6 itself must occur in this reference thread, not
    in execution chats.

-   v0.11.2 remains the behavioral baseline throughout Phase 6 unless
    explicitly changed.

### Guiding Principles Reinforced

-   No surprise refactors

-   No unapproved schema changes

-   Favor clarity over cleverness

-   Preserve backward compatibility

-   Replace destructive actions with reversible states

-   Every workflow should feel intentional and complete

### Phase & Version Transition

-   **Phase 5c** formally closed with v0.11.2 as a stability milestone.

-   **Phase 6** opened as the final pre-v1.0 workflow-completion phase.

-   Target versions for Phase 6 are **v0.12.x**, progressing toward a
    **v1.0 release candidate**.

### Outcome

This chat locks in Phase 6 intent, scope, and structure, and establishes
a disciplined execution model for the remaining pre-v1.0 work on Ulysses
CRM.

**Ulysses CRM -- Commission Engine Discussion**\
**Date:** January 12, 2025

### Context & Goal

This discussion explored whether Dennis's existing Excel-based
commission formula and projections could be incorporated directly into
Ulysses CRM, eliminating the need to rely on external spreadsheets. The
broader goal was to assess feasibility, scope, timing, and architectural
fit within the Ulysses roadmap.

### Key Conclusions & Decisions

1.  **Feasibility Confirmed**

    -   Commission logic can be implemented in Ulysses at both:

        -   A **high-level** (simple, per-transaction commission
            calculator).

        -   A **granular level** (full commission engine with splits,
            fees, referrals, projections, and reporting).

    ```{=html}
    <!-- -->
    ```
    -   The existing Excel logic maps cleanly to a structured data
        model.

```{=html}
<!-- -->
```
1.  **Add-On Architecture Chosen**

    -   The commission functionality will be implemented as an
        **optional add-on module**, not part of core Ulysses.

    -   It will be:

        -   Feature-flagged.

        -   UI-hidden unless enabled.

        -   Lightly coupled to Transactions.

    ```{=html}
    <!-- -->
    ```
    -   This reinforces the principle that Ulysses core remains
        workflow-first, not accounting-first.

```{=html}
<!-- -->
```
1.  **Editable Inputs & Projections Confirmed**

    -   Commission terms will be **fully editable**, both:

        -   Via user-level defaults.

        -   Via per-transaction overrides.

    ```{=html}
    <!-- -->
    ```
    -   The system will support:

        -   Pipeline projections.

        -   Probability-weighted forecasting.

        -   Quarter-based rollups.

        -   Actual vs projected commission tracking.

```{=html}
<!-- -->
```
1.  **Explicit Deferral Until After v1.0**

    -   The Commission Engine is **explicitly deferred until after Phase
        7 / Version 1.0**.

    -   It is not a blocker for current phases.

    -   This decision was locked as a roadmap commitment.

### Design Principles Reinforced

-   **Core stability before financial complexity**: v1.0 must focus on
    trust, workflow reliability, and data safety.

-   **Modular extensibility**: Advanced features should ship as opt-in
    add-ons.

-   **Design-now, build-later**: Data models and transaction logic
    should not block future commission features, even if not implemented
    yet.

-   **Incremental delivery**: Commission functionality should roll out
    in tiers (Lite → Pro), not as a single monolithic release.

### Roadmap Impact

-   **No changes to Phase 6 or Phase 7 scope**

-   **Post-v1.0 (Phase 8 / v1.1+)**:

    -   Introduce Financial Add-Ons category.

    -   Commission Engine is the first planned add-on.

    -   Possible future extensions include referral tracking and expense
        attribution.

### Canon Roadmap Note (Locked)

The Commission Engine (editable commission logic with projections) will
be implemented as an optional, feature-flagged add-on to Ulysses CRM
after Phase 7 / v1.0. It is explicitly deferred and not part of core
v1.0, but the system should remain designed to support it.

### Outcome

This chat resulted in a clear, locked architectural and roadmap decision
that preserves momentum toward v1.0 while setting the foundation for a
powerful post-launch upgrade path.

## Ulysses CRM --- Phase 6(ab) Completion & Phase 6c Transition

**Date:** January 13, 2025

## Context & Goal of This Session

This session served to **close out all remaining Phase 6a and 6b work**
by grouping unfinished items into a consolidated **Phase 6(ab)**
catch-up effort, ensuring no regression, no destructive behavior, and no
unfinished lifecycle logic before advancing to Phase 6c.

Primary objectives were:

-   Finalize **Imported Contacts Activation Flow**

-   Complete and normalize **Listing & Offer Status lifecycles**

-   Ensure **production parity** (schema + app layer)

-   Confirm UX intent and guardrails before moving to Phase 6c

## Key Decisions & Outcomes

### 1. Phase Structure Adjustment

-   Remaining Phase 6a and 6b items were intentionally grouped into
    **Phase 6(ab)**.

-   This avoided reopening completed phases while preserving linear
    project history.

-   Phase 6(ab) is now **officially closed**.

## Features Implemented (Phase 6(ab))

### Imported Contacts Activation Flow (Completed)

-   Added `contact_state` column with allowed values:

    -   `imported`

    -   `active`

    -   `inactive`

```{=html}
<!-- -->
```
-   Implemented DB-level CHECK constraint.

-   Preserved existing import provenance by:

    -   Leaving `"Imported from FlexMLS"` in `notes`

    -   Using notes only for one-time backfill logic

```{=html}
<!-- -->
```
-   Ran **production-only SQL update** to mark FlexMLS imports as
    `imported`.

-   Established rule:

    -   **State controls behavior**

    -   **Notes preserve history**

```{=html}
<!-- -->
```
-   Imported contacts are excluded from:

    -   Dashboard

    -   Follow-ups

    -   Active workflows

```{=html}
<!-- -->
```
-   Visibility of imported contacts is deferred to Phase 6c via UI
    surfacing.

**Design principle reinforced:**\
*No silent data mutation. State drives behavior; notes preserve
context.*

### Listing & Offer Status Lifecycle Normalization (Completed)

-   Audited `transactions` schema and constraints.

-   Normalized `listing_status` and `offer_status` values.

-   Updated defaults:

    -   New transactions always start in `draft`.

```{=html}
<!-- -->
```
-   Implemented application-level guardrails to prevent invalid state
    writes.

-   Confirmed that:

    -   Statuses are **editable only after transaction creation**

    -   Lifecycle changes occur intentionally in **Edit Transaction**

```{=html}
<!-- -->
```
-   UI clarity improvement:

    -   Renamed **"Listing Status" → "MLS Status"**

```{=html}
<!-- -->
```
-   Confirmed this behavior is **intentional and correct**, not a
    regression.

**Design principle reinforced:**\
*New transaction = intent, not reality. Lifecycle truth is applied only
after creation.*

### Production Parity & Stability

-   Resolved multiple schema-drift and migration-ordering issues.

-   Confirmed:

    -   App code can safely deploy before DB migration.

    -   DB migrations are idempotent and production-safe.

```{=html}
<!-- -->
```
-   Ensured production sanity after fixes:

    -   No crashes

    -   No invalid constraints

    -   No UI regressions

```{=html}
<!-- -->
```
-   `app.py` changes committed and pushed to `main`.

## UX & Workflow Decisions Confirmed

-   Imported contacts should **remain visible in data**, but not active
    workflows.

-   Imported contacts will receive their own **Contacts tab** in Phase
    6c.

-   Tab order decision recorded:

    -   All

    -   Buyers

    -   Sellers

    -   Leads

    -   Past Clients

    -   **Imported** (Phase 6c)

    -   (Future) Inactive

```{=html}
<!-- -->
```
-   Inactive contacts explicitly deferred until a future phase.

## Phase & Version Transitions

### Phase Status

-   Phase 6a: Complete

-   Phase 6b: Complete

-   Phase 6(ab): **Closed in this session**

-   Phase 6c: **Opened**

### Version Transition

-   Entering **Phase 6c**

-   Target version: **v0.11.5**

## Phase 6c Scope Reaffirmed (No Work Yet)

-   Engagement Log UX polish ("Edit" → "View / Edit")

-   Associated Contacts UX improvements

-   Imported Contacts UI tab

-   Seller-side showing feedback (manual only)

-   Checklist auto-save indicator polish

-   No schema changes unless explicitly approved

## Final Outcome

This session successfully:

-   Eliminated all remaining Phase 6a/6b gaps

-   Locked in lifecycle safety and clarity

-   Preserved data integrity and provenance

-   Established a clean, confident transition into Phase 6c

**Phase 6(ab) is formally closed.**\
The system is now ready for **Phase 6c UX maturity work** under version
**v0.11.5**.

**Project Evolution Summary -- Ulysses CRM**\
**Date:** January 15, 2025

### Context and Goal

The purpose of this work session was to design and implement a
**newsletter signup and contact capture workflow** for the Keyport
community that integrates cleanly with **Ulysses CRM**, modeled after
the existing Open House sign-in architecture. The goal was to ensure
that newsletter subscribers are captured as first-class contacts in
Ulysses while using an external platform (Substack) for content
delivery.

## Primary Goals Established

-   Create a **public newsletter signup mechanism** that feeds directly
    into Ulysses CRM.

-   Preserve Ulysses as the **system of record** for contacts, metadata,
    and engagement history.

-   Use Substack strictly as the **distribution layer**, not the
    authoritative contact database.

-   Ensure public signup pages **do not appear as part of the
    authenticated Ulysses UI**, even when accessed by a logged-in user.

-   Reuse proven Open House sign-in patterns wherever possible.

## Key Decisions Made

### 1. Architecture: Split Responsibilities

-   **Substack** will handle:

    -   Email delivery

    -   Unsubscribes

    -   Public newsletter archive

```{=html}
<!-- -->
```
-   **Ulysses CRM** will handle:

    -   Contact creation and deduplication

    -   Newsletter opt-in tracking

    -   Source attribution

    -   Engagement logging

This reinforced the principle that *Ulysses understands people, Substack
sends emails*.

### 2. Data Model Changes

A migration was created and successfully applied to introduce:

-   Newsletter-specific opt-in fields on `contacts`

-   A new `newsletter_signup_links` table with:

    -   `public_token`

    -   `redirect_url`

    -   activation state

    -   ownership via `created_by_user_id`

This mirrors the Open House public-token pattern and allows future
expansion (multiple campaigns, QR codes, token rotation).

### 3. Public Token Management

-   Public tokens are stored in the database, not in code.

-   Tokens can be rotated safely via SQL updates.

-   Old tokens immediately invalidate old URLs.

-   Token values are never displayed in the UI.

This reinforces Ulysses' design principle of **database-driven
configuration, not hardcoded behavior**.

### 4. Public Page Rendering Strategy (Critical Design Decision)

A key issue emerged:\
The newsletter signup page was rendering inside the full Ulysses UI
(navbar, task modal, authenticated chrome) when accessed by a logged-in
user.

**Root cause identified:**

-   Open House sign-in pages implicitly behave as anonymous pages.

-   Newsletter signup pages are public, but can be accessed while logged
    in.

-   Authentication state alone is insufficient to determine layout
    behavior.

**Resolution:**

-   Introduced the concept of an explicit `is_public_page` flag passed
    to templates.

-   Updated `base.html` to conditionally suppress:

    -   Navbar

    -   Task modal

    -   Task-related JavaScript

```{=html}
<!-- -->
```
-   Added support for a `body_class` variable to align styling with Open
    House (`openhouse-public`).

This established a new, explicit design rule:

*Public pages must declare themselves public, regardless of
authentication state.*

This allows:

-   Previewing public tools while logged in

-   Consistent behavior across future public-facing features

### 5. Template and Route Behavior

-   Newsletter signup and thanks pages were updated to:

    -   Extend the standard base template

    -   Pass `is_public_page=True`

    -   Use the same visual treatment as Open House sign-in

```{=html}
<!-- -->
```
-   No separate `base_public.html` was introduced, avoiding template
    duplication.

## Design Principles Reinforced

-   **Separation of concerns**: delivery vs relationship ownership

-   **Explicit intent over implicit behavior** in templates

-   **Reuse before reinvention** (Open House as architectural reference)

-   **Public does not mean unauthenticated**

-   **Database-driven configuration**

-   **Minimal friction for end users**

## Features Implemented

-   Newsletter signup database schema

-   Public token-based signup links

-   Contact creation and deduplication logic

-   Newsletter opt-in tracking

-   Optional engagement logging

-   Public-page rendering controls

## Features Explicitly Deferred

-   Admin UI for managing newsletter signup links

-   Token rotation history or grace-period redirects

-   Full visual parity between newsletter signup and Open House branding

-   Native newsletter sending from Ulysses

-   Substack API integration

-   Advanced segmentation beyond opt-in flag

These were acknowledged as future (post--v1.0 / Phase 7+) enhancements.

## Phase and Version Context

-   Work occurred during the **Phase 6 era** of Ulysses CRM development.

-   No version bump was performed during this session.

-   Changes align with the architectural direction leading toward v1.0
    readiness, particularly around public-facing tools and multi-context
    rendering.

### Closing Note

This session marked an important maturation point for Ulysses CRM:\
the introduction of **explicit public-page semantics** that decouple
layout behavior from authentication state. This decision lays groundwork
not just for newsletters, but for future community tools, events,
surveys, and public-facing workflows.

The system now supports growing a community audience with dignity,
clarity, and long-term ownership.

**Ulysses CRM --- Phase 6c Development Summary**\
**Date:** January 16, 2025

### Context and Goals

This work session continues the evolution of **Ulysses CRM** following
the formal close of Phase 6b and the transition into **Phase 6c
(v0.11.5)**. Phase 6c is explicitly scoped as a **UX maturity and
confidence polish phase**, with strict guardrails: no schema changes, no
destructive actions, no new workflows, and no automation. The
overarching goal is to make the system feel finished, deliberate, and
trustworthy as it approaches v1.0 readiness.

### Key Decisions

-   **Dashboard-first UX polish:** Although the Imported Contacts tab
    was originally identified as the first Phase 6c task, we
    intentionally pivoted to dashboard improvements after identifying
    immediate UX scaling issues as data volume increases.

-   **"Active" means actionable:** The existing dashboard definition of
    Active Contacts (recent engagement, follow-up scheduled, or
    buyer/seller profile) was validated and preserved. Seed data issues
    confirmed that the logic was correct, reinforcing trust in the
    current model.

-   **Pagination over scrolling:** Dashboard lists were intentionally
    constrained to smaller, paged views rather than long scrolls,
    reinforcing clarity and reducing cognitive load.

-   **Accept "good enough" motion behavior:** Anchor-based navigation to
    avoid losing scroll context was retained despite some residual
    "snap" behavior. More advanced scroll state handling (AJAX or
    JS-based restoration) was explicitly deferred as post-v1.0 work.

### Features Added (Phase 6c)

-   **Active Contacts Dashboard Pagination**

    -   Limited Active Contacts to **10 per page**.

    -   Implemented lightweight paging using a fetch-11/show-10 pattern.

    -   Preserved all existing business logic defining "active."

```{=html}
<!-- -->
```
-   **Dashboard Pagination UX Refinement**

    -   Replaced simple Prev/Next buttons with **Bootstrap pagination
        (pagination-sm)** to match the Contacts page visual language.

    -   Ensured the dashboard pagination is visually quieter and
        subordinate to primary content.

```{=html}
<!-- -->
```
-   **Reusable Pagination Macro**

    -   Introduced a reusable Jinja macro for dashboard pagination.

    -   Eliminated duplication risk and established a consistent pattern
        for future dashboard sections (Past Clients, Recent Engagements,
        Professionals).

    -   Confirmed compatibility with existing Jinja2 constraints (no
        kwargs unpacking).

```{=html}
<!-- -->
```
-   **Seed Data Validation**

    -   Created realistic test contacts to validate dashboard behavior.

    -   Confirmed dashboard filtering behavior based on follow-ups,
        engagements, and profiles.

### Features Explicitly Deferred

-   **Imported Contacts Tab**

    -   Still fully in scope for Phase 6c.

    -   UI-only addition to the Contacts page, filtering by
        `contact_state = 'imported'`.

```{=html}
<!-- -->
```
-   **Past Clients Dashboard Pagination**

    -   Identified as a near-term follow-up using the same pagination
        macro.

```{=html}
<!-- -->
```
-   **Advanced Scroll Handling**

    -   AJAX pagination or scroll-position persistence deferred to
        post-v1.0.

```{=html}
<!-- -->
```
-   **Other Phase 6c Items**

    -   Engagement Log UX polish ("Edit" → "View / Edit").

    -   Seller-side showing feedback (manual entry).

    -   Checklist auto-save indicator polish.

### Design Principles Reinforced

-   **Clarity over quantity:** Dashboards should surface only what is
    actionable.

-   **Consistency builds trust:** UI patterns should match across
    sections (Dashboard and Contacts).

-   **No silent refactors:** UX improvements must not alter business
    logic or data meaning.

-   **Phase discipline:** Features outside the explicit scope are
    consciously deferred, not partially implemented.

### Phase and Version Status

-   **Phase 6a:** Complete

-   **Phase 6b:** Complete

-   **Phase 6(ab):** Closed (catch-up finalized)

-   **Phase 6c:** In progress

    -   Dashboard UX polish substantially complete

    -   Remaining scoped items identified and unchanged

```{=html}
<!-- -->
```
-   **Target version:** v0.11.5

This session solidified Phase 6c's direction as a refinement phase,
improved dashboard scalability and coherence, and laid a clean
foundation for completing the remaining UX-only items without risking
regression or scope creep.

## Phase 6c — Final Implementation & Close-Out Chat
**Date:** January 16, 2025  
**Target Version:** v0.11.5  
**Status:** Phase 6c Closed

### Purpose of This Chat
This chat served as the **final execution, verification, and close-out session** for Phase 6c. The focus was on completing all remaining UX polish items, validating behavior against canon rules, resolving edge-case UI friction, and formally confirming that Phase 6c objectives were satisfied without scope creep or architectural drift.

### Key Work Completed

#### Engagement Log UX Finalization
- Verified that all “Edit” actions in the Engagement Log were renamed to **View / Edit**
- Confirmed page titles, buttons, and navigation consistency
- Ensured no routing, permission, or workflow changes were introduced
- Marked this item complete and closed

#### Associated Contacts UX Refinement
- Resolved unintended auto-save behavior when selecting an existing contact
- Modal now remains open until explicit confirmation
- Introduced dynamic CTA: **Link <Selected Name>**
- Added confirmation language clarifying bidirectional relationship visibility
- Verified edit-association modal behavior and persistence
- No schema or routing changes introduced

**Explicitly deferred by decision (not omission):**
- Disable link action until relationship type entered
- Reset modal selection state on close
- Additional visual highlight polish

#### Imported Contacts Verification
- Confirmed imported contacts governed strictly by `contact_state`
- Imported contacts searchable but hidden from default views
- Manual activation and keep-inactive flows verified
- UI display bug resolved and state alignment confirmed

#### Dashboard UX Confirmation
- Pagination and limits verified for Active Contacts and related lists
- Known page-jump behavior accepted as non-blocking

### Canon Compliance Check
- Verified adherence to `ULYSSES_CRM_CANON.md` guardrails
- No schema drift
- No destructive actions
- No incomplete or partially implemented features

### Phase 6c Closure Determination
All Phase 6c objectives were satisfied. All deferrals were explicit and intentional.  
**Phase 6c is formally closed.**

### Forward-Looking Note
Remaining UX refinements identified during this phase are intentionally deferred to a future, UI-heavy usability upgrade phase.


## Phase 7A — v1.0.0 Finalization & Release Summary

**Status:** Complete  
**Release:** v1.0.0 (Production)  
**Scope Type:** Hardening, completion, and release readiness  
**Deployment:** Live

### Purpose of Phase 7A
Phase 7A marked the final stabilization and release phase of Ulysses CRM v1.0.0.  
The goal was to harden all previously implemented systems, eliminate architectural gaps, enforce tenant isolation, and ensure the application could be confidently deployed and used in production without feature debt or unsafe assumptions.

No new conceptual features were introduced in Phase 7A. All work focused on completion, correctness, usability, and consistency.

---

### Core Systems Confirmed Complete in v1.0.0

#### Authentication & User System
- Fully implemented user authentication using Flask-Login
- Secure password hashing and validation
- Login, logout, and session management finalized
- Last-login tracking implemented
- Inactive-user enforcement confirmed

#### Owner / Admin Controls
- Owner-only admin access enforced via decorators
- Invite-based user onboarding implemented
- Secure, expiring user invite tokens
- Invite lifecycle handling (create, revoke, consume)
- Active user listing and activation toggling
- Admin dashboard summary counts (users, invites)

#### Tasks System (Phase 5 finalized)
- Full task lifecycle supported:
  - Open
  - Snoozed
  - Completed
  - Canceled
- Task relationships supported:
  - Contacts
  - Transactions
  - Engagements
  - Professionals
- Task modal creation and editing finalized
- Task list filtering by status finalized
- Backend status enforcement confirmed
- Defensive ownership checks on all task actions

#### Transactions, Contacts, Professionals
- Multi-entity relationships stabilized
- UI consistency across list, view, and modal flows
- Defensive deletes (no destructive cascades without intent)
- Contact display-name resolution hardened
- Table layout consistency enforced

#### Engagements
- Transcript handling confirmed
- Summary / notes fallback logic finalized
- Engagement context correctly displayed in tasks and contacts

---

### UI & UX Stabilization
- Consistent page wrapper and layout structure enforced
- Navigation finalized and stabilized
- Modal behavior standardized across features
- Table action-column wrapping prevented
- Flash messaging normalized and styled
- Background and overlay handling finalized for production

---

### Data Safety & Architecture
- All user-facing queries scoped by `user_id`
- No cross-tenant data leakage paths remain
- Defensive guards added around critical INSERT/UPDATE paths
- Production schema parity confirmed
- Version display and environment indicator finalized

---

### Documentation & Canon
- Canonical design and architecture documents locked
- Phase scopes respected and closed
- No unfinished features left dangling at v1.0.0
- Future enhancements explicitly deferred to post-1.0 versions

---

### Explicit Non-Goals of Phase 7A
The following were **intentionally excluded** from v1.0.0 and deferred:
- AI summarization or automation features
- IDX / MLS integrations
- Commission engine
- Multi-user role expansion beyond owner/user
- Custom checklist builders
- Advanced reporting or analytics

---

### Release Outcome
Ulysses CRM v1.0.0 was successfully deployed as a stable, production-ready system with:
- Clear ownership boundaries
- A complete task and engagement workflow
- Admin safety controls
- A clean upgrade path for future patch and minor releases

All subsequent work proceeds under **post-1.0 semantic versioning (v1.0.1+)** and must not retroactively alter Phase 7A scope.




## Tenant Isolation & Open Houses Audit  
**Completed:** January 26, 2026  
**Next Chat Start:** January 26, 2026

### Context & Primary Goal

This audit focused on hardening **Ulysses CRM** for true multi-user tenant isolation, with an emphasis on preventing cross-user data leakage both now and in future phases.

The immediate trigger was unexpected behavior observed in **Professionals** and **Open Houses** once multi-user work began in **Phase 7B**. The broader goal was to methodically audit both database schema and application code to ensure that every user-owned resource is correctly scoped by a `user_id` (or equivalent ownership field), and that all decisions are memorialized to avoid reliance on undocumented or “tribal” knowledge.

---

### Key Design Principles Reinforced

- **SQL-level tenant enforcement is mandatory**  
  Ownership must be enforced in the `WHERE` clause of every `SELECT`, `UPDATE`, `DELETE`, and `EXPORT` query.  
  UI-only or route-level filtering is insufficient.

- **Schema and code must agree**  
  If a table includes a `user_id` or ownership column, *all* routes touching that table must consistently scope by it.

- **No silent assumptions**  
  Any hardcoded ownership values (e.g., `user_id = 1`) are unacceptable once multi-user support exists.

- **Audit-first mindset**  
  All changes are accompanied by:
  - schema inspection
  - grep-based code scanning
  - written audit notes  
  This allows future reconstruction of intent and reasoning.

- **Pause over speed**  
  Development intentionally slowed to avoid subtle multi-tenant bugs that are costly to unwind later.

---

### What Was Completed

#### 1. Professionals (Closed)

- Identified missing `user_id` handling in **Professionals**.
- Confirmed schema includes `professionals.user_id`.
- Updated all related functionality to scope by `current_user.id`:
  - creation
  - listing
  - editing
  - deletion
  - dropdown helpers
- Refactored `get_professionals_for_dropdown()` to explicitly require `user_id`.
- Verified via grep that all call sites pass `current_user.id`.

**Status:** ✅ Tenant-safe and closed.

---

#### 2. Open Houses (Major Work Completed)

Open Houses were identified as a **high-risk area** due to the combination of public access (sign-ins) and private ownership.

##### Schema Audit

- Confirmed:
  - `open_houses.created_by_user_id`
  - `open_house_signins.user_id`
- Verified no `NULL` or invalid `user_id` values in local data.
- Confirmed indexing and foreign key constraints.

##### Routes Updated for Tenant Isolation

The following routes were explicitly updated and verified:

- **Create Open House**
  - `created_by_user_id = current_user.id`
  - Removed hardcoded user IDs
  - Correct handling of `RETURNING id`

- **List Open Houses**
  - `WHERE created_by_user_id = current_user.id`

- **Open House Detail**
  - `WHERE id = %s AND created_by_user_id = %s`

- **Export CSV**
  - `WHERE open_house_id = %s AND user_id = %s`

- **Public Open House Sign-In**
  - Public token resolves owning user (`owner_user_id`)
  - Contacts are matched or created under the owner’s user account
  - `open_house_signins.user_id = owner_user_id` enforced on insert

##### Outcomes Ensured

- Public visitors cannot leak data across tenants
- Owners only see their own sign-ins
- CSV exports cannot exfiltrate other users’ data

**Status:** ✅ Functionally tenant-safe and verified locally.

---

#### 3. Audit Infrastructure Added

To support systematic review and long-term safety, a formal audit structure was introduced:

- Created `docs/audits/`
- Added:
  - `schema_local.sql`
  - `schema_local_tables.txt`
  - `2026_01_25_phase_7b_multi_user_audit.md`
  - `2026_01_25_tenant_isolation_audit.md`

- Performed scripted scans to:
  - identify tables with `user_id`
  - identify ownership fields such as `created_by_user_id`
  - cross-reference schema with code usage

This establishes a **repeatable audit pattern** for remaining modules.

---

#### 4. Tasks (Confirmed Safe)

Tasks were reviewed and confirmed to already meet tenant-isolation standards:

- All task mutations enforce `WHERE user_id = %s`
- Helper functions centralize ownership enforcement
- No raw task queries bypass tenant scope
- Schema includes appropriate constraints and indexes

**Status:** ✅ Explicitly confirmed and closed.

---
## Phase 7B — Agent Identity Foundations and My Profile  
**Completed:** January 28, 2026  
**Next Chat Start:** January 28, 2026

### Context & Goal

Phase 7B continued post-v1.0 work under patch semantics (v1.0.1+) to complete multi-user hardening and establish agent identity foundations so the system is safe for multiple users and self-configurable by each agent.

The immediate implementation goal was to add a first-class, tenant-safe user profile page so identity data used by Templates and footers can be configured without code edits.

---

### What Was Completed

#### 1. Agent and Brokerage Identity Data Model (Closed)

- Extended `users` with agent identity fields:
  - `title`
  - `agent_phone`
  - `agent_website`
  - `license_number`
  - `license_state` (added during implementation as a low-risk, forward-compatible schema extension)
- Confirmed `brokerages` exists as a strict 1:1 table keyed by `user_id`:
  - `brokerages.user_id` is PRIMARY KEY and NOT NULL
  - Foreign key to `users(id)` with `ON DELETE CASCADE`
- Confirmed footer identity rendering contract:
  - `_get_brokerage_footer()` is the single integration point for Templates and related output
  - Agent contact appears before brokerage contact by design
  - Agent website is shown ahead of brokerage website by design
  - City/state formatting uses a comma separator

**Status:** ✅ Closed.

---

#### 2. My Profile Page (Closed)

- Added a logged-in profile page for the current user:
  - Route: `/account` (GET/POST)
  - Template: `templates/account/profile.html`
- Implemented tenant-safe reads and writes:
  - Users are updated via `WHERE id = current_user.id`
  - Brokerages are upserted via `ON CONFLICT (user_id)` and always written under `current_user.id`
- Implemented safe update semantics to avoid accidental data loss:
  - Uses `COALESCE(NULLIF(..., ''), existing_value)` so blank inputs do not overwrite existing values
- Added an Account link in the navbar targeting `url_for('account')`
- Resolved endpoint drift by removing the legacy `account_profile` endpoint and updating navbar references accordingly

**Status:** ✅ Closed.

---

#### 3. Account Creation Consistency (Closed)

- Accept-invite and My Profile now share a single, canonical field contract for identity data.
- Phone formatting is consistent via a global, opt-in formatter:
  - Global formatter lives in `base.html`
  - Fields opt in by adding the `phone-input` class
  - Implemented in both:
    - `templates/account/profile.html`
    - `templates/auth/accept_invite.html` (agent phone)

**Status:** ✅ Closed.

---

### Noted Future Enhancement

- Multi-state licensing should eventually be supported beyond a single `users.license_state` field.
  - Expected approach: a structured per-user licenses model (e.g., separate licenses table) introduced in a later phase.

---

### Release Guidance

These changes constitute a patch-level release candidate.

- Recommended next patch version: **v1.0.1**
- Ensure production parity includes any schema additions introduced locally (notably `users.license_state`) before deploying the patch.

---

# Phase 7B Closeout & Transition Document

**Project:** Ulysses CRM
**Version Tagged:** v1.0.2
**Date Closed:** 2026-01-31

---

## Purpose of This Document

This document closes **Phase 7B (User Onboarding & Tenant Isolation Hardening)** and serves as a clean handoff for the *next chat / next phase*. It captures what is complete, what is locked, what assumptions now hold, and what the next conversation can safely build on without re-auditing prior work.

---

## Phase 7B Objectives (Recap)

Phase 7B focused on safely introducing multi-user support **without compromising tenant isolation** or Canon ownership rules.

Primary goals:

* Invite-only onboarding (no self-registration)
* Hard tenant isolation enforced at SQL level
* Admins can manage users *without* seeing user data
* Token-based invites and resets (no SMTP)
* Prepare system for post-v1.0 extensibility

All goals are now **met and verified**.

---

## What Is Complete and Locked

### 1. User Onboarding (Invite-Only)

* Admin can create invites
* Secure, single-use, time-limited tokens
* Accept-invite flow creates:

  * user account
  * profile fields
  * brokerage record (user-owned)
* Invite consumption is atomic and transactional
* Password reset flow mirrors invite flow

**Status:** CLOSED ✅

---

### 2. Tenant Isolation (Hard Enforcement)

**Canonical tenant key:** `user_id`

Approved alternate keys:

* `created_by_user_id` (Open Houses)
* derived owner via token (public routes)

All affected areas audited and fixed:

* Contacts
* Engagements
* Tasks
* Transactions
* Professionals
* Open Houses + Sign-ins
* Templates

Negative tests performed:

* Cross-user ID guessing returns 404
* Exports scoped by tenant
* Public routes derive owner safely

**Status:** CLOSED ✅

---

### 3. Templates Tenant Isolation

* `templates.user_id` added
* Backfilled safely
* Indexed by tenant + category + timestamps
* Foreign key enforced (prod-safe follow-up migration)

**Status:** CLOSED ✅

---

### 4. Phone & URL Normalization (UI Standard)

**Phone:**

* Opt-in via `phone-input` class
* Auto-format on blur: `(555) 555-5555`

**URLs:**

* Accept `example.com`, `www.example.com`, or full URLs
* No forced `https://` on input
* Stored clean for future linking

Applied to:

* Profile
* Accept Invite
* Admin flows

**Status:** CLOSED ✅

---

### 5. Invite / Reset Link Safety

* `PUBLIC_BASE_URL` required in production
* No fallback to localhost in prod
* Fail-fast if misconfigured
* Links built without request inference

**Status:** CLOSED ✅

---

## Versioning & Releases

* **v1.0.2**

  * Phase 7B fully complete
  * Tagged and pushed
  * Production verified

Versioning discipline restored:

* Next work begins at **v1.0.3+**

---

## Canon Status

Canon laws upheld:

* Tenant isolation at SQL level
* No admin data access
* No implicit ownership
* Local-first, prod-safe migrations
* Explicit version tagging

Phase 7B is formally **closed in Canon**.

---

## Known Deferrals (Intentional)

* SMTP email delivery
* 2FA
* Teams / shared data
* IDX integrations
* Commission Engine

All deferrals are documented and intentional.

---

## Safe Starting Point for Next Chat

The next chat may safely assume:

* Multi-user system is stable
* Tenant isolation is enforced
* User onboarding is production-ready
* No further Phase 7B audits required

Recommended next topics:

* Phase 8 planning
* Post-v1.0 enhancements
* UX polish
* Optional add-on modules

---

**Phase 7B: COMPLETE.**

This document is the authoritative handoff for all future work.
-------------------------


## 2026-02-03 — Associations + Task Modal Fixes (Contact Edit)

### Summary
Two user-facing issues were resolved:
1) Creating an associated contact was accidentally inserting a new contact twice due to duplicated INSERT logic in the route.
2) The "+ Task" modal from Edit Contact either hung on "Loading..." or failed to open due to mismatched invocation patterns and DOM/template issues. Contact prefill was also not reliably applied.

A template hygiene issue (duplicate element IDs) was found to be a root cause of strange behavior inside the task modal.

### Changes

#### 1) Associated Contacts: Create-and-Link route cleanup
- Route: `/contacts/<int:contact_id>/associations/create`
- Removed the accidental duplicate contact INSERT path. The route should create exactly one contact, then create one association, then commit once.
- Confirmed tenant safety: validates parent contact ownership via `contacts.user_id = current_user.id` before creating child contact or association.

Canon Law reinforced:
- **One DB action per intent.** No duplicate INSERT paths inside a single route.
- **Tenant enforcement at SQL level** before performing cross-table writes.

#### 2) Task Modal: Open from Edit Contact with proper prefill and return path
- Standardized the working pattern: the Edit Contact "+ Task" button calls:
  - `openTaskModal(url, title)` with a URL that points to `tasks_new` in modal mode and includes:
    - `modal=1`
    - `contact_id=<current contact>`
    - `next=/edit/<id>#engagements` (or the appropriate anchor)
- This guarantees:
  - The modal loader fetches HTML successfully (no infinite Loading state).
  - The task form is rendered with the correct prefilled contact.
  - Post-save redirects back to the contact page anchor.

Canon Law reinforced:
- **Use a single modal source of truth.** The task modal is owned by `base.html` (one instance in DOM).
- **Modal content should come from modal endpoints or modal mode on existing endpoints** (here: `tasks_new?modal=1`), with prefill passed via querystring.

#### 3) Task form modal template hygiene: remove duplicate IDs
- File: `templates/tasks/form_modal.html`
- Removed a second, incorrect block that duplicated:
  - `id="taskContactSelected"`
  - `id="taskContactSelectedLabel"`
  - `id="taskContactClear"`
- Verified with:
  - `grep -n 'id="taskContactSelected"' templates/tasks/form_modal.html` returning exactly one match.
- This eliminated unpredictable selector behavior and inconsistent UI state in the modal.

Canon Law reinforced:
- **IDs must be unique within rendered DOM.** Duplicate IDs break querySelector/getElementById assumptions and create non-deterministic UI bugs.

#### 4) Template cleanup: remove unused task modal template
- Removed `templates/tasks/task_modal.html` after confirming the modal lives in `base.html` and is loaded via `openTaskModal()`.

### Files touched
- `app.py`
- `static/js/task_form.js`
- `templates/base.html`
- `templates/edit_contact.html`
- `templates/tasks/form_modal.html`
- Deleted: `templates/tasks/task_modal.html`

### Operational notes
- Preferred working pattern for opening task modal:
  - From any context, build a URL to `tasks_new` with `modal=1` and any prefill params (contact_id, next).
  - Call `openTaskModal(url, 'New Task')`.
- Avoid introducing alternate modal containers or duplicate modal markup across templates.

----------------
## Project History

### 2026-02-07 — AI Enablement, Guards, and Canon Handling

Key outcomes:
- AI functionality successfully enabled in production with per-user controls
- AI access confirmed to require both database enablement and server-level configuration
- User-level AI governance fields validated in production schema
- Daily and monthly AI guardrails confirmed operational
- Requirements.txt update identified and corrected as part of AI rollout
- Canon document handling clarified: future canon updates will be delivered as additive patches rather than full replacements

Design principles reinforced:
- No silent feature activation
- Explicit user consent for AI
- Canon treated as a living but controlled specification


