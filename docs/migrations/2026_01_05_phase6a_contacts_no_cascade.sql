BEGIN;

-- Convert ON DELETE CASCADE to ON DELETE RESTRICT for all FKs referencing contacts

ALTER TABLE buyer_profiles
  DROP CONSTRAINT IF EXISTS buyer_profiles_contact_id_fkey;
ALTER TABLE buyer_profiles
  ADD CONSTRAINT buyer_profiles_contact_id_fkey
  FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE RESTRICT;

ALTER TABLE seller_profiles
  DROP CONSTRAINT IF EXISTS seller_profiles_contact_id_fkey;
ALTER TABLE seller_profiles
  ADD CONSTRAINT seller_profiles_contact_id_fkey
  FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE RESTRICT;

ALTER TABLE engagements
  DROP CONSTRAINT IF EXISTS engagements_contact_id_fkey;
ALTER TABLE engagements
  ADD CONSTRAINT engagements_contact_id_fkey
  FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE RESTRICT;

ALTER TABLE interactions
  DROP CONSTRAINT IF EXISTS interactions_contact_id_fkey;
ALTER TABLE interactions
  ADD CONSTRAINT interactions_contact_id_fkey
  FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE RESTRICT;

ALTER TABLE listing_checklist_items
  DROP CONSTRAINT IF EXISTS listing_checklist_items_contact_id_fkey;
ALTER TABLE listing_checklist_items
  ADD CONSTRAINT listing_checklist_items_contact_id_fkey
  FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE RESTRICT;

ALTER TABLE contact_special_dates
  DROP CONSTRAINT IF EXISTS contact_special_dates_contact_id_fkey;
ALTER TABLE contact_special_dates
  ADD CONSTRAINT contact_special_dates_contact_id_fkey
  FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE RESTRICT;

ALTER TABLE related_contacts
  DROP CONSTRAINT IF EXISTS related_contacts_contact_id_fkey;
ALTER TABLE related_contacts
  ADD CONSTRAINT related_contacts_contact_id_fkey
  FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE RESTRICT;

ALTER TABLE contact_associations
  DROP CONSTRAINT IF EXISTS contact_associations_contact_id_primary_fkey;
ALTER TABLE contact_associations
  ADD CONSTRAINT contact_associations_contact_id_primary_fkey
  FOREIGN KEY (contact_id_primary) REFERENCES contacts(id) ON DELETE RESTRICT;

ALTER TABLE contact_associations
  DROP CONSTRAINT IF EXISTS contact_associations_contact_id_related_fkey;
ALTER TABLE contact_associations
  ADD CONSTRAINT contact_associations_contact_id_related_fkey
  FOREIGN KEY (contact_id_related) REFERENCES contacts(id) ON DELETE RESTRICT;

ALTER TABLE transactions
  DROP CONSTRAINT IF EXISTS transactions_contact_id_fkey;
ALTER TABLE transactions
  ADD CONSTRAINT transactions_contact_id_fkey
  FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE RESTRICT;

ALTER TABLE transactions
  DROP CONSTRAINT IF EXISTS transactions_primary_contact_id_fkey;
ALTER TABLE transactions
  ADD CONSTRAINT transactions_primary_contact_id_fkey
  FOREIGN KEY (primary_contact_id) REFERENCES contacts(id) ON DELETE RESTRICT;

-- Leave these alone (already safe):
-- tasks_contact_id_fkey (ON DELETE SET NULL)
-- transactions_secondary_contact_id_fkey (ON DELETE SET NULL)

COMMIT;
