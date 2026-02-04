# ULYSSES CRM

## Release Checklist and Rollback Plan – v1.1.0

**Feature Line:** Phase 8.1 – AI-Assisted Engagement Intelligence  
**Release:** v1.1.0  
**Baseline:** Production v1.0.3  
**Status:** Canon-bound operational plan

---

## 1. Purpose

This document defines a production-safe checklist for shipping Ulysses v1.1.0 and a rollback posture that prioritizes:

* Stability
* Tenant safety
* Predictable costs
* Fast disablement if needed

The plan assumes production operations should be forward-only at the database layer and that rollback is primarily achieved through feature gating.

---

## 2. Release Strategy

### 2.1 Primary Safety Mechanism

AI is protected by two independent gates:

1. Global flag: `AI_FEATURES_AVAILABLE`
2. User opt-in: `users.ai_enabled`

In any failure scenario, disablement is achieved by setting the global flag to false.

---

## 3. Pre-Release Checklist (Local)

### 3.1 Code and Configuration

* Confirm OpenAI keys are not hard-coded anywhere
* Confirm OpenAI key is read only from environment
* Confirm logs do not print transcripts or raw AI responses
* Confirm prompt version binding is enforced (`v1.1.0` only)

### 3.2 Database

* Apply migration to local DB
* Verify columns exist with `\d+ users`
* Confirm defaults fail closed:

  * `ai_enabled = false`
  * `ai_daily_request_limit = 0`
  * `ai_monthly_spend_cents = 0`

### 3.3 UI

* Confirm “Summarize transcript” button is hidden or disabled when AI is off
* Confirm Settings toggle exists and is off by default
* Confirm modal displays disclosure text

### 3.4 Backend

* Confirm endpoint requires authentication
* Confirm tenant ownership enforcement on `engagement_id`
* Confirm guard denies:

  * AI disabled
  * daily limit exceeded
  * monthly cap exceeded
  * empty transcript

### 3.5 Behavioral Tests

* Empty transcript returns clean 400 error
* Non-owner engagement_id returns 404
* AI disabled returns 403
* Daily limit returns 429
* Monthly cap returns 429
* Upstream failure returns 502 or 504 and does not increment counters

---

## 4. Pre-Release Checklist (Production)

### 4.1 Configuration Freeze

Before any production changes:

* Ensure `AI_FEATURES_AVAILABLE` remains false
* Ensure OpenAI API key is configured in production secret store but unused until enabled

### 4.2 Database Migration

* Apply `2026_02_03_ai_optin_usage_controls_v110.sql` using production-safe process
* Verify schema immediately after:

  * Columns exist
  * Defaults correct
* Do not enable AI yet

### 4.3 Deploy Application

* Deploy v1.1.0 code with global AI disabled
* Verify core application paths are healthy:

  * Login
  * Contacts list and edit
  * Engagement create and edit
  * Tasks
  * Transactions

---

## 5. Enablement Checklist (Controlled)

After v1.1.0 is deployed and stable with AI disabled:

1. Enable `AI_FEATURES_AVAILABLE = true`
2. Confirm UI now displays AI affordances only for opted-in users
3. Opt in only your user account
4. Set conservative limits for your account:

   * daily request limit
   * monthly cap
5. Run real-world tests from Engagement modal

Only after successful results:

* Invite additional users to opt in, if desired

---

## 6. Post-Release Verification

### 6.1 Functional Verification

* Summarization works end-to-end
* Output formatting matches contract
* Save and discard behaviors are correct
* Transcript remains unchanged
* AI output is not persisted unless explicitly saved

### 6.2 Cost and Counter Verification

* `ai_daily_requests_used` increments only on success
* `ai_monthly_spend_cents` increments only on success
* Daily reset logic works when date changes
* Monthly reset logic works at month boundary

### 6.3 Tenant Safety

* Confirm no cross-user engagement access is possible
* Confirm no cross-user usage counters are affected

---

## 7. Rollback and Emergency Response Plan

### 7.1 Primary Rollback (Preferred)

If anything goes wrong:

* Set `AI_FEATURES_AVAILABLE = false`

This immediately:

* Removes AI functionality from the UI
* Prevents AI endpoint execution server-side
* Stops all AI spend

This is the default rollback posture.

---

### 7.2 Secondary Response (If Needed)

If issues relate to a specific account:

* Set `users.ai_enabled = false` for the affected user

If issues relate to runaway usage:

* Set `ai_daily_request_limit = 0` for all users
* Set `ai_monthly_cap_cents = 0` or null and rely on the global flag

---

### 7.3 Code Rollback

If a code rollback is required:

* Revert to v1.0.3 application code
* Keep the new `users` columns in place

Columns are additive and should not break older code if the older code ignores them.

Avoid dropping columns in production.

---

## 8. Release Completion Criteria

v1.1.0 is considered complete when:

* Production is running v1.1.0
* AI is globally enabled or deliberately kept disabled
* For any enabled user, AI runs only on explicit request
* Costs and counters behave predictably
* No existing workflows regress

---

## 9. Canon Statement

> *Ulysses releases fail closed. When uncertainty exists, AI must be disabled globally rather than partially trusted.*
