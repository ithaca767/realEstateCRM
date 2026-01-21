# Ulysses CRM – Messaging (SMS & Email) Opt‑Out and Compliance Design Notes

**Status:** Reference / Future Design  
**Scope:** SMS texting and email communications with opt‑out support  
**Audience:** Internal product and engineering planning  
**Disclaimer:** This document reflects practical, conservative industry patterns. It is not legal advice.

---

## 1. Purpose

This document outlines a compliant, pragmatic approach for supporting:

- SMS texting with opt‑out handling
- Email sending with unsubscribe capability

The goal is to enable real estate communication workflows while minimizing regulatory and operational risk.

---

## 2. Guiding Principles

1. **Consent is tracked, not assumed**
2. **Opt‑out is easy, immediate, and enforced**
3. **Suppression beats cleverness**
4. **One‑to‑one messaging and campaigns are treated differently**
5. **Auditability matters**

---

## 3. SMS (Text Messaging) Design

### 3.1 Consent Model

Each phone number should track:

- `sms_consent_status`
  - unknown
  - opted_in
  - opted_out
- `sms_consent_source`
  - written
  - verbal
  - form
  - other
- `sms_consent_at`
- `sms_opted_out_at`

Default state for new contacts: `unknown`.

---

### 3.2 Opt‑Out Handling

SMS messages that are automated or templated should include:

> “Reply STOP to opt out. Reply HELP for help.”

System behavior:
- Incoming message with STOP (or equivalent) immediately:
  - sets `sms_consent_status = opted_out`
  - records `sms_opted_out_at`
- All future SMS to that number are blocked unless re‑opt‑in is recorded.

---

### 3.3 Message Types

#### 1:1 Personal Messages
- Used for active clients and transactional communication
- Still respect opt‑out status
- Do not auto‑send if opted out

#### Campaign / Bulk Messages
- Require explicit opt‑in
- Must include opt‑out language
- Must be logged with timestamp and message content

---

## 4. Email Design

### 4.1 Consent and Suppression

Each email address should track:

- `email_consent_status`
  - unknown
  - opted_in
  - opted_out
- `email_opted_out_at`

---

### 4.2 Unsubscribe Mechanism

All marketing or bulk emails must include:

- A visible unsubscribe link
- One‑click or minimal friction unsubscribe
- Suppression enforced immediately upon unsubscribe

---

### 4.3 Transactional vs Marketing Email

- **Transactional emails**
  - Appointment confirmations
  - Contract milestones
  - Required disclosures
- **Marketing emails**
  - Newsletters
  - Announcements
  - Promotions

Marketing emails must always respect opt‑out and include unsubscribe links.

---

## 5. Data Model (Conceptual)

Suggested fields on Contact or Communication Channel:

### Phone
- phone_number
- sms_consent_status
- sms_consent_source
- sms_consent_at
- sms_opted_out_at

### Email
- email_address
- email_consent_status
- email_opted_out_at

---

## 6. Enforcement Rules

Before sending any message:

1. Check channel consent status
2. If opted out → block send
3. Log attempt (optional but recommended)
4. Never override suppression automatically

---

## 7. Integration Strategy

### Phase A (Recommended First)
- Track consent and opt‑out locally
- Enforce suppression
- Send via third‑party provider (SMS or email)

### Phase B (Later)
- Campaign management
- Delivery analytics
- Bounce handling
- Provider webhooks

---

## 8. Risk Management Notes

- SMS compliance has real financial penalties
- Err on the side of blocking messages
- Preserve opt‑out records indefinitely
- Avoid ambiguous consent states

---

## 9. Relationship to Tasks and Engagements

- Engagements record what was sent or received
- Tasks can represent follow‑ups created as a result of messaging
- Messaging systems should log an Engagement record for every outbound SMS or email

---

## 10. Out of Scope (For Now)

- MMS support
- Short code provisioning
- AI‑generated campaign content
- Cross‑account shared suppression lists

---

## 11. Summary

- SMS and email opt‑out is achievable and manageable
- The key challenge is compliance discipline, not technology
- Ulysses should implement conservative defaults and explicit user intent

This document is intended as a durable reference for future implementation.

---
