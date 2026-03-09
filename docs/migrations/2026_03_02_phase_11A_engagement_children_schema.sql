BEGIN;

-- 1) Add parent pointer
ALTER TABLE engagements
ADD COLUMN parent_engagement_id integer;

-- 2) Prevent self-parenting
ALTER TABLE engagements
ADD CONSTRAINT engagements_parent_not_self
CHECK (parent_engagement_id IS NULL OR parent_engagement_id <> id);

-- 3) Self-referential FK
-- CASCADE is strongly preferred so "delete parent engagement" removes followup children.
ALTER TABLE engagements
ADD CONSTRAINT engagements_parent_engagement_id_fkey
FOREIGN KEY (parent_engagement_id)
REFERENCES engagements(id)
ON DELETE CASCADE;

-- 4) Index to load children fast (and tenant-safely)
CREATE INDEX idx_engagements_user_parent_occurred
ON engagements (user_id, parent_engagement_id, occurred_at DESC)
WHERE parent_engagement_id IS NOT NULL;

-- 5) Index for child-followups due list (this becomes the replacement for idx_engagements_followup_due later)
CREATE INDEX idx_engagements_child_followup_due_open
ON engagements (user_id, follow_up_due_at)
WHERE parent_engagement_id IS NOT NULL
  AND requires_follow_up = true
  AND follow_up_completed = false
  AND follow_up_due_at IS NOT NULL;
  
COMMIT;