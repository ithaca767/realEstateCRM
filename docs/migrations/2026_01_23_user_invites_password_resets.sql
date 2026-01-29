-- Ulysses CRM
-- Phase 7B: User Onboarding and Access Control
-- Additive schema only: user_invites, password_resets
-- Date: 2026-01-23

BEGIN;

CREATE TABLE IF NOT EXISTS user_invites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  invited_email TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',

  token_hash TEXT NOT NULL,

  invited_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  used_by_user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,

  note TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,

  CONSTRAINT user_invites_role_check CHECK (role IN ('owner', 'user'))
);

-- Token hash should be unique so we can do direct lookup and avoid collisions
CREATE UNIQUE INDEX IF NOT EXISTS user_invites_token_hash_uq
  ON user_invites (token_hash);

CREATE INDEX IF NOT EXISTS user_invites_invited_email_idx
  ON user_invites (invited_email);

CREATE INDEX IF NOT EXISTS user_invites_expires_at_idx
  ON user_invites (expires_at);

-- Helpful for "show active invites" screens
CREATE INDEX IF NOT EXISTS user_invites_active_idx
  ON user_invites (created_at)
  WHERE used_at IS NULL AND revoked_at IS NULL;


CREATE TABLE IF NOT EXISTS password_resets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  token_hash TEXT NOT NULL,

  request_ip TEXT,
  request_user_agent TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS password_resets_token_hash_uq
  ON password_resets (token_hash);

CREATE INDEX IF NOT EXISTS password_resets_user_id_idx
  ON password_resets (user_id);

CREATE INDEX IF NOT EXISTS password_resets_expires_at_idx
  ON password_resets (expires_at);

COMMIT;
