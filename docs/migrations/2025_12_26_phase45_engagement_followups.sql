cat > docs/migrations/2025_12_26_phase45_engagement_followups.sql <<'SQL'
BEGIN;

ALTER TABLE engagements
  ADD COLUMN IF NOT EXISTS requires_follow_up BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE engagements
  ADD COLUMN IF NOT EXISTS follow_up_due_at TIMESTAMPTZ;

ALTER TABLE engagements
  ADD COLUMN IF NOT EXISTS follow_up_completed BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE engagements
  ADD COLUMN IF NOT EXISTS follow_up_completed_at TIMESTAMP WITHOUT TIME ZONE;

CREATE INDEX IF NOT EXISTS idx_engagements_followup_due
  ON engagements (user_id, follow_up_due_at)
  WHERE requires_follow_up = TRUE
    AND follow_up_completed = FALSE
    AND follow_up_due_at IS NOT NULL;

COMMIT;
SQL
