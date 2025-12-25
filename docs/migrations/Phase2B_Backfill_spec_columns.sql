-- Phase 2B: Backfill v0.10.0 spec columns (non-breaking, idempotent)
-- Backfills:
--   - primary_contact_id from contact_id
--   - address from address_line/city/state/postal_code
--   - status_changed_at from created_at (only if null)
-- Does NOT:
--   - modify Phase 1 columns or constraints
--   - change transaction_type semantics
--   - drop or tighten anything

BEGIN;

-- 1) Backfill primary_contact_id from existing required contact_id
UPDATE transactions
SET primary_contact_id = contact_id
WHERE primary_contact_id IS NULL;

-- 2) Backfill address as a single text field from component fields (when address is currently null/blank)
--    Format example: "123 Main St, Keyport, NJ 07735"
UPDATE transactions
SET address = NULLIF(
    CONCAT_WS(', ',
      NULLIF(TRIM(address_line), ''),
      NULLIF(TRIM(city), ''),
      NULLIF(
        TRIM(
          CONCAT_WS(' ',
            NULLIF(TRIM(state), ''),
            NULLIF(TRIM(postal_code), '')
          )
        ),
        ''
      )
    ),
    ''
)
WHERE (address IS NULL OR TRIM(address) = '');

-- 3) Seed status_changed_at for existing rows (only if null)
--    This provides a sensible baseline for historical records without changing current behavior.
UPDATE transactions
SET status_changed_at = created_at
WHERE status_changed_at IS NULL;

COMMIT;
