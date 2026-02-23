-- 2026_02_22_phase10c_email_messages_direction_check.sql
-- Phase 10C: add CHECK constraint for email_messages.direction (idempotent)

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'chk_email_messages_direction'
  ) THEN
    ALTER TABLE email_messages
    ADD CONSTRAINT chk_email_messages_direction
    CHECK (direction IN ('inbound', 'outbound', 'unknown'));
  END IF;
END $$;