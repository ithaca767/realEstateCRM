# ULYSSES CRM

## AI Backend Route and Service Contract – v1.1.0

**Feature:** AI-Assisted Engagement Transcript Summarization  
**Release:** v1.1.0 (Phase 8.1)  
**Baseline:** Production v1.0.3  
**Status:** Canon-bound specification

---

## 1. Purpose

This document defines the backend route(s), request and response schema, error semantics, and service-layer boundaries for the v1.1.0 AI-assisted engagement summarization feature.

The goal is to provide a stable, testable contract that:

* Enforces opt-in and rate limits server-side
* Uses the v1.1.0 Prompt Contract without drift
* Returns structured outputs suitable for the Engagement UI modal

---

## 2. Scope

This contract covers only:

* User-initiated transcript summarization

It explicitly excludes:

* Background processing
* Any other AI features

---

## 3. Endpoint

### 3.1 Route

`POST /api/ai/engagements/summarize`

Notes:

* Route is API-only (no template rendering)
* Authentication required
* Intended consumer is the Engagement modal

---

## 4. Authentication and Authorization

### 4.1 Authentication

* Must require `@login_required` (or equivalent)
* Session-based auth is acceptable for first-party UI

### 4.2 Authorization

* AI access requires global flag AND user opt-in
* AI access must be enforced server-side even if UI hides the feature

Authorization checks must be centralized via the AI guard function defined in the Opt-In spec.

---

## 5. Request Schema

### 5.1 Content-Type

* `application/json`

### 5.2 JSON Body

Required fields:

```json
{
  "engagement_id": 123,
  "source_text": "...",
  "prompt_version": "v1.1.0"
}
```

Field rules:

* `engagement_id` is required and must belong to the current user (tenant-safe)
* `source_text` is required, non-empty, and provided by the user
* `prompt_version` must equal `v1.1.0` for this release line

Input constraints:

* Reject payloads above a configured maximum (recommended: 25,000 characters)
* Trim leading and trailing whitespace

---

## 6. Response Schema

### 6.1 Success Response

* HTTP 200

```json
{
  "ok": true,
  "prompt_version": "v1.1.0",
  "result": {
    "one_sentence_summary": "...",
    "crm_narrative_summary": "...",
    "suggested_follow_up_items": [
      "...",
      "..."
    ]
  },
  "usage": {
    "daily_requests_used": 3,
    "daily_request_limit": 10,
    "monthly_spend_cents": 425,
    "monthly_cap_cents": 2000
  }
}
```

Field rules:

* `suggested_follow_up_items` must be an array
* If none are identified, return an empty array
* `usage` is included to support UI display and transparency

---

## 7. Error Semantics

All errors return:

* `ok: false`
* `error.code` (stable string)
* `error.message` (user-safe)

### 7.1 Standard Error Shape

```json
{
  "ok": false,
  "error": {
    "code": "...",
    "message": "..."
  }
}
```

### 7.2 Error Codes and Status

* 400 `invalid_request`  
  Missing or invalid parameters

* 403 `ai_not_enabled`  
  User has not opted into AI

* 403 `ai_globally_disabled`  
  Global AI flag is off

* 404 `engagement_not_found`  
  Engagement does not exist or does not belong to current user

* 413 `payload_too_large`  
  Input exceeds configured limit

* 429 `ai_daily_limit_reached`  
  Daily request limit exceeded

* 429 `ai_monthly_cap_reached`  
  Monthly spend cap reached

* 502 `ai_upstream_error`  
  OpenAI returned an error or invalid response

* 504 `ai_timeout`  
  OpenAI call exceeded timeout

Error messages must be neutral and must not expose internal secrets.

---

## 8. Guardrails and Enforcement

### 8.1 Central Guard Function

The endpoint must call a shared guard function that enforces:

* Global flag is enabled
* User opt-in is enabled
* Daily and monthly usage limits are respected
* Input is present and within size limits

The guard must return a structured reason to map to the error codes above.

---

## 9. Service Layer Boundaries

### 9.1 Controller Responsibilities

The route handler must:

1. Validate request schema
2. Verify engagement ownership (tenant-safe)
3. Invoke AI guard
4. Call service layer to generate summaries
5. Post-process into structured fields
6. Return response JSON

The controller must not:

* Embed prompt text inline
* Make direct OpenAI calls

---

### 9.2 Service Responsibilities

A dedicated service (example name: `ai_summarize_engagement_text`) must:

* Assemble prompts using the Prompt Contract document
* Call OpenAI via a single client wrapper
* Parse the model output into structured fields
* Return structured data back to the controller

The service must not:

* Read or mutate the Engagement record
* Persist data
* Create tasks or emails

---

## 10. OpenAI Client Wrapper Contract

All OpenAI calls must route through a single wrapper module.

Wrapper responsibilities:

* Reads API key from environment
* Applies model name from config
* Applies timeouts and retry policy
* Normalizes upstream errors into internal error types

Recommended configuration keys:

* `OPENAI_API_KEY`
* `OPENAI_MODEL_SUMMARIZE` (default set explicitly)
* `OPENAI_TIMEOUT_SECONDS` (recommended: 30)
* `AI_FEATURES_AVAILABLE` (global flag)

---

## 11. Prompt Version Binding

The backend must bind the request to `prompt_version: v1.1.0`.

Rules:

* If the request specifies a different prompt version, reject with `invalid_request`
* Prompt text used must be the v1.1.0 System Prompt and Instruction Prompt as defined in the Prompt Contract document

Silent prompt changes are prohibited.

---

## 12. Output Parsing Rules

The service must enforce the Output Contract:

* Extract the three labeled sections
* Normalize whitespace
* Return strings for the two summary fields
* Return a list for follow-up items

If parsing fails:

* Return `ai_upstream_error`
* Do not increment usage counters

---

## 13. Usage Accounting

Usage counters must be incremented only after a successful OpenAI response and successful parsing.

Recommended approach:

1. Make OpenAI call
2. Parse response
3. Increment usage counters
4. Return success

If any step fails, no counters should be incremented.

---

## 14. Observability

Minimum recommended logging (no sensitive content):

* user_id
* engagement_id
* prompt_version
* input_char_count
* outcome (success or error code)
* latency_ms

Logs must not include:

* full transcript text
* OpenAI API key
* raw OpenAI response

---

## 15. Security Notes

* Do not log source text
* Do not echo secrets
* Encourage users in UI disclosures not to paste credentials or private identifiers

---

## 16. Definition of Done

This contract is complete when:

* The endpoint exists and returns the defined schemas
* Guardrails are enforced server-side
* Tenant isolation is enforced for engagement access
* Prompt version binding is enforced
* Usage counters update only on successful completion

---

## 17. Canon Statement

> *In Ulysses CRM, AI is invoked through stable, version-bound contracts. All access is opt-in, all execution is intentional, and all results are reviewable before becoming part of the record.*
