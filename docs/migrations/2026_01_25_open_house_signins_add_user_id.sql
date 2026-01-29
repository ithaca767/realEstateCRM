BEGIN;

ALTER TABLE open_house_signins
ADD COLUMN IF NOT EXISTS user_id integer;

-- Backfill from parent open_houses owner
UPDATE open_house_signins s
SET user_id = oh.created_by_user_id
FROM open_houses oh
WHERE s.open_house_id = oh.id
  AND s.user_id IS NULL;

ALTER TABLE open_house_signins
ALTER COLUMN user_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_open_house_signins_user_id
ON open_house_signins(user_id);

CREATE INDEX IF NOT EXISTS idx_open_house_signins_open_house_user
ON open_house_signins(open_house_id, user_id);

COMMIT;
