-- Phase 2B2: Backfill transactions.address from contacts (non-breaking, idempotent)
-- Rule:
--   1) Prefer subject_* address fields if present
--   2) Else use current_* address fields if present
--   3) Else leave as null/blank
-- Only updates transactions where address is null or blank.

BEGIN;

UPDATE transactions t
SET address = caddr.built_address
FROM (
  SELECT
    c.id AS contact_id,

    -- Build address with preference: subject_* first, else current_*
    COALESCE(
      NULLIF(
        CONCAT_WS(', ',
          NULLIF(BTRIM(c.subject_address), ''),
          NULLIF(BTRIM(c.subject_city), ''),
          NULLIF(
            BTRIM(
              CONCAT_WS(' ',
                NULLIF(BTRIM(c.subject_state), ''),
                NULLIF(BTRIM(c.subject_zip), '')
              )
            ),
            ''
          )
        ),
        ''
      ),
      NULLIF(
        CONCAT_WS(', ',
          NULLIF(BTRIM(c.current_address), ''),
          NULLIF(BTRIM(c.current_city), ''),
          NULLIF(
            BTRIM(
              CONCAT_WS(' ',
                NULLIF(BTRIM(c.current_state), ''),
                NULLIF(BTRIM(c.current_zip), '')
              )
            ),
            ''
          )
        ),
        ''
      )
    ) AS built_address
  FROM contacts c
) AS caddr
WHERE t.contact_id = caddr.contact_id
  AND (t.address IS NULL OR BTRIM(t.address) = '')
  AND caddr.built_address IS NOT NULL;

COMMIT;
