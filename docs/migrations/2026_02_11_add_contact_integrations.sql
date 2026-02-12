-- docs/migrations/2026_02_11_add_contact_integrations.sql
--
-- Phase 8B/8C: ActivePipe Bridge
-- Add per-contact integration profiles without bloating core contacts.
--
-- Canon notes:
-- - Additive-only schema
-- - Multi-tenant safe (user_id present and indexed)
-- - No destructive changes

BEGIN;

CREATE TABLE IF NOT EXISTS contact_integrations (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  contact_id BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  integration_key TEXT NOT NULL,
  external_id TEXT NULL,
  payload_json JSONB NULL,
  last_exported_at TIMESTAMP NULL,
  last_imported_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Prevent duplicate integration profiles per contact per tenant
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'uq_contact_integrations_user_contact_key'
  ) THEN
    ALTER TABLE contact_integrations
      ADD CONSTRAINT uq_contact_integrations_user_contact_key
      UNIQUE (user_id, contact_id, integration_key);
  END IF;
END $$;

-- Helpful indexes (tenant safe access patterns)
CREATE INDEX IF NOT EXISTS idx_contact_integrations_user_contact
  ON contact_integrations (user_id, contact_id);

CREATE INDEX IF NOT EXISTS idx_contact_integrations_user_key
  ON contact_integrations (user_id, integration_key);

CREATE INDEX IF NOT EXISTS idx_contact_integrations_user_key_external
  ON contact_integrations (user_id, integration_key, external_id);

COMMIT;
