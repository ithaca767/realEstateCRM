-- 2026_09_22_client_relationship_contacts.sql
--
-- Allow one client relationship to include one or more Contacts.
--
-- Transitional design:
-- - client_relationships remains the representation/agreement record.
-- - client_relationship_contacts stores the Contacts included in it.
-- - Existing client_relationships.contact_id remains temporarily for
--   backward compatibility with the currently deployed application.
-- - Existing relationships are backfilled into the membership table.
--
-- Security invariants:
-- - Every membership belongs to exactly one Ulysses user.
-- - The relationship must belong to that same user.
-- - The contact must belong to that same user.
-- - A contact may appear only once in a given client relationship.

BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS client_relationships_user_id_id_uq
    ON client_relationships (user_id, id);

CREATE TABLE IF NOT EXISTS client_relationship_contacts (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    relationship_id BIGINT NOT NULL,
    contact_id INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT client_relationship_contacts_user_fk
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT client_relationship_contacts_relationship_owner_fk
        FOREIGN KEY (user_id, relationship_id)
        REFERENCES client_relationships(user_id, id)
        ON DELETE CASCADE,

    CONSTRAINT client_relationship_contacts_contact_owner_fk
        FOREIGN KEY (user_id, contact_id)
        REFERENCES contacts(user_id, id)
        ON DELETE RESTRICT,

    CONSTRAINT client_relationship_contacts_unique_member
        UNIQUE (user_id, relationship_id, contact_id)
);

CREATE INDEX IF NOT EXISTS idx_client_relationship_contacts_user_contact
    ON client_relationship_contacts (user_id, contact_id);

CREATE INDEX IF NOT EXISTS idx_client_relationship_contacts_user_relationship
    ON client_relationship_contacts (user_id, relationship_id);

INSERT INTO client_relationship_contacts (
    user_id,
    relationship_id,
    contact_id
)
SELECT
    cr.user_id,
    cr.id,
    cr.contact_id
FROM client_relationships cr
WHERE NOT EXISTS (
    SELECT 1
    FROM client_relationship_contacts crc
    WHERE crc.user_id = cr.user_id
      AND crc.relationship_id = cr.id
      AND crc.contact_id = cr.contact_id
);

COMMIT;
