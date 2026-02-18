-- Phase 9 Premium Flag: AI Answer Mode gating
-- Local-first; production-safe.

ALTER TABLE users
ADD COLUMN IF NOT EXISTS ai_premium_enabled BOOLEAN NOT NULL DEFAULT FALSE;
