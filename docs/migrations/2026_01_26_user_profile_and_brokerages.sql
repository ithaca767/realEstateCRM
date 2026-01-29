-- 2026_01_26_user_profile_and_brokerages.sql
-- User profile + brokerage info (v1.0.x safe)

BEGIN;

-- -------------------------------------------------------------------
-- 1) Brokerages table (1:1 with users, keyed by user_id)
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS brokerages (
  user_id INTEGER PRIMARY KEY
    REFERENCES users(id) ON DELETE CASCADE,

  brokerage_name        TEXT,
  address1              TEXT,
  address2              TEXT,
  city                  TEXT,
  state                 TEXT,
  zip                   TEXT,
  brokerage_phone       TEXT,
  brokerage_website     TEXT,
  office_license_number TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Helpful index (non-unique, safe)
CREATE INDEX IF NOT EXISTS idx_brokerages_name
  ON brokerages (brokerage_name);

-- -------------------------------------------------------------------
-- 2) Extend users with agent-level profile fields
-- -------------------------------------------------------------------
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS agent_phone   TEXT,
  ADD COLUMN IF NOT EXISTS agent_website TEXT;

COMMIT;
