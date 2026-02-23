-- 2026_02_22_phase10c_email_messages.sql
-- Phase 10C: Store imported email messages and link them to contacts.

CREATE TABLE IF NOT EXISTS email_messages (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  email_account_id INTEGER NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,

  provider TEXT NOT NULL, -- 'gmail'
  provider_message_id TEXT NOT NULL,
  provider_thread_id TEXT,

  message_date TIMESTAMPTZ,
  subject TEXT,
  from_name TEXT,
  from_email TEXT,

  to_emails JSONB,
  cc_emails JSONB,

  snippet TEXT,

  -- Phase 10C: snippet-first. Bodies can be added later.
  body_text TEXT,
  body_html TEXT,

  direction TEXT, -- 'inbound', 'outbound', 'unknown'

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Dedupe: unique per user + account + provider message id
CREATE UNIQUE INDEX IF NOT EXISTS ux_email_messages_user_account_provider_msg
  ON email_messages (user_id, email_account_id, provider, provider_message_id);

CREATE INDEX IF NOT EXISTS ix_email_messages_user_date
  ON email_messages (user_id, message_date DESC);

CREATE INDEX IF NOT EXISTS ix_email_messages_user_from_email
  ON email_messages (user_id, lower(from_email));

CREATE INDEX IF NOT EXISTS ix_email_messages_user_account_date
  ON email_messages (user_id, email_account_id, message_date DESC);

CREATE TABLE IF NOT EXISTS email_message_links (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  email_message_id INTEGER NOT NULL REFERENCES email_messages(id) ON DELETE CASCADE,
  contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,

  match_type TEXT NOT NULL, -- 'from', 'to', 'cc', 'manual'
  matched_email TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_email_links_user_msg_contact_type
  ON email_message_links (user_id, email_message_id, contact_id, match_type);

CREATE INDEX IF NOT EXISTS ix_email_links_user_contact
  ON email_message_links (user_id, contact_id);

CREATE INDEX IF NOT EXISTS ix_email_links_user_message
  ON email_message_links (user_id, email_message_id);

COMMENT ON TABLE email_messages IS 'Phase 10C: Imported email messages (snippet-first).';
COMMENT ON TABLE email_message_links IS 'Phase 10C: Links between emails and contacts (auto + manual).';