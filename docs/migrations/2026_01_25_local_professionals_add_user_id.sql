BEGIN;

ALTER TABLE professionals
ADD COLUMN IF NOT EXISTS user_id integer;

UPDATE professionals
SET user_id = 1
WHERE user_id IS NULL;

ALTER TABLE professionals
ALTER COLUMN user_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_professionals_user_id
ON professionals(user_id);

COMMIT;
