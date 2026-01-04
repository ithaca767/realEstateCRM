BEGIN;

-- Rename columns to production-safe, consistent names
ALTER TABLE transaction_deadlines
  RENAME COLUMN label TO name;

ALTER TABLE transaction_deadlines
  RENAME COLUMN due_at TO due_date;

COMMIT;

