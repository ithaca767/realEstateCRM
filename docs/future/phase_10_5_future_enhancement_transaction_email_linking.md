# Future Enhancement: Transaction-Aware Email Linking

**Document Type:** Future Enhancement Proposal\
**Related Phase:** Phase 10 (Email Sync)\
**Created:** 2026-03-01

------------------------------------------------------------------------

## Purpose

To introduce transaction-aware email linking in Ulysses CRM to prevent
cross-client contamination when professionals (e.g., housing authority
reps, attorneys, lenders) work across multiple clients and transactions.

------------------------------------------------------------------------

## Current Model (Phase 10)

-   Emails are stored once in `email_messages`.
-   Emails are linked to contacts via `email_message_links`.
-   Linking is based on header matches (from/to/cc).

This works but is not transaction-aware.

------------------------------------------------------------------------

## Proposed Enhancement

Introduce a new table:

``` sql
CREATE TABLE email_message_transaction_links (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    email_message_id INTEGER NOT NULL REFERENCES email_messages(id) ON DELETE CASCADE,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(email_message_id, transaction_id)
);
```

------------------------------------------------------------------------

## Intended Behavior

When importing emails:

1.  Identify matched contacts.
2.  If matched contact has exactly one active transaction → auto-link
    email to that transaction.
3.  If multiple active transactions → skip auto-link (manual resolution
    possible later).
4.  If none → do not link to transaction.

------------------------------------------------------------------------

## Display Model

-   Contact View: show emails linked to contact.
-   Transaction View: show emails linked to transaction.
-   Professional View: show emails linked to that professional only.

This prevents cross-deal contamination when professionals serve multiple
clients.

------------------------------------------------------------------------

## Edge Cases to Consider

-   Two buyers on one transaction.
-   One professional working across multiple transactions
    simultaneously.
-   Shared mailboxes.
-   Email threads spanning multiple transactions.

------------------------------------------------------------------------

## Status

Preserved for future implementation prior to or after Release 2.0.
