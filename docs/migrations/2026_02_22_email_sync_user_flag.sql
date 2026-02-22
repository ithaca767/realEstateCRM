-- 2026_02_22_email_sync_user_flag.sql
-- Adds a per-user feature flag for the Emails tab and email sync features.

ALTER TABLE users
ADD COLUMN IF NOT EXISTS email_sync_enabled boolean NOT NULL DEFAULT false;

-- Optional: helpful comment for future maintainers
COMMENT ON COLUMN users.email_sync_enabled IS
'If true, user can access Email Sync features and Emails tab UI.';