BEGIN;

-- =========================================================
-- Phase 5: Tasks (v0.11.0)
-- Authoritative spec: Ulysses_CRM_Phase_5_Design_and_Scope_v2.md
-- Local-first. Production frozen until explicit parity plan.
-- =========================================================

-- 1) Tasks table
CREATE TABLE IF NOT EXISTS tasks (
  id SERIAL PRIMARY KEY,

  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
  transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
  engagement_id INTEGER REFERENCES engagements(id) ON DELETE SET NULL,
  professional_id INTEGER REFERENCES professionals(id) ON DELETE SET NULL,

  title VARCHAR(255) NOT NULL,
  description TEXT,

  task_type VARCHAR(50),
  status VARCHAR(30) NOT NULL DEFAULT 'open',   -- open, completed, snoozed, canceled
  priority VARCHAR(20),                        -- keep as string for now (low/normal/high etc)

  due_date DATE,
  due_at TIMESTAMPTZ,

  snoozed_until TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  canceled_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Basic integrity on status values listed in the spec
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'tasks_status_check'
  ) THEN
    ALTER TABLE tasks
      ADD CONSTRAINT tasks_status_check
      CHECK (status IN ('open','completed','snoozed','canceled'));
  END IF;
END $$;

-- Useful indexes for dashboard groupings and per-contact views
CREATE INDEX IF NOT EXISTS idx_tasks_user_status_due
  ON tasks (user_id, status, due_date);

CREATE INDEX IF NOT EXISTS idx_tasks_user_due_at
  ON tasks (user_id, due_at);

CREATE INDEX IF NOT EXISTS idx_tasks_contact
  ON tasks (user_id, contact_id);

CREATE INDEX IF NOT EXISTS idx_tasks_transaction
  ON tasks (user_id, transaction_id);

CREATE INDEX IF NOT EXISTS idx_tasks_engagement
  ON tasks (user_id, engagement_id);

CREATE INDEX IF NOT EXISTS idx_tasks_professional
  ON tasks (user_id, professional_id);


-- 2) Task document links association table (spec calls this out)
CREATE TABLE IF NOT EXISTS task_document_links (
  id SERIAL PRIMARY KEY,

  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,

  url TEXT NOT NULL,
  provider VARCHAR(30) NOT NULL DEFAULT 'other',  -- google_drive, icloud, dropbox, onedrive, other
  notes TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'task_document_links_provider_check'
  ) THEN
    ALTER TABLE task_document_links
      ADD CONSTRAINT task_document_links_provider_check
      CHECK (provider IN ('google_drive','icloud','dropbox','onedrive','other'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_task_doclinks_task
  ON task_document_links (task_id);

CREATE INDEX IF NOT EXISTS idx_task_doclinks_user
  ON task_document_links (user_id);


-- 3) Engagement document links are optional for v0.11.0 (spec says optional)
-- We are not creating it in this migration.


-- =========================================================
-- Phase 5: Transaction Context (NEW)
-- =========================================================

ALTER TABLE transactions
  ADD COLUMN IF NOT EXISTS transaction_context TEXT;

ALTER TABLE transactions
  ADD COLUMN IF NOT EXISTS transaction_context_updated_at TIMESTAMPTZ;


COMMIT;
