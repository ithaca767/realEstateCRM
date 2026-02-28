-- Phase 10D: DB-backed OAuth state (Outlook, optional Gmail later)

CREATE TABLE IF NOT EXISTS oauth_states (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  state TEXT NOT NULL,
  redirect_path TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  consumed_at TIMESTAMPTZ
);

-- One active state per provider per user (optional but helpful)
CREATE UNIQUE INDEX IF NOT EXISTS oauth_states_user_provider_state_uq
  ON oauth_states(user_id, provider, state);

CREATE INDEX IF NOT EXISTS oauth_states_lookup_active_idx
  ON oauth_states(provider, state)
  WHERE consumed_at IS NULL;

CREATE INDEX IF NOT EXISTS oauth_states_cleanup_idx
  ON oauth_states(created_at)
  WHERE consumed_at IS NULL;