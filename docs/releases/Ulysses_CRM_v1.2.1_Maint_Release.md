# Ulysses CRM – v1.2.1 Maintenance Release

**Release Type:** Point Release  
**Version:** 1.2.1  
**Branch:** main  
**Scope:** UI Navigation Refinement + Environment Banner Positioning  

---

## Summary

v1.2.1 is a lightweight UI maintenance release focused on improving navigation clarity and environment safety signaling.

No database changes.  
No schema modifications.  
No behavioral changes to core business logic.  

---

## Changes

### 1. Navbar Simplification

- Reduced visual crowding in top navigation
- Introduced **“More”** dropdown for secondary items:
  - Templates
  - Calendar Feed
  - Admin (owner only)
- Moved Search to modal-trigger button
- Converted Account to right-aligned dropdown (Account + Logout)

Result:
Cleaner primary navigation and improved visual hierarchy.

---

### 2. Global Search Modal

- Replaced inline search field with modal-based search
- Added keyboard shortcuts:
  - `/`
  - `Ctrl + K` / `Cmd + K`
- Autofocus on open

No backend changes.

---

### 3. Environment Banner Position Fix

- Moved LOCAL DEVELOPMENT ENVIRONMENT banner above navbar
- Ensures environment visibility before any navigation interaction
- Production remains unaffected (`APP_ENV == "PROD"`)

---

## Deleted Artifact

- Removed malformed duplicate documentation path:
  - `docs/docs:phases:phase_9_ai_universal_search.md`
- Canonical Phase 9 documentation remains intact under:
  - `docs/phases/Ulysses_CRM_phase_9_ai_universal_search.md`

---

## Impact

- UI-only release
- No migrations
- No tenant model impact
- No API surface changes
- Safe deploy

---

## Status

Tagged: `v1.2.1`  
Production: Pending / Deployed (update as applicable)
