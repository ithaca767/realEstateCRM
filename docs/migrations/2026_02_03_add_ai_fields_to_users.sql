-- Ulysses CRM
-- Phase 8: AI Foundations
-- Add per-user AI enablement, limits, and usage counters
-- Fail-closed by default

ALTER TABLE users
ADD COLUMN IF NOT EXISTS ai_enabled BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS ai_daily_request_limit INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS ai_daily_requests_used INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS ai_last_daily_reset_at DATE,
ADD COLUMN IF NOT EXISTS ai_monthly_cap_cents INTEGER,
ADD COLUMN IF NOT EXISTS ai_monthly_spend_cents INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS ai_last_monthly_reset_at DATE;
