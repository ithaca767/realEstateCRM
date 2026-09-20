-- 2026_09_20_calendar_feed_tokens.sql
--
-- Per-user calendar feed credentials.
--
-- Security invariants:
-- - A calendar credential belongs to exactly one Ulysses user.
-- - Raw calendar tokens are never stored.
-- - token_hash is generated using the existing TOKEN_PEPPER-backed helper.
-- - Calendar feed access must never imply access to another user's CRM data.

CREATE TABLE IF NOT EXISTS calendar_feed_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS calendar_feed_tokens_active_user_uq
    ON calendar_feed_tokens (user_id)
    WHERE revoked_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS calendar_feed_tokens_token_hash_uq
    ON calendar_feed_tokens (token_hash);
