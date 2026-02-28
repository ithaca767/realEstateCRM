BEGIN;

ALTER TABLE email_accounts
ADD COLUMN IF NOT EXISTS last_sync_at timestamptz;

ALTER TABLE email_accounts
ADD COLUMN IF NOT EXISTS last_sync_stats jsonb;

COMMIT;