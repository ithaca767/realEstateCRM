# ULYSSES CRM

## Database Migration Plan – AI Opt-In and Usage Controls (v1.1.0)

**Feature Line:** Phase 8.1 – AI-Assisted Engagement Intelligence  
**Release:** v1.1.0  
**Baseline:** Production v1.0.3  
**Scope:** Minimal users-table additions only  
**Status:** Canon-bound implementation plan

---

## 1. Goal

Add the minimal user-level fields required to:

* Keep AI disabled by default
* Allow explicit opt-in per user
* Enforce daily request limits
* Enforce monthly spend caps
* Track usage counters safely

No other schema changes are included in v1.1.0.

---

## 2. File Naming Convention

Create a forward-only migration SQL file in `docs/migrations/`.

Recommended file name:

* `docs/migrations/2026_02_03_ai_optin_usage_controls_v110.sql`

Notes:

* Use the actual date you create the file
* Keep naming consistent with existing production-safe migration files

---

## 3. Schema Changes

### 3.1 Table: `users`

Add these columns:

* `ai_enabled` boolean not null default false
* `ai_daily_request_limit` integer not null default 0
* `ai_daily_requests_used` integer not null default 0
* `ai_last_daily_reset_at` date null
* `ai_monthly_cap_cents` integer null
* `ai_monthly_spend_cents` integer not null default 0
* `ai_last_monthly_reset_at` date null

Design notes:

* Monetary values are integer cents
* Defaults are safe and conservative
* `ai_daily_request_limit = 0` means no AI requests allowed even if opted in, unless you set it to a positive number (this is a deliberate safety stance)
* Reset dates are stored as dates so you can compare in America/New_York without timezone ambiguity

---

## 4. Forward Migration SQL (Canonical Draft)

Place this in the migration file.

```sql
BEGIN;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS ai_enabled boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS ai_daily_request_limit integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS ai_daily_requests_used integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS ai_last_daily_reset_at date NULL,
  ADD COLUMN IF NOT EXISTS ai_monthly_cap_cents integer NULL,
  ADD COLUMN IF NOT EXISTS ai_monthly_spend_cents integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS ai_last_monthly_reset_at date NULL;

COMMIT;
```

---

## 5. Rollback Guidance (Documentation Only)

Ulysses production migrations should be treated as forward-only.

If a rollback is needed for operational reasons, the safest rollback is typically application-level (disable AI globally, do not drop columns). Dropping columns is destructive and complicates future re-application.

If you must provide a rollback script for local development only, keep it separate and clearly labeled as non-production.

---

## 6. Post-Migration Defaults and Operating Policy

### 6.1 Defaults (After Migration)

After migration:

* AI remains disabled for all users (`ai_enabled = false`)
* Even if a user enables AI later, daily limit defaults to 0 until explicitly set

This ensures:

* No accidental spend
* Explicit enablement includes both opt-in and limits

### 6.2 Recommended initial operating values

For your own account testing:

* `ai_enabled = true`
* `ai_daily_request_limit = 10`
* `ai_monthly_cap_cents = 2000` (example: $20.00)
* Set `ai_last_daily_reset_at` and `ai_last_monthly_reset_at` to today on first enablement

These values can be adjusted later without schema changes.

---

## 7. Application Changes Required to Support Migration

After columns exist, backend logic must:

* Treat missing reset dates as requiring initialization
* Reset daily counters when `ai_last_daily_reset_at` is not today
* Reset monthly spend when `ai_last_monthly_reset_at` is not in the current month
* Only increment usage on successful completion of an AI request

These behaviors belong in the centralized AI guard and usage accounting logic.

---

## 8. Deployment Checklist

### 8.1 Local

1. Apply migration to `realestatecrm_local`
2. Verify columns exist:

   * `\d+ users`
3. Verify defaults:

   * `ai_enabled` default false
   * `ai_daily_request_limit` default 0
   * `ai_monthly_spend_cents` default 0

### 8.2 Production

1. Ensure global AI flag remains disabled before migrating
2. Apply migration using production-safe process
3. Verify schema parity
4. Deploy app code that reads these fields
5. Keep AI globally disabled until end-to-end tests are complete

---

## 9. Definition of Done

This migration plan is complete when:

* The migration file exists in `docs/migrations/`
* Columns are added to `users` locally and in production
* Defaults are verified
* No existing functionality is impacted

---

## 10. Canon Statement

> *Ulysses AI is opt-in by design. Database defaults must always fail closed: no opt-in, no usage, no spend.*
