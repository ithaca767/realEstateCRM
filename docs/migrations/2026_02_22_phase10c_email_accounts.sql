-- 2026_02_22_phase10c_email_accounts.sql
-- Phase 10C: Gmail OAuth account storage (tokens stored encrypted at rest by app).

CREATE TABLE IF NOT EXISTS email_accounts (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  provider TEXT NOT NULL, -- 'gmail'
  primary_email TEXT NOT NULL,
  provider_account_id TEXT, -- optional, can store "me" profile id later

  access_token_enc TEXT,
  refresh_token_enc TEXT,
  token_expires_at TIMESTAMPTZ,

  sync_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  last_sync_at TIMESTAMPTZ,
  sync_cursor TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_email_accounts_user_provider_email
  ON email_accounts (user_id, provider, lower(primary_email));

CREATE INDEX IF NOT EXISTS ix_email_accounts_user_provider
  ON email_accounts (user_id, provider);