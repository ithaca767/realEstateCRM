BEGIN;

CREATE TABLE IF NOT EXISTS buyer_checklist_items (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE RESTRICT,
    item_key TEXT NOT NULL,
    label TEXT NOT NULL,
    due_date DATE,
    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    UNIQUE (contact_id, item_key)
);

CREATE INDEX IF NOT EXISTS idx_buyer_checklist_contact
ON buyer_checklist_items(contact_id);

CREATE INDEX IF NOT EXISTS idx_buyer_checklist_due_date
ON buyer_checklist_items(due_date);

CREATE INDEX IF NOT EXISTS idx_buyer_checklist_complete_due
ON buyer_checklist_items(is_complete, due_date);

CREATE INDEX IF NOT EXISTS idx_buyer_checklist_contact_active
ON buyer_checklist_items(contact_id)
WHERE archived_at IS NULL;

INSERT INTO buyer_checklist_items
    (contact_id, item_key, label, is_complete)
SELECT
    bp.contact_id,
    v.item_key,
    v.label,
    v.is_complete
FROM buyer_profiles bp
CROSS JOIN LATERAL (
    VALUES
        ('cis_signed',
         'Consumer Information Statement Signed',
         COALESCE(bp.cis_signed, FALSE)),

        ('buyer_agreement_signed',
         'Buyer Agency Agreement Signed',
         COALESCE(bp.buyer_agreement_signed, FALSE)),

        ('wire_fraud_notice_signed',
         'Wire Fraud Notice Signed',
         COALESCE(bp.wire_fraud_notice_signed, FALSE)),

        ('dual_agency_consent_signed',
         'Informed Consent to Dual Agency Signed',
         COALESCE(bp.dual_agency_consent_signed, FALSE)),

        ('preapproval_letter_received',
         'Pre-approval Letter Received',
         COALESCE(bp.preapproval_letter_received, FALSE)),

        ('proof_of_funds_received',
         'Proof of Funds Received (if applicable)',
         COALESCE(bp.proof_of_funds_received, FALSE)),

        ('photo_id_received',
         'Photo ID Received',
         COALESCE(bp.photo_id_received, FALSE))
) AS v(item_key, label, is_complete)
ON CONFLICT (contact_id, item_key) DO NOTHING;

COMMIT;
