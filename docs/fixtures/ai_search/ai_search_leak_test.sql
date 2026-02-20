-- REGRESSION FIXTURE
-- Purpose: inject two contacts and distinct engagements to detect AI cross-contact leakage
-- Created: 2026-02-20
-- Do not run in production.
-- Tag: [AI-LEAK-TEST-2026-02-20]

BEGIN;

-- Tracy fixture contact
WITH ins AS (
  INSERT INTO contacts (user_id, name, email, phone, notes)
  VALUES (
    1,
    'Tracy Strumolo (AI Leak Test)',
    'tracy.ai.leak.test@example.com',
    '555-000-0004',
    '[AI-LEAK-TEST-2026-02-20] Tracy fixture contact for AI leak tests.'
  )
  RETURNING id
)
SELECT id AS tracy_contact_id FROM ins;

-- Jessica fixture contact
WITH ins AS (
  INSERT INTO contacts (user_id, name, email, phone, notes)
  VALUES (
    1,
    'Jessica Johnson (AI Leak Test)',
    'jessica.ai.leak.test@example.com',
    '555-000-0008',
    '[AI-LEAK-TEST-2026-02-20] Jessica fixture contact for AI leak tests.'
  )
  RETURNING id
)
SELECT id AS jessica_contact_id FROM ins;

-- Tracy engagement with unmistakable offer language
WITH tracy AS (
  SELECT id FROM contacts
  WHERE user_id = 1 AND email = 'tracy.ai.leak.test@example.com'
  ORDER BY id DESC
  LIMIT 1
)
INSERT INTO engagements (user_id, contact_id, occurred_at, engagement_type, summary_clean, notes)
SELECT
  1,
  tracy.id,
  NOW(),
  'call',
  'OFFER $101,000 from Antoinette ("Annie"). Initial deposit $5,000 NOT received. [AI-LEAK-TEST-2026-02-20]',
  'Tracy test engagement: buyer selling own home, expected close mid-March, proposed close April 1. [AI-LEAK-TEST-2026-02-20]'
FROM tracy;

-- Jessica engagement with unmistakable estate language
WITH jess AS (
  SELECT id FROM contacts
  WHERE user_id = 1 AND email = 'jessica.ai.leak.test@example.com'
  ORDER BY id DESC
  LIMIT 1
)
INSERT INTO engagements (user_id, contact_id, occurred_at, engagement_type, summary_clean, notes)
SELECT
  1,
  jess.id,
  NOW(),
  'email',
  'Executrix of estate, property 41 Atlantic Street. Mortgage rate dispute 2% vs 8%. [AI-LEAK-TEST-2026-02-20]',
  'Jessica test engagement: estate coordination and property maintenance follow-ups. [AI-LEAK-TEST-2026-02-20]'
FROM jess;

COMMIT;
