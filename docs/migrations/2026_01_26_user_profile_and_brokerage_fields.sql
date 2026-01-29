-- 2026_01_26_user_profile_and_brokerage_fields.sql

BEGIN;

-- 1) Extend users with agent profile fields
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS phone TEXT,
  ADD COLUMN IF NOT EXISTS title TEXT,
  ADD COLUMN IF NOT EXISTS license_number TEXT,
  ADD COLUMN IF NOT EXISTS agent_website TEXT;

-- 2) Create brokerages table (1 per user)
CREATE TABLE IF NOT EXISTS brokerages (
  user_id INTEGER PRIMARY KEY
    REFERENCES users(id) ON DELETE CASCADE,

  brokerage_name TEXT,
  address1 TEXT,
  address2 TEXT,
  city TEXT,
  state TEXT,
  zip TEXT,
  brokerage_phone TEXT,
  brokerage_website TEXT,
  office_license_number TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_brokerages_name ON brokerages (brokerage_name);

COMMIT;
