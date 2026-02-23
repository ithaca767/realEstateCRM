-- 2026_02_22_phase10c_email_messages_direction_check.sql
-- Phase 10C: add CHECK constraint for email_messages.direction

ALTER TABLE email_messages
ADD CONSTRAINT chk_email_messages_direction
CHECK (direction IN ('inbound', 'outbound', 'unknown'));