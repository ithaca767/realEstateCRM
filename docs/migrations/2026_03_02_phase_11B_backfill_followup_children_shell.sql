BEGIN;

WITH candidates AS (
  SELECT p.*
  FROM engagements p
  WHERE p.parent_engagement_id IS NULL
    AND p.requires_follow_up = TRUE
    AND p.follow_up_due_at IS NOT NULL
    AND NOT EXISTS (
      SELECT 1
      FROM engagements c
      WHERE c.parent_engagement_id = p.id
        AND c.follow_up_due_at = p.follow_up_due_at
        AND c.user_id = p.user_id
    )
),
inserted AS (
  INSERT INTO engagements (
    user_id,
    contact_id,
    parent_engagement_id,
    engagement_type,
    occurred_at,
    outcome,
    notes,
    transcript_raw,
    summary_clean,
    created_at,
    updated_at,
    requires_follow_up,
    follow_up_due_at,
    follow_up_completed,
    follow_up_completed_at
  )
  SELECT
    user_id,
    contact_id,
    id AS parent_engagement_id,
    engagement_type,
    occurred_at,                  -- keep close to the parent’s time
    NULL,                         -- shell: empty content
    NULL,
    NULL,
    NULL,
    now(),
    now(),
    TRUE,
    follow_up_due_at,
    follow_up_completed,
    follow_up_completed_at
  FROM candidates
  RETURNING parent_engagement_id
)
UPDATE engagements p
SET
  requires_follow_up = FALSE,
  follow_up_due_at = NULL,
  follow_up_completed = FALSE,
  follow_up_completed_at = NULL,
  updated_at = now()
WHERE p.id IN (SELECT parent_engagement_id FROM inserted);

COMMIT;