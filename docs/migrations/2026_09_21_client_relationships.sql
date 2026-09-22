-- 2026_09_21_client_relationships.sql
--
-- First-class client relationship records.
--
-- A contact may have multiple client relationships over time.
-- A "Current Client" is a contact with at least one current relationship.
--
-- Security invariants:
-- - Every client relationship belongs to exactly one Ulysses user.
-- - The composite foreign key guarantees that contact_id belongs to the
--   same user_id stored on the client relationship.
-- - No route, service, API, AI/Assist consumer, background job, or future
--   workflow may use a relationship record to cross tenant boundaries.

BEGIN;

-- contacts.id is already globally unique. This additional unique key exists
-- so tenant-owned child records can enforce (user_id, contact_id) together.
CREATE UNIQUE INDEX IF NOT EXISTS contacts_user_id_id_uq
    ON contacts (user_id, id);

CREATE TABLE IF NOT EXISTS client_relationships (
    id BIGSERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL,
    contact_id INTEGER NOT NULL,

    relationship_type TEXT NOT NULL,
    agreement_type TEXT NOT NULL,

    signed_date DATE NOT NULL,
    end_date DATE,

    status TEXT NOT NULL DEFAULT 'current'
        CHECK (status IN ('current', 'ended')),

    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT client_relationships_user_fk
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT client_relationships_contact_owner_fk
        FOREIGN KEY (user_id, contact_id)
        REFERENCES contacts(user_id, id)
        ON DELETE RESTRICT,

    CONSTRAINT client_relationships_dates_check
        CHECK (end_date IS NULL OR end_date >= signed_date)
);

CREATE INDEX IF NOT EXISTS idx_client_relationships_user_contact
    ON client_relationships (user_id, contact_id);

CREATE INDEX IF NOT EXISTS idx_client_relationships_user_status
    ON client_relationships (user_id, status);

CREATE INDEX IF NOT EXISTS idx_client_relationships_current_contact
    ON client_relationships (user_id, contact_id)
    WHERE status = 'current';

COMMIT;
