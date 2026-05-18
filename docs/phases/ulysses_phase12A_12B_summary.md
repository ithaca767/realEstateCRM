# Ulysses CRM – Phase 12A/12B AI Transcription Progress Summary

## Current Status

Completed substantial groundwork for Ulysses CRM AI transcription workflow integration.

The project evolved from an initial standalone Whisper/transcription page concept into a much cleaner and more “Ulysses-native” architecture:

```text
Transcription → Transcript → Existing AI Assist → Manual Save
```

The key architectural decision was:

> Transcription is an input tool into the existing AI engagement pipeline, not a separate AI system.

This preserves:
- existing AI guardrails
- no-auto-save philosophy
- existing AI Assist preview workflow
- structured prompt/parsing contracts
- user-intent-only persistence

---

# Phase 12A – Standalone Transcription Page

## Implemented

Created:

```text
/transcriptions
```

Features:
- upload audio
- call OpenAI transcription endpoint
- temporary file processing only
- transcript preview
- copy transcript
- summarize transcript
- AI preview
- no DB persistence unless user manually uses output elsewhere

Uses existing:
- AI guard
- OpenAI wrapper
- AI summarization pipeline

No audio retention.

No auto-save.

---

# Phase 12B – Engagement Page Transcription Modal

## Implemented

Added modal transcription workflow to:

```text
templates/edit_engagement.html
```

Workflow:

```text
Open engagement
→ Upload Audio / Transcribe
→ Modal upload
→ Transcript preview
→ Insert into transcript_raw
→ Existing AI Assist summarizes
→ Manual Save Changes
```

## Important Design Decision

No automatic:
- engagement creation
- transcript persistence
- summary persistence
- follow-up creation

Everything remains manual-save.

---

# Modal Details

## Added Button

Near:

```text
Transcript (raw)
```

Added:

```text
Upload Audio / Transcribe
```

## Added Modal

```text
#engTranscriptionModal
```

Features:
- upload audio
- transcribe audio
- transcript preview
- insert transcript
- append transcript

## Added JS

Reuses:

```text
POST /api/ai/transcribe
```

Inserts transcript directly into:

```js
textarea[name="transcript_raw"]
```

---

# Edit Contact Page Work

## Discovered

The modal existed only in:

```text
edit_engagement.html
```

But NOT in:

```text
edit_contact.html
```

Specifically:

```text
Engagement Log → Create Engagement form
```

still used manual paste-only workflow.

## Current Required Work

Need to finish integration inside:

```text
templates/edit_contact.html
```

### Current State

The button was successfully added:

```text
Upload Audio / Transcribe
```

inside the “Paste transcript and summary (optional)” collapse area.

Need to fully wire:
- modal
- modal JS
- transcript insertion

for the engagement creation form.

---

# Important JS Adjustment

For `edit_contact.html`, transcript insertion must target:

```js
form[data-engagement-create="1"]
```

instead of generic:

```js
document.querySelector('textarea[name="transcript_raw"]')
```

Correct pattern:

```js
const createForm = document.querySelector('form[data-engagement-create="1"]');

const transcriptField = createForm
  ? createForm.querySelector('textarea[name="transcript_raw"]')
  : document.querySelector('textarea[name="transcript_raw"]');
```

This prevents transcript insertion into the wrong textarea.

---

# AI Guard / Usage Findings

Discovered transcription calls are using the same AI usage counters as summarization.

Meaning:

```text
Transcribe = 1 AI request
Summarize = 1 AI request
```

User hit local limit of 10 rapidly during testing.

## Local Dev Adjustment Made

Updated local user:

```sql
UPDATE users
SET ai_daily_request_limit = 100
WHERE email = 'dennis@local.dev';
```

Current local settings:

```text
ai_daily_request_limit = 100
ai_daily_requests_used = 1
```

---

# Architectural Decisions Locked

## Keep BOTH

### Standalone Utility Page

```text
/transcriptions
```

### Engagement Modal Add-On

Inside:
- edit_engagement.html
- edit_contact.html

---

# Future Add-On Gating Decision

## Long-Term

Add:

```sql
users.transcription_enabled BOOLEAN DEFAULT FALSE
```

Use:

```python
current_user.transcription_enabled
```

to gate feature.

## Temporary

May reuse:
- ai_enabled
- ai_premium_enabled

until migration exists.

---

# Professional Conversation Logging (NEXT CHAT)

## Major Decision

Do NOT overload:

```text
engagements.contact_id
```

with professional conversations.

## Recommended Architecture

Create separate table:

```sql
professional_engagements
```

instead of adding `professional_id` to engagements.

Reason:
- cleaner domain separation
- avoids muddying “contact engagement”
- cleaner future UI
- cleaner AI workflows

## Proposed Table

```sql
CREATE TABLE professional_engagements (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  professional_id INTEGER NOT NULL REFERENCES professionals(id),
  engagement_type TEXT NOT NULL,
  occurred_at TIMESTAMPTZ,
  outcome TEXT,
  notes TEXT,
  transcript_raw TEXT,
  summary_clean TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

# Proposed Professional Workflow

```text
Professionals
→ Open professional
→ Add Conversation
→ Upload Audio / Transcribe
→ AI Assist
→ Save Professional Engagement
```

Supports:
- attorneys
- lenders
- inspectors
- contractors
- title reps
- etc.

without mixing them into contact engagement history.

---

# Documents Needed for Next Chat

Please bring:
- current `professionals.html`
- current `edit_professional.html`
- any professional-related routes in `app.py`
- any existing professional schema/migrations if available

Especially important:
- how professionals are currently edited/viewed
- whether professional notes/history already exist
- current professionals table structure

That will allow clean design of:
- professional engagement UI
- routes
- schema
- AI integration
- transcription modal reuse
