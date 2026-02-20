-- REGRESSION FIXTURE
-- Purpose: prevent cross-contact AI Answer leakage
-- Created: 2026-02-20
-- Linked to: Phase 9 AI Search hardening
-- Do not run in production.


BEGIN;

-- Delete child rows first
DELETE FROM engagements
WHERE user_id = 1
  AND (
    COALESCE(summary_clean, '') ILIKE '%[AI-LEAK-TEST-2026-02-20]%'
    OR COALESCE(notes, '') ILIKE '%[AI-LEAK-TEST-2026-02-20]%'
  );

DELETE FROM transactions
WHERE user_id = 1
  AND COALESCE(address, '') ILIKE '%[AI-LEAK-TEST-2026-02-20]%';

-- Delete fixture contacts
DELETE FROM contacts
WHERE user_id = 1
  AND (
    email IN ('tracy.ai.leak.test@example.com', 'jessica.ai.leak.test@example.com')
    OR COALESCE(notes, '') ILIKE '%[AI-LEAK-TEST-2026-02-20]%'
  );

COMMIT;