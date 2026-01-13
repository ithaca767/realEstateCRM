BEGIN;

-- 1) Backfill listing_status to new normalized set
UPDATE transactions
SET listing_status = CASE listing_status
  WHEN 'lead' THEN 'draft'
  WHEN 'preparing' THEN 'coming_soon'
  WHEN 'active' THEN 'active'
  WHEN 'under_contract' THEN 'under_contract'
  WHEN 'sold' THEN 'closed'
  WHEN 'withdrawn' THEN 'withdrawn'
  WHEN 'expired' THEN 'expired'
  ELSE listing_status
END;

-- 2) Backfill offer_status to new normalized set
UPDATE transactions
SET offer_status = CASE offer_status
  WHEN 'none' THEN 'draft'
  WHEN 'drafting' THEN 'draft'
  WHEN 'submitted' THEN 'submitted'
  WHEN 'countered' THEN 'countered'
  WHEN 'accepted' THEN 'accepted'
  WHEN 'rejected' THEN 'rejected'
  WHEN 'withdrawn' THEN 'withdrawn'
  ELSE offer_status
END;

-- 3) Set new defaults
ALTER TABLE transactions
  ALTER COLUMN listing_status SET DEFAULT 'draft';

ALTER TABLE transactions
  ALTER COLUMN offer_status SET DEFAULT 'draft';

-- 4) Replace CHECK constraints with the new allowed sets
ALTER TABLE transactions
  DROP CONSTRAINT IF EXISTS transactions_listing_status_check;

ALTER TABLE transactions
  ADD CONSTRAINT transactions_listing_status_check
  CHECK (listing_status::text = ANY (ARRAY[
    'draft',
    'coming_soon',
    'active',
    'under_contract',
    'back_on_market',
    'withdrawn',
    'expired',
    'closed'
  ]::text[]));

ALTER TABLE transactions
  DROP CONSTRAINT IF EXISTS transactions_offer_status_check;

ALTER TABLE transactions
  ADD CONSTRAINT transactions_offer_status_check
  CHECK (offer_status::text = ANY (ARRAY[
    'draft',
    'submitted',
    'countered',
    'accepted',
    'rejected',
    'withdrawn',
    'under_contract',
    'closed'
  ]::text[]));

COMMIT;
