-- 2026_09_22_showings.sql
--
-- First-class Showing records for buyer and listing workflows.
--
-- Design:
-- - A Showing belongs to exactly one Ulysses user.
-- - showing_type distinguishes buyer showings from listing showings.
-- - Buyer showings may include one or more explicitly selected CRM Contacts.
-- - Listing showings may link to an existing seller transaction.
-- - transaction_id is optional because a buyer showing does not require
--   creation of a Transaction.
-- - Address fields preserve the property represented by the Showing itself.
-- - Feedback is intentionally lightweight in v1.
--
-- Security invariants:
-- - Every Showing belongs to exactly one Ulysses user.
-- - Any linked Transaction must belong to that same user.
-- - Every Showing Contact membership must belong to that same user.
-- - Every Contact in a Showing must belong to that same user.
-- - No route, service, API, AI/Assist consumer, background job, Activity
--   Engine consumer, calendar workflow, or future voice workflow may cross
--   tenant boundaries through Showing data.

BEGIN;

-- Composite ownership keys used by tenant-safe child foreign keys.
CREATE UNIQUE INDEX IF NOT EXISTS transactions_user_id_id_uq
    ON transactions (user_id, id);

CREATE TABLE IF NOT EXISTS showings (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,

    showing_type TEXT NOT NULL
        CHECK (showing_type IN ('buyer', 'listing')),

    transaction_id INTEGER,

    address_line TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,

    scheduled_at TIMESTAMPTZ NOT NULL,

    status TEXT NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'completed', 'canceled', 'no_show')),

    showing_agent_name TEXT,
    showing_agent_brokerage TEXT,
    showing_agent_email TEXT,
    showing_agent_phone TEXT,

    interest_level TEXT
        CHECK (
            interest_level IS NULL
            OR interest_level IN (
                'very_interested',
                'interested',
                'neutral',
                'not_interested'
            )
        ),

    feedback TEXT,
    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT showings_user_fk
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT showings_transaction_owner_fk
        FOREIGN KEY (user_id, transaction_id)
        REFERENCES transactions(user_id, id)
        ON DELETE RESTRICT
);

CREATE UNIQUE INDEX IF NOT EXISTS showings_user_id_id_uq
    ON showings (user_id, id);

CREATE INDEX IF NOT EXISTS idx_showings_user_scheduled
    ON showings (user_id, scheduled_at);

CREATE INDEX IF NOT EXISTS idx_showings_user_status
    ON showings (user_id, status);

CREATE INDEX IF NOT EXISTS idx_showings_user_transaction
    ON showings (user_id, transaction_id)
    WHERE transaction_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS showing_contacts (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    showing_id BIGINT NOT NULL,
    contact_id INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT showing_contacts_user_fk
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT showing_contacts_showing_owner_fk
        FOREIGN KEY (user_id, showing_id)
        REFERENCES showings(user_id, id)
        ON DELETE CASCADE,

    CONSTRAINT showing_contacts_contact_owner_fk
        FOREIGN KEY (user_id, contact_id)
        REFERENCES contacts(user_id, id)
        ON DELETE RESTRICT,

    CONSTRAINT showing_contacts_unique_member
        UNIQUE (user_id, showing_id, contact_id)
);

CREATE INDEX IF NOT EXISTS idx_showing_contacts_user_contact
    ON showing_contacts (user_id, contact_id);

CREATE INDEX IF NOT EXISTS idx_showing_contacts_user_showing
    ON showing_contacts (user_id, showing_id);

COMMIT;
