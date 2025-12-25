-- Phase 2A: Add v0.10.0 spec columns to transactions (additive only)
-- Safe to run in production because it only adds nullable columns and optional indexes.
-- No data backfills. No NOT NULL changes. No drops.

BEGIN;

ALTER TABLE transactions
  -- Core details (spec)
  ADD COLUMN IF NOT EXISTS address TEXT,

  -- Relationships (spec)
  ADD COLUMN IF NOT EXISTS primary_contact_id INTEGER,
  ADD COLUMN IF NOT EXISTS secondary_contact_id INTEGER,

  -- Pricing (spec)
  ADD COLUMN IF NOT EXISTS list_price NUMERIC(12,2),
  ADD COLUMN IF NOT EXISTS offer_price NUMERIC(12,2),
  ADD COLUMN IF NOT EXISTS accepted_price NUMERIC(12,2),
  ADD COLUMN IF NOT EXISTS closed_price NUMERIC(12,2),

  -- Core milestone dates (spec)
  ADD COLUMN IF NOT EXISTS list_date DATE,
  ADD COLUMN IF NOT EXISTS attorney_review_end_date DATE,
  ADD COLUMN IF NOT EXISTS inspection_deadline DATE,
  ADD COLUMN IF NOT EXISTS financing_contingency_date DATE,
  ADD COLUMN IF NOT EXISTS appraisal_deadline DATE,
  ADD COLUMN IF NOT EXISTS mortgage_commitment_date DATE,

  -- Closing dates (spec)
  ADD COLUMN IF NOT EXISTS expected_close_date DATE,
  ADD COLUMN IF NOT EXISTS actual_close_date DATE,

  -- Audit (spec)
  ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMP;

-- Add foreign keys for the new relationship columns (nullable, so non-breaking)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'transactions_primary_contact_id_fkey'
  ) THEN
    ALTER TABLE transactions
      ADD CONSTRAINT transactions_primary_contact_id_fkey
      FOREIGN KEY (primary_contact_id)
      REFERENCES contacts(id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'transactions_secondary_contact_id_fkey'
  ) THEN
    ALTER TABLE transactions
      ADD CONSTRAINT transactions_secondary_contact_id_fkey
      FOREIGN KEY (secondary_contact_id)
      REFERENCES contacts(id)
      ON DELETE SET NULL;
  END IF;
END $$;

-- Helpful indexes for Phase 2 and beyond (safe, non-breaking)
CREATE INDEX IF NOT EXISTS idx_transactions_primary_contact_id
  ON transactions(primary_contact_id);

CREATE INDEX IF NOT EXISTS idx_transactions_secondary_contact_id
  ON transactions(secondary_contact_id);

COMMIT;
