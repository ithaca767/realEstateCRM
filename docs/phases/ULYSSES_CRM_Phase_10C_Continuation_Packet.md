# ULYSSES CRM

## Phase 10C Continuation Packet

Branch: feature/phase-10-email-sync\
Status: Branch-isolated. No deployment assumed.

------------------------------------------------------------------------

# 1. Canon-Ready Phase 10 Section Insertion

## Phase 10: Email Sync (Gmail) Foundation

**Status:** Phase 10A and 10B complete. Phase 10C partially scaffolded.\
**Branch isolation:** All Phase 10 work is confined to
`feature/phase-10-email-sync`. `main` remains production-safe with
auto-deploy enabled and contains no Phase 10 code.

### Goal

Introduce secure, tenant-safe Email Sync infrastructure that can ingest
Gmail messages and link them to Contacts without compromising production
stability or cross-tenant isolation.

------------------------------------------------------------------------

## Phase 10A: Feature Gating (Complete)

-   Added `users.email_sync_enabled BOOLEAN NOT NULL DEFAULT FALSE`.
-   Updated `User` model and `load_user()` to include the flag.
-   Enforced gating in both UI and routes.
-   Email integration routes abort with 403 when disabled.

**Design principle:** Feature flags must be enforced at the route level,
not just templates.

------------------------------------------------------------------------

## Phase 10B: Contact Email Aliases (Complete)

-   Introduced `contact_emails` table for multiple addresses per
    Contact.
-   Enforced strict tenant isolation via `user_id`.
-   Added uniqueness constraint `UNIQUE (user_id, lower(email))`.
-   Backfilled legacy `contacts.email` values.

**Design principle:** Email identity is first-class data, not inferred
from a single field.

------------------------------------------------------------------------

## Phase 10C: OAuth and Storage Foundation (Partial)

-   Added Gmail OAuth integration and `email_accounts` table.
-   Tokens encrypted using Fernet symmetric encryption.
-   Required environment variables:
    -   `GMAIL_OAUTH_CLIENT_ID`
    -   `GMAIL_OAUTH_CLIENT_SECRET`
    -   `GMAIL_OAUTH_REDIRECT_URI`
    -   `EMAIL_TOKEN_ENCRYPTION_KEY`
-   OAuth flow tested locally.

Planned continuation includes: - `email_messages` table -
`email_message_links` table - Gmail ingestion pipeline - Automatic
linking to contacts - Manual reassignment workflow (Option B) - Contact
Email tab enhancements

------------------------------------------------------------------------

# 2. Phase 10C Continuation Plan

## 10C.1 Data Model Completion

### email_messages

Durable storage of ingested Gmail message metadata and parsed fields.

Conceptual columns: - `user_id` - `email_account_id` -
`provider_message_id` - `provider_thread_id` - `subject` -
`from_email` - `to_emails` - `cc_emails` - `sent_at` - `received_at` -
`snippet` - `body_text` - `body_html` - `raw_json` (optional) -
Deduplication constraint on
`(user_id, email_account_id, provider_message_id)`

### email_message_links

Attach ingested messages to CRM entities.

Minimal fields: - `user_id` - `email_message_id` - `contact_id` -
`link_state` - `confidence` - `linked_by` - `linked_at`

Recommended link_state values: - `auto_linked` - `user_linked` -
`user_unlinked` - `needs_review`

------------------------------------------------------------------------

## 10C.2 Ingestion Pipeline (Gmail)

### Manual Ingestion Route

-   POST `/integrations/email/gmail/ingest`
-   Gated by `current_user.email_sync_enabled`
-   Ingest recent messages (last N days)
-   Deduplicated inserts

### Incremental Strategy

-   Store `last_ingested_at` or Gmail `historyId`
-   Begin with timestamp-based ingestion
-   Upgrade to history-based sync later

### Token Refresh Handling

-   Detect expiry
-   Refresh access token
-   Persist rotated token and expiration

------------------------------------------------------------------------

## 10C.3 Matching and Linking (Option B)

### Auto-Linking Algorithm (v1)

-   Normalize all email addresses (lowercase).
-   Lookup `contact_emails` by `(user_id, lower(email))`.
-   If exactly one match, auto-link.
-   Store link row with `auto_linked` and confidence score.

### Manual Reassignment (Option B)

-   User can unlink without deleting message.
-   User can link to a different contact.
-   Preserve audit via `linked_by` and `linked_at`.
-   Support many-to-many linking if future expansion desired.

------------------------------------------------------------------------

# 3. UI Integration Plan

## Integrations Page

-   Show connected account status
-   Sync toggle
-   "Ingest recent emails" button
-   Display last ingested timestamp

## Contact Edit Page -- Email Tab

-   Visible only if feature enabled
-   Paginated table of linked messages
-   Columns: Date, From, Subject, Snippet, Link State
-   Actions: View, Reassign, Unlink
-   Modal or panel for message detail view

------------------------------------------------------------------------

# 4. Migration Ordering Strategy (Future Production Release)

1.  Phase 10A -- Add `users.email_sync_enabled`
2.  Phase 10B -- Add `contact_emails`
3.  Phase 10C -- Add `email_accounts`
4.  Phase 10C -- Add `email_messages`
5.  Phase 10C -- Add `email_message_links`
6.  Run backfills separately and idempotently

Production rule: - Run migrations before deploying dependent code. -
Feature flag remains default FALSE until controlled enablement.

------------------------------------------------------------------------

# End of Phase 10C Continuation Packet
