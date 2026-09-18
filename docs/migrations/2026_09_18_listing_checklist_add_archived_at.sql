BEGIN;

ALTER TABLE listing_checklist_items
ADD COLUMN IF NOT EXISTS archived_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_listing_checklist_contact_active
ON listing_checklist_items(contact_id)
WHERE archived_at IS NULL;

COMMIT;
