BEGIN;

-- 1) Add column (nullable first for backfill)
ALTER TABLE interactions
  ADD COLUMN IF NOT EXISTS user_id INTEGER;

-- 2) Backfill user_id from owning contact
UPDATE interactions i
SET user_id = c.user_id
FROM contacts c
WHERE i.contact_id = c.id
  AND i.user_id IS NULL;

-- 3) Enforce NOT NULL (only after backfill)
ALTER TABLE interactions
  ALTER COLUMN user_id SET NOT NULL;

-- 4) Add FK (matches PROD intent)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE constraint_name = 'interactions_user_id_fkey'
      AND table_name = 'interactions'
  ) THEN
    ALTER TABLE interactions
      ADD CONSTRAINT interactions_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
  END IF;
END $$;

-- 5) Add index (matches PROD intent)
CREATE INDEX IF NOT EXISTS idx_interactions_user_happened
  ON interactions (user_id, happened_at DESC);

COMMIT;
