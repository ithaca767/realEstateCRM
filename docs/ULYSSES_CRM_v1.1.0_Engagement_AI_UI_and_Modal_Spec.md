# ULYSSES CRM

## Engagement AI UI Placement and Modal Flow Specification – v1.1.0

**Feature:** AI-Assisted Engagement Transcript Summarization  
**Release:** v1.1.0 (Phase 8.1)  
**Baseline:** Production v1.0.3  
**Status:** Canon-bound specification

---

## 1. Purpose

This document defines the exact UI placement, affordances, and modal interaction flow for AI-assisted engagement transcript summarization in Ulysses CRM.

The objective is to ensure the feature feels:

* Intentional
* Predictable
* Non-intrusive
* Clearly subordinate to human judgment

---

## 2. Design Principles

The following principles are binding:

* AI actions must be user-initiated
* AI affordances must be visible but restrained
* AI output must never overwrite user content
* Saving AI output must require explicit confirmation
* Original user input must remain intact

---

## 3. Placement Within Engagement View

### 3.1 Location

The AI action is placed **within the Engagement detail view**, adjacent to the transcript or notes field.

Recommended placement:

* Secondary action button aligned with engagement tools
* Label: **“Summarize transcript”**

This placement reinforces that AI operates on *existing content* rather than generating new records.

---

### 3.2 Visibility Rules

* If global AI flag is disabled, the button is not rendered
* If user-level `ai_enabled` is false, the button is disabled or hidden
* A short inline message may appear: “AI assistance is off. Enable it in Settings.”

Backend enforcement applies regardless of UI state.

---

## 4. Interaction Flow

### 4.1 Button Click

When the user clicks **“Summarize transcript”**:

* Validate that engagement contains user-supplied text
* If empty, show inline error: “Add notes or a transcript to summarize.”
* If present, open the AI modal

---

## 5. AI Modal Specification

### 5.1 Modal Header

* Title: **“AI Transcript Summary”**
* Subtitle or helper text:

  * “This tool helps summarize your notes. Review before saving.”

---

### 5.2 Disclosure Section

Displayed at the top of the modal in subdued text:

* “AI assistance is optional and runs only when you click Generate.”
* “No tasks, emails, or decisions are created automatically.”
* “Review and edit results before saving.”

---

### 5.3 Action Controls

Initial state:

* Primary button: **“Generate summary”**
* Secondary button: Cancel

While processing:

* Disable all buttons
* Show spinner or progress indicator

---

### 5.4 Output Sections

Once generation completes, render **three clearly separated, editable sections**:

1. **One-Sentence Summary**

   * Editable text area
   * Single paragraph

2. **CRM Narrative Summary**

   * Editable multi-line text area
   * Default focus section

3. **Suggested Follow-Up Items**

   * Bullet list format
   * Editable
   * Label clearly as “Suggestions”

If no follow-ups are returned, display:

* “None identified.”

---

### 5.5 Editability Rules

* All AI-generated text is editable
* User may remove entire sections
* Original transcript is never modified

---

## 6. Save and Discard Behavior

### 6.1 Save Options

Primary action:

* **“Save to engagement”**

On save:

* Replace or populate the Engagement summary fields
* Preserve original transcript unchanged
* Log AI usage counters

---

### 6.2 Discard Options

Secondary actions:

* Cancel
* Close modal

On discard:

* No AI output is persisted
* No engagement fields are modified

---

## 7. Error States

The UI must handle and message the following conditions gracefully:

* AI disabled: “AI assistance is not enabled for your account.”
* Rate limit reached: “Daily AI usage limit reached.”
* Monthly cap reached: “Monthly AI usage limit reached.”
* Service error: “AI service is temporarily unavailable.”

No partial data should be saved in error cases.

---

## 8. Accessibility and Tone

* Avoid novelty language or playful AI metaphors
* Use professional, neutral wording
* Maintain visual hierarchy consistent with existing Engagement UI

AI should feel like a **quiet assistant**, not a feature spotlight.

---

## 9. Definition of Done

This specification is complete when:

* AI action is correctly placed in Engagement view
* Modal flow matches this document
* AI output is editable and non-destructive
* Save and discard paths behave as specified
* Error states are handled cleanly

---

## 10. Canon Statement

> *In Ulysses CRM, AI appears only where it serves clarity, never where it distracts or assumes authority.*
