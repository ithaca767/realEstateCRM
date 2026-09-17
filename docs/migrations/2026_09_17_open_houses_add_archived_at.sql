BEGIN;

ALTER TABLE open_houses
ADD COLUMN IF NOT EXISTS archived_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_open_houses_user_active
ON open_houses(created_by_user_id, start_datetime DESC)
WHERE archived_at IS NULL;

COMMIT;
