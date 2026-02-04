# ULYSSES CRM

## AI Feature Flag and Opt-In Enforcement Specification – v1.1.0

**Feature:** AI-Assisted Engagement Summarization  
**Release:** v1.1.0 (Phase 8.1)  
**Baseline:** Production v1.0.3  
**Status:** Canon-bound specification

---

## 1. Goal

Enable AI features only when a user explicitly opts in, and enforce that decision in both the UI and backend so AI functionality can never execute accidentally or implicitly.

---

## 2. Design Laws

The following laws are binding for this feature:

* AI is disabled by default
* AI requires explicit user opt-in
* Opt-in is enforced server-side
* Feature availability is tenant-safe
* Usage caps prevent surprise billing
* AI requests are user-initiated only

---

## 3. Storage Model

### 3.1 Opt-In Scope

AI opt-in is stored at the **user level**.

Rationale:

* Aligns with tenant isolation
* Supports future per-user pricing or add-ons
* Avoids accidental system-wide enablement

---

### 3.2 Recommended Schema Changes

Add the following fields to the `users` table:

* `ai_enabled` boolean not null default false
* `ai_monthly_cap_cents` integer nullable
* `ai_monthly_spend_cents` integer not null default 0
* `ai_last_monthly_reset_at` timestamp nullable
* `ai_daily_request_limit` integer not null default 0
* `ai_daily_requests_used` integer not null default 0
* `ai_last_daily_reset_at` date nullable

Notes:

* Monetary values should be stored as integer cents
* Timestamps should follow the application timezone (America/New_York)

---

## 4. Backend Enforcement

### 4.1 Central Guard Function

All AI routes must invoke a single guard function prior to any OpenAI request.

**Guard Conditions**

1. `current_user.ai_enabled` is true
2. Daily request limit not exceeded
3. Monthly spend cap not exceeded
4. User-supplied text is present and non-empty
5. Optional hard limit on input length

**Failure Responses**

* 403 Forbidden: AI not enabled
* 429 Too Many Requests: daily limit exceeded
* 429 Too Many Requests: monthly cap exceeded

---

### 4.2 Atomicity and Safety

Usage counters must be updated only after a successful OpenAI response.

Rules:

* Call OpenAI first
* On success, increment daily request count and monthly spend
* On failure, do not increment any counters

This prevents charging for failed or rejected requests.

---

## 5. UI Enforcement

### 5.1 Account Settings

Add an **AI Features** section to user settings containing:

* Toggle: Enable AI assistance
* Disclosure text explaining:

  * AI is optional and disabled by default
  * AI runs only on explicit user action
  * No automation of tasks, emails, or decisions
  * Usage is metered

If enabled, display:

* Monthly usage and remaining cap (if configured)
* Daily request usage and remaining requests

---

### 5.2 Engagement UI

In the Engagement detail view:

**If AI is disabled**

* Hide or disable the Summarize button
* Display message: “AI assistance is off. Enable it in Settings.”

**If AI is enabled**

* Display the “Summarize transcript” button
* On click, open a modal that includes:

  * Brief disclosure
  * Generate action
  * AI output preview
  * Options to Save or Discard

UI checks are advisory only. Backend enforcement is mandatory.

---

## 6. Feature Flag Layers

Two layers of control are required:

### 6.1 Global Application Flag

* `AI_FEATURES_AVAILABLE` (default false)
* Allows deployment without exposure
* Can be enabled without redeploying

### 6.2 User-Level Flag

* `users.ai_enabled`
* Must be true for any AI request to proceed

Both flags must be true for AI functionality to be available.

---

## 7. Rollout Strategy

Recommended sequence:

1. Deploy code with global flag disabled
2. Enable globally in a controlled environment
3. Test end-to-end
4. Enable in production
5. Keep AI disabled by default for all users
6. Invite selected users to opt in

---

## 8. Disclosure Copy Requirements

Disclosure language should be consistent across settings and modals:

* “AI assistance is optional and disabled by default.”
* “AI runs only when you click Generate.”
* “Review and edit results before saving.”
* “Do not paste sensitive credentials or private identifiers.”

---

## 9. Definition of Done

This specification is complete when:

* User-level opt-in fields exist in the database
* Settings UI can toggle AI enablement
* Engagement UI reflects opt-in state
* Backend rejects AI requests when not opted in
* Usage caps prevent surprise billing

---

## 10. Canon Statement

> *In Ulysses CRM, AI capabilities are gated by explicit user consent and enforced at every layer. Convenience never overrides intent, safety, or accountability.*
