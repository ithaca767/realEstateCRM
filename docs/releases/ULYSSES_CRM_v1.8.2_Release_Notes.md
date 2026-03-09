# Ulysses CRM -- Release Notes

## v1.8.2 -- Login UX & Stability Hardening Release

**Release Type:** Point Release\
**Focus:** UI polish, routing stabilization, legal visibility
compliance, branding refinement

------------------------------------------------------------------------

## Summary

Version 1.8.2 formalizes improvements to the login experience and
resolves production routing instability introduced during dashboard
restructuring. This release enhances visual consistency, strengthens
legal page discoverability for compliance purposes, and reinforces
disciplined version governance.

------------------------------------------------------------------------

## Improvements

### Login Experience

-   Integrated branded background using existing `app-bg` overlay system
-   Added Ulysses logo to login header
-   Refined typography and spacing for improved SaaS polish
-   Added visible links to:
    -   `/privacy`
    -   `/terms`
-   Ensured login page remains clean, focused, and production-safe

### Legal Visibility

-   Confirmed `/privacy` and `/terms` routes are publicly accessible
-   Linked legal pages directly from login for crawler compliance
-   Strengthened Google OAuth / SaaS verification readiness

### Routing Stabilization

-   Restored stable dashboard routing
-   Ensured `/dashboard` compatibility behavior remains intact
-   Prevented production 404 regression during redirect flow

### Branding

-   Updated `ulysses-logo.svg`
-   Ensured consistent background integration across app and login

### Version Governance

-   Version surfaced via global context processor
-   Reinforced structured release discipline
-   Tagged and versioned as v1.8.2

------------------------------------------------------------------------

## Technical Scope

-   No database changes
-   No schema migrations
-   No authentication logic changes
-   No API changes
-   UI / presentation layer improvements only

------------------------------------------------------------------------

## Production Impact

-   Zero downtime expected
-   Zero migration risk
-   Zero backward compatibility impact

------------------------------------------------------------------------

## Status

✅ Stable\
✅ Production verified\
✅ Tagged as v1.8.2

------------------------------------------------------------------------

Ulysses CRM continues evolving as a disciplined, versioned SaaS product
with structured governance and production-grade stability.
