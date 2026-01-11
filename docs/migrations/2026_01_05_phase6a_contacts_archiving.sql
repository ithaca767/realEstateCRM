-- docs/migrations/2026_01_05_phase6a_contacts_archiving.sql

ALTER TABLE contacts
  ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_user_archived
  ON contacts (user_id, archived_at);
