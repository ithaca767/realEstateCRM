-- 2026_02_22_phase10b_contact_emails.sql
-- Phase 10B: Additional emails per contact for improved email matching.

CREATE TABLE IF NOT EXISTS contact_emails (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,

  email TEXT NOT NULL,
  label TEXT, -- e.g., 'work', 'personal', 'spouse', 'other'
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Normalize: store emails lowercased to simplify matching and uniqueness.
-- (We enforce uniqueness on lower(email) via index.)
CREATE UNIQUE INDEX IF NOT EXISTS ux_contact_emails_user_email_lower
  ON contact_emails (user_id, lower(email));

CREATE UNIQUE INDEX IF NOT EXISTS ux_contact_emails_user_contact_email_lower
  ON contact_emails (user_id, contact_id, lower(email));

CREATE INDEX IF NOT EXISTS ix_contact_emails_user_contact
  ON contact_emails (user_id, contact_id);

-- Optional: partial index for quick lookups of primary entries
CREATE INDEX IF NOT EXISTS ix_contact_emails_user_contact_primary
  ON contact_emails (user_id, contact_id)
  WHERE is_primary = TRUE;

-- Optional (recommended): trigger-less updated_at pattern can be handled in app code.
COMMENT ON TABLE contact_emails IS 'Phase 10B: Additional emails per contact (tenant-scoped).';
COMMENT ON COLUMN contact_emails.email IS 'Stored as entered; uniqueness enforced on lower(email).';