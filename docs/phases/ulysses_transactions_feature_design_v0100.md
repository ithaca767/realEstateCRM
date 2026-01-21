# Ulysses CRM - Transactions Feature Design
Target version: v0.10.0
Status: Locked for implementation
Owner: Dennis Fotopoulos
Purpose: Preserve canonical design decisions for Listings and Offers

---

## 1. Executive Summary

The Transactions feature elevates Ulysses CRM from a contact-centric system to a transaction-aware real estate CRM.

Rather than attaching statuses, prices, and deadlines directly to buyers or sellers, Ulysses introduces a first-class Transaction object that represents:

- A seller-side Listing
- A buyer-side Offer

Transactions are the sole owners of:
- Status lifecycle
- Pricing evolution
- Critical dates and deadlines

Buyer and Seller sheets reflect transactions.
The Dashboard synthesizes transactions.
No other object owns transactional truth.

This feature is scoped for v0.10.0 and intentionally excludes commissions, MLS sync, and reporting.

---

## 2. Conceptual Model

### 2.1 Core Object: Transaction

A Transaction represents a single real-world deal instance.

A transaction:
- Is either a listing or an offer
- Has exactly one primary contact
- May optionally have a secondary contact (future use)
- Progresses through a defined status lifecycle
- Owns prices, dates, and deadlines

Buyers and sellers do not have statuses.
Transactions do.

---

## 3. Transaction Types

| Type    | Description                    |
|--------|--------------------------------|
| listing | Seller-side property listing   |
| offer   | Buyer-side offer on a property |

Both types share the same lifecycle, fields, and dashboard logic.

---

## 4. Status Lifecycle (Canonical)

### 4.1 Shared Status Enum (Locked)

Statuses are shared across listings and offers.

Lifecycle order (authoritative):

1. Draft (default)
2. Coming Soon
3. Active
4. Attorney Review
5. Pending/UC
6. Closed
7. Temporarily Off Market
8. Withdrawn
9. Canceled (Final)
10. Expired

### 4.2 Status Rules

- Draft is the initial status for all transactions
- Closed is terminal
- All other statuses preserve historical data
- Draft is visible in Ulysses but never public-facing
- UI labels match MLS language exactly
- Internal storage uses lowercase snake_case

---

## 5. Data Model (v0.10.0)

### 5.1 Transactions Table

This table supports both listings and offers.

```sql
CREATE TABLE transactions (
  id SERIAL PRIMARY KEY,

  -- Type and status
  transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('listing', 'offer')),
  status VARCHAR(30) NOT NULL,

  -- Core details
  address TEXT NOT NULL,

  -- Relationships
  primary_contact_id INTEGER NOT NULL REFERENCES contacts(id),
  secondary_contact_id INTEGER REFERENCES contacts(id),

  -- Pricing
  list_price NUMERIC(12,2),
  offer_price NUMERIC(12,2),
  accepted_price NUMERIC(12,2),
  closed_price NUMERIC(12,2),

  -- Core milestone dates (authoritative order)
  list_date DATE,
  attorney_review_end_date DATE,
  inspection_deadline DATE,
  financing_contingency_date DATE,
  appraisal_deadline DATE,
  mortgage_commitment_date DATE,

  -- Closing dates
  expected_close_date DATE,
  actual_close_date DATE,

  -- Audit fields
  status_changed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2 Design Rationale

- Single table avoids duplication and branching logic
- Pricing fields accommodate full lifecycle without forcing values
- Core milestone dates cover the majority of real-world deals
- No commissions included (explicitly deferred)

---

## 6. Custom Deadlines Model

### 6.1 Purpose

Custom deadlines capture deal-specific requirements without bloating the transactions table.

Examples:
- CO inspection
- Fire certification
- HOA documents
- Septic certification
- Buyer documentation deadlines

### 6.2 Transaction Deadlines Table

```sql
CREATE TABLE transaction_deadlines (
  id SERIAL PRIMARY KEY,
  transaction_id INTEGER NOT NULL
    REFERENCES transactions(id)
    ON DELETE CASCADE,

  label VARCHAR(100) NOT NULL,
  due_date DATE NOT NULL,
  reminder_offset_days INTEGER DEFAULT 0,
  completed BOOLEAN DEFAULT FALSE,
  notes TEXT,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6.3 Behavioral Rules

- Deadlines generate reminders based on due_date minus reminder_offset_days
- Completed deadlines do not surface as overdue
- Deadlines are preserved for historical context
- Deleting a transaction deletes its deadlines

---

## 7. User Workflows

### 7.1 Seller-Side: Listing Lifecycle

1. Navigate to Seller Sheet
2. Click "+ Add Listing"
3. Transaction created with:
   - Status = Draft
   - Primary contact linked
4. Progress through lifecycle:
   - Coming Soon -> Active -> Attorney Review -> Pending/UC -> Closed
5. Alternate outcomes:
   - Withdrawn
   - Temporarily Off Market
   - Canceled (Final)
   - Expired

Each status change:
- Updates status
- Sets status_changed_at
- Preserves historical data

---

### 7.2 Buyer-Side: Offer Lifecycle

1. Navigate to Buyer Sheet
2. Click "+ Add Offer"
3. Transaction created with:
   - Status = Draft
   - Offer price (if known)
4. Progress mirrors listing lifecycle
5. Closing converts the offer to a completed transaction

---

## 8. Dashboard Behavior

### 8.1 Source of Truth

The Dashboard is read-only intelligence.

- No editing
- No status changes
- No direct data ownership

### 8.2 Dashboard Sections

- Draft Transactions (optional visibility)
- Coming Soon
- Active Listings
- Active Buyer Offers
- Pending/UC
- Upcoming Deadlines
- Overdue Deadlines
- Closings in Next 30 / 60 Days

All dashboard items link back to:
- The transaction
- The related contact
- Engagement history

---

## 9. Versioning and Scope Control

### 9.1 Included in v0.10.0

- Transactions table
- Transaction deadlines table
- Status lifecycle
- Buyer and seller sheet integration
- Dashboard synthesis

### 9.2 Explicitly Out of Scope

- Commission calculations
- MLS sync
- Reporting and analytics
- Buyer-to-seller transaction linking
- Automation beyond reminders

These are candidates for v0.11.0+.

---

## 10. Guiding Principles (Non-Negotiable)

- Transactions own truth
- Statuses are MLS-realistic
- Dashboard mirrors, never edits
- Flexibility without schema chaos
- Preserve history over deletion
- Do it right once

---

## 11. Document Contract

This document is the authoritative reference for the Transactions feature.

Changes require:
- Explicit agreement
- Version consideration
- Intentional revision of this document

No silent drift.

End of document
