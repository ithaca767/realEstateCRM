BEGIN;

-- 0) Rename production "status" (which is actually US state) -> "state"
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='transactions' AND column_name='status'
  )
  AND NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='transactions' AND column_name='state'
  )
  THEN
    EXECUTE 'ALTER TABLE public.transactions RENAME COLUMN status TO state';
  END IF;
END $$;

-- 1) Add true lifecycle status column expected by v0.10.0 code
ALTER TABLE public.transactions
  ADD COLUMN IF NOT EXISTS status character varying(30);

UPDATE public.transactions
SET status = COALESCE(status, 'draft')
WHERE status IS NULL;

ALTER TABLE public.transactions
  ALTER COLUMN status SET DEFAULT 'draft';

ALTER TABLE public.transactions
  ALTER COLUMN status SET NOT NULL;

-- 2) Add columns expected by templates and queries
ALTER TABLE public.transactions
  ADD COLUMN IF NOT EXISTS address text,
  ADD COLUMN IF NOT EXISTS primary_contact_id integer,
  ADD COLUMN IF NOT EXISTS secondary_contact_id integer,
  ADD COLUMN IF NOT EXISTS list_price numeric(12,2),
  ADD COLUMN IF NOT EXISTS offer_price numeric(12,2),
  ADD COLUMN IF NOT EXISTS accepted_price numeric(12,2),
  ADD COLUMN IF NOT EXISTS closed_price numeric(12,2),
  ADD COLUMN IF NOT EXISTS list_date date,
  ADD COLUMN IF NOT EXISTS attorney_review_end_date date,
  ADD COLUMN IF NOT EXISTS inspection_deadline date,
  ADD COLUMN IF NOT EXISTS financing_contingency_date date,
  ADD COLUMN IF NOT EXISTS appraisal_deadline date,
  ADD COLUMN IF NOT EXISTS mortgage_commitment_date date,
  ADD COLUMN IF NOT EXISTS expected_close_date date,
  ADD COLUMN IF NOT EXISTS actual_close_date date,
  ADD COLUMN IF NOT EXISTS status_changed_at timestamp without time zone;

-- 3) Backfill address from existing address parts if address is empty
UPDATE public.transactions
SET address = NULLIF(
  trim(
    COALESCE(address_line, '') ||
    CASE WHEN COALESCE(city,'') <> '' THEN ', ' || city ELSE '' END ||
    CASE WHEN COALESCE(state,'') <> '' THEN ', ' || state ELSE '' END ||
    CASE WHEN COALESCE(postal_code,'') <> '' THEN ' ' || postal_code ELSE '' END
  ),
  ''
)
WHERE (address IS NULL OR address = '')
  AND (address_line IS NOT NULL OR city IS NOT NULL OR state IS NOT NULL OR postal_code IS NOT NULL);

-- 4) Add status check constraint if missing
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'transactions_status_check'
  ) THEN
    EXECUTE $c$
      ALTER TABLE public.transactions
      ADD CONSTRAINT transactions_status_check
      CHECK (
        status::text = ANY (
          ARRAY[
            'draft','coming_soon','active','attorney_review','pending_uc','closed',
            'temp_off_market','withdrawn','canceled','expired'
          ]::text[]
        )
      )
    $c$;
  END IF;
END $$;

COMMIT;

-- 5) Indexes (run outside transaction is fine, but regular CREATE INDEX is ok here too)
CREATE INDEX IF NOT EXISTS idx_transactions_status ON public.transactions USING btree (status);
CREATE INDEX IF NOT EXISTS idx_transactions_primary_contact_id ON public.transactions USING btree (primary_contact_id);
CREATE INDEX IF NOT EXISTS idx_transactions_secondary_contact_id ON public.transactions USING btree (secondary_contact_id);

-- 6) Foreign keys (only if missing)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'transactions_primary_contact_id_fkey'
  ) THEN
    EXECUTE 'ALTER TABLE ONLY public.transactions
             ADD CONSTRAINT transactions_primary_contact_id_fkey
             FOREIGN KEY (primary_contact_id) REFERENCES public.contacts(id) ON DELETE CASCADE';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'transactions_secondary_contact_id_fkey'
  ) THEN
    EXECUTE 'ALTER TABLE ONLY public.transactions
             ADD CONSTRAINT transactions_secondary_contact_id_fkey
             FOREIGN KEY (secondary_contact_id) REFERENCES public.contacts(id) ON DELETE SET NULL';
  END IF;
END $$;

