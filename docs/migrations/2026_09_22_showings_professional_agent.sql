BEGIN;

-- Required for tenant-safe composite foreign keys that reference Professionals.
CREATE UNIQUE INDEX IF NOT EXISTS professionals_user_id_id_uq
    ON professionals (user_id, id);

-- A Showing may be associated with a reusable Professional record for
-- the cooperating/showing agent. Manual showing-agent fields remain on
-- showings as historical snapshot/fallback information.
ALTER TABLE showings
    ADD COLUMN IF NOT EXISTS showing_agent_professional_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_showings_user_agent_professional
    ON showings (user_id, showing_agent_professional_id)
    WHERE showing_agent_professional_id IS NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'showings_agent_professional_owner_fk'
          AND conrelid = 'showings'::regclass
    ) THEN
        ALTER TABLE showings
            ADD CONSTRAINT showings_agent_professional_owner_fk
            FOREIGN KEY (user_id, showing_agent_professional_id)
            REFERENCES professionals (user_id, id)
            ON DELETE RESTRICT;
    END IF;
END
$$;

COMMIT;
