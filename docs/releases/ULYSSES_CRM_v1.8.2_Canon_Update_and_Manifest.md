# ULYSSES CRM -- Canon Update & Release Manifest

## Version 1.8.2

------------------------------------------------------------------------

# Canon Update Entry (For ULYSSES_CRM_CANON.md)

## v1.8.2 -- Login UX & Stability Hardening

Version 1.8.2 formalizes UI and routing stabilization following
dashboard restructuring work. This release strengthens login page
branding by integrating the shared background overlay system, adds
public-facing Privacy and Terms links for compliance visibility, updates
core branding assets, and restores stable dashboard routing behavior in
production. No schema changes, authentication logic modifications, or
data migrations were introduced. This release reinforces disciplined
version governance and maintains Ulysses CRM's production stability
standards.

------------------------------------------------------------------------

# Formal Release Manifest -- v1.8.2

**Release Version:** 1.8.2\
**Release Type:** Point Release\
**Environment Target:** Production\
**Schema Changes:** None\
**Migrations Required:** No\
**Backward Compatibility Impact:** None

------------------------------------------------------------------------

## Included Changes

### UI / UX

-   Branded login background integration using `app-bg` overlay system
-   Refined login typography and layout polish
-   Legal page links added to login page
-   Minor spacing and visual consistency improvements

### Routing

-   Dashboard routing stabilized
-   `/dashboard` compatibility route verified
-   Production 404 regression resolved

### Branding

-   Updated `ulysses-logo.svg`
-   Ensured consistent background styling across login and app

### Governance

-   Version bump to 1.8.2
-   Reinforced structured release tagging
-   Version surfaced via context processor

------------------------------------------------------------------------

## Deployment Checklist

-   [x] version.py updated to 1.8.2\
-   [x] Commit created with structured release message\
-   [x] Git tag created: v1.8.2\
-   [x] Production deployment verified\
-   [x] Login page tested (background, overlay, logo, legal links)\
-   [x] Privacy and Terms routes verified public (HTTP 200)

------------------------------------------------------------------------

## Risk Profile

Low risk release.

-   No database changes\
-   No migration scripts\
-   No dependency updates\
-   No environment configuration changes

------------------------------------------------------------------------

## Rollback Strategy

If rollback required:

1.  Revert to previous git tag (v1.8.1 or prior stable tag)
2.  Redeploy application
3.  No database rollback necessary

------------------------------------------------------------------------

## Status

✅ Production Stable\
✅ Tagged\
✅ Documented

------------------------------------------------------------------------

End of Manifest -- v1.8.2
