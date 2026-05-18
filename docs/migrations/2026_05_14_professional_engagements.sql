CREATE TABLE IF NOT EXISTS professional_engagements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,

    conversation_type TEXT NOT NULL DEFAULT 'call',
    occurred_at TIMESTAMPTZ,

    notes TEXT,
    transcript_raw TEXT,
    summary_clean TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_professional_engagements_user_professional
ON professional_engagements(user_id, professional_id);

CREATE INDEX IF NOT EXISTS idx_professional_engagements_occurred_at
ON professional_engagements(user_id, occurred_at DESC);
