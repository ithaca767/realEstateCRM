-- 2026_09_20_users_add_timezone_name.sql
--
-- Account-level IANA timezone preference.
-- IMPORTANT: adding this preference does not change runtime timezone behavior.
-- Existing runtime behavior remains America/New_York until a later,
-- separately tested migration changes get_user_tz().

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS timezone_name TEXT;

UPDATE users
SET timezone_name = 'America/New_York'
WHERE timezone_name IS NULL
   OR BTRIM(timezone_name) = '';

ALTER TABLE users
    ALTER COLUMN timezone_name SET DEFAULT 'America/New_York',
    ALTER COLUMN timezone_name SET NOT NULL;

COMMIT;
