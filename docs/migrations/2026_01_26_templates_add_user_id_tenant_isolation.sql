-- Tenant isolation: Templates
-- Local-first migration

ALTER TABLE templates
  ADD COLUMN IF NOT EXISTS user_id integer;

-- Backfill existing rows to the current owner user if you have a known owner id.
-- If you have multiple users already, pause here and decide the mapping.
-- For local dev with a single owner user, this is safe.

-- Example: set everything to user_id = 1 (adjust if needed)
UPDATE templates
SET user_id = 1
WHERE user_id IS NULL;

ALTER TABLE templates
  ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE templates
  ADD CONSTRAINT IF NOT EXISTS templates_user_id_fkey
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_templates_user_updated_at
  ON templates (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_templates_user_category
  ON templates (user_id, category);

CREATE INDEX IF NOT EXISTS idx_templates_user_archived_at
  ON templates (user_id, archived_at);
