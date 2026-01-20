-- 2026_01_15_newsletter_signup_links_and_contact_optin.sql

BEGIN;

-- 1) Contacts: newsletter fields
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS newsletter_opt_in boolean NOT NULL DEFAULT false,
ADD COLUMN IF NOT EXISTS newsletter_opt_in_date timestamp without time zone,
ADD COLUMN IF NOT EXISTS newsletter_source text;

-- 2) Public link table (like open_houses public_token concept)
CREATE TABLE IF NOT EXISTS newsletter_signup_links (
  id serial PRIMARY KEY,
  created_by_user_id integer NOT NULL REFERENCES users(id),
  title text NOT NULL,
  public_token text NOT NULL UNIQUE,
  redirect_url text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamp without time zone DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_newsletter_links_user_id
ON newsletter_signup_links(created_by_user_id);

COMMIT;
