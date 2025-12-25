-- Phase 1 (v0.10.0): Add canonical transactions.status without breaking production
-- Additive only: does NOT drop listing_status or offer_status

BEGIN;

-- 1) Add the new canonical status column (nullable first for safe backfill)
ALTER TABLE transactions
  ADD COLUMN IF NOT EXISTS status VARCHAR(30);

-- 2) Backfill status using a conservative mapping from existing listing_status
--    If listing_status does not exist or is NULL, default to 'draft'
--    This is intentionally minimal and safe.
UPDATE transactions
SET status =
  CASE
    WHEN status IS NOT NULL THEN status
    WHEN listing_status IS NULL THEN 'draft'
    WHEN listing_status = 'lead' THEN 'draft'
    WHEN listing_status = 'preparing' THEN 'coming_soon'
    WHEN listing_status = 'active' THEN 'active'
    WHEN listing_status = 'under_contract' THEN 'pending_uc'
    WHEN listing_status = 'sold' THEN 'closed'
    WHEN listing_status = 'withdrawn' THEN 'withdrawn'
    WHEN listing_status = 'expired' THEN 'expired'
    ELSE 'draft'
  END;

-- 3) Set default and NOT NULL for the new canonical column
ALTER TABLE transactions
  ALTER COLUMN status SET DEFAULT 'draft';

ALTER TABLE transactions
  ALTER COLUMN status SET NOT NULL;

-- 4) Add v0.10.0 canonical lifecycle constraint (snake_case)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'transactions_status_check'
  ) THEN
    ALTER TABLE transactions
      ADD CONSTRAINT transactions_status_check
      CHECK (
        status IN (
          'draft',
          'coming_soon',
          'active',
          'attorney_review',
          'pending_uc',
          'closed',
          'temp_off_market',
          'withdrawn',
          'canceled',
          'expired'
        )
      );
  END IF;
END $$;

-- 5) Index for filtering and dashboards
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);

COMMIT;
