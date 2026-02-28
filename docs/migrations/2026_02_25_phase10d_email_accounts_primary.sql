-- Phase 10D: Outlook support groundwork
-- Add a "primary email account" per user (provider-agnostic)

ALTER TABLE email_accounts
ADD COLUMN IF NOT EXISTS is_primary boolean NOT NULL DEFAULT false;

-- Ensure only one primary per user
CREATE UNIQUE INDEX IF NOT EXISTS ux_email_accounts_user_primary
ON email_accounts (user_id)
WHERE is_primary = true;

-- Optional: backfill existing rows, pick the newest as primary when none exists
WITH ranked AS (
  SELECT id, user_id,
         ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC, id DESC) AS rn
  FROM email_accounts
)
UPDATE email_accounts ea
SET is_primary = true
FROM ranked r
WHERE ea.id = r.id
  AND r.rn = 1
  AND NOT EXISTS (
    SELECT 1 FROM email_accounts ea2
    WHERE ea2.user_id = ea.user_id AND ea2.is_primary = true
  );