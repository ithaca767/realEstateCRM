BEGIN;

-- =========================================
-- Phase 5 (v0.11.0) Production Schema Parity
-- Additive only. No data changes.
-- =========================================

-- 1) transactions: add transaction context fields
ALTER TABLE public.transactions
  ADD COLUMN IF NOT EXISTS transaction_context text;

ALTER TABLE public.transactions
  ADD COLUMN IF NOT EXISTS transaction_context_updated_at timestamp with time zone;


-- 2) tasks table + sequence + defaults + primary key

CREATE TABLE IF NOT EXISTS public.tasks (
  id integer NOT NULL,
  user_id integer NOT NULL,
  contact_id integer,
  transaction_id integer,
  engagement_id integer,
  professional_id integer,
  title character varying(255) NOT NULL,
  description text,
  task_type character varying(50),
  status character varying(30) DEFAULT 'open'::character varying NOT NULL,
  priority character varying(20),
  due_date date,
  due_at timestamp with time zone,
  snoozed_until timestamp with time zone,
  completed_at timestamp with time zone,
  canceled_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  CONSTRAINT tasks_status_check CHECK (
    (status)::text = ANY (
      (ARRAY[
        'open'::character varying,
        'completed'::character varying,
        'snoozed'::character varying,
        'canceled'::character varying
      ])::text[]
    )
  )
);

CREATE SEQUENCE IF NOT EXISTS public.tasks_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;

ALTER SEQUENCE public.tasks_id_seq OWNED BY public.tasks.id;

ALTER TABLE public.tasks
  ALTER COLUMN id SET DEFAULT nextval('public.tasks_id_seq'::regclass);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'tasks_pkey'
      AND conrelid = 'public.tasks'::regclass
  ) THEN
    ALTER TABLE ONLY public.tasks
      ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);
  END IF;
END $$;


-- 3) task_document_links table + sequence + defaults + primary key

CREATE TABLE IF NOT EXISTS public.task_document_links (
  id integer NOT NULL,
  user_id integer NOT NULL,
  task_id integer NOT NULL,
  url text NOT NULL,
  provider character varying(30) DEFAULT 'other'::character varying NOT NULL,
  notes text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  CONSTRAINT task_document_links_provider_check CHECK (
    (provider)::text = ANY (
      (ARRAY[
        'google_drive'::character varying,
        'icloud'::character varying,
        'dropbox'::character varying,
        'onedrive'::character varying,
        'other'::character varying
      ])::text[]
    )
  )
);

CREATE SEQUENCE IF NOT EXISTS public.task_document_links_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;

ALTER SEQUENCE public.task_document_links_id_seq OWNED BY public.task_document_links.id;

ALTER TABLE public.task_document_links
  ALTER COLUMN id SET DEFAULT nextval('public.task_document_links_id_seq'::regclass);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'task_document_links_pkey'
      AND conrelid = 'public.task_document_links'::regclass
  ) THEN
    ALTER TABLE ONLY public.task_document_links
      ADD CONSTRAINT task_document_links_pkey PRIMARY KEY (id);
  END IF;
END $$;


-- 4) Indexes

CREATE INDEX IF NOT EXISTS idx_task_doclinks_task
  ON public.task_document_links (task_id);

CREATE INDEX IF NOT EXISTS idx_task_doclinks_user
  ON public.task_document_links (user_id);

CREATE INDEX IF NOT EXISTS idx_tasks_contact
  ON public.tasks (user_id, contact_id);

CREATE INDEX IF NOT EXISTS idx_tasks_engagement
  ON public.tasks (user_id, engagement_id);

CREATE INDEX IF NOT EXISTS idx_tasks_professional
  ON public.tasks (user_id, professional_id);

CREATE INDEX IF NOT EXISTS idx_tasks_transaction
  ON public.tasks (user_id, transaction_id);

CREATE INDEX IF NOT EXISTS idx_tasks_user_due_at
  ON public.tasks (user_id, due_at);

CREATE INDEX IF NOT EXISTS idx_tasks_user_status_due
  ON public.tasks (user_id, status, due_date);

CREATE INDEX IF NOT EXISTS idx_transaction_deadlines_transaction_id
  ON public.transaction_deadlines (transaction_id);

CREATE INDEX IF NOT EXISTS idx_transaction_deadlines_user_due
  ON public.transaction_deadlines (user_id, due_date);


-- 5) Foreign keys (added conditionally)

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='task_document_links_task_id_fkey') THEN
    ALTER TABLE ONLY public.task_document_links
      ADD CONSTRAINT task_document_links_task_id_fkey
      FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='task_document_links_user_id_fkey') THEN
    ALTER TABLE ONLY public.task_document_links
      ADD CONSTRAINT task_document_links_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='tasks_contact_id_fkey') THEN
    ALTER TABLE ONLY public.tasks
      ADD CONSTRAINT tasks_contact_id_fkey
      FOREIGN KEY (contact_id) REFERENCES public.contacts(id) ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='tasks_engagement_id_fkey') THEN
    ALTER TABLE ONLY public.tasks
      ADD CONSTRAINT tasks_engagement_id_fkey
      FOREIGN KEY (engagement_id) REFERENCES public.engagements(id) ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='tasks_professional_id_fkey') THEN
    ALTER TABLE ONLY public.tasks
      ADD CONSTRAINT tasks_professional_id_fkey
      FOREIGN KEY (professional_id) REFERENCES public.professionals(id) ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='tasks_transaction_id_fkey') THEN
    ALTER TABLE ONLY public.tasks
      ADD CONSTRAINT tasks_transaction_id_fkey
      FOREIGN KEY (transaction_id) REFERENCES public.transactions(id) ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='tasks_user_id_fkey') THEN
    ALTER TABLE ONLY public.tasks
      ADD CONSTRAINT tasks_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
  END IF;
END $$;

COMMIT;

