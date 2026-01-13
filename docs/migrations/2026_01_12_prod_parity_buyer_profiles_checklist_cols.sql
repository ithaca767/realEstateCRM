BEGIN;

ALTER TABLE buyer_profiles
  ADD COLUMN IF NOT EXISTS preapproval_letter_received boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS proof_of_funds_received boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS photo_id_received boolean DEFAULT false;

-- Backfill any existing rows that might have NULLs
UPDATE buyer_profiles
SET
  preapproval_letter_received = COALESCE(preapproval_letter_received, false),
  proof_of_funds_received     = COALESCE(proof_of_funds_received, false),
  photo_id_received           = COALESCE(photo_id_received, false);

-- Optional hardening if you want these guaranteed non-null going forward:
-- ALTER TABLE buyer_profiles
--   ALTER COLUMN preapproval_letter_received SET NOT NULL,
--   ALTER COLUMN proof_of_funds_received     SET NOT NULL,
--   ALTER COLUMN photo_id_received           SET NOT NULL;

COMMIT;
