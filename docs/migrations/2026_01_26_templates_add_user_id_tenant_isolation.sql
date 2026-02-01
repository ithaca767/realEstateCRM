-- Tenant isolation: Templates
-- Local-first migration

ALTER TABLE templates
  ADD COLUMN IF NOT EXISTS user_id integer;

UPDATE templates
SET user_id = 1
WHERE user_id IS NULL;

ALTER TABLE templates
  ALTER COLUMN user_id SET NOT NULL;

-- NOTE: Postgres does not support ADD CONSTRAINT IF NOT EXISTS.
-- Constraint added via 2026_01_28_prod_fix_templates_fk.sql using a DO block.

CREATE INDEX IF NOT EXISTS idx_templates_user_updated_at
  ON templates (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_templates_user_category
  ON templates (user_id, category);

CREATE INDEX IF NOT EXISTS idx_templates_user_archived_at
  ON templates (user_id, archived_at);
