# Ulysses CRM UI Consistency Checklist
# Phase 4.5
# Last updated: 2025-12-28

## Purpose

This document defines UI consistency standards for Ulysses CRM.
All UI work in Phase 4.5 and beyond must follow this checklist to prevent drift and rework.

## 1. Page Layout Rules

### Container rules
- Do not add a `.container` wrapper inside templates if `base.html` already provides the container or panel structure
- Pages should begin with a page header block, followed by content cards

### Page header pattern
- Title line: `h2.mb-0`
- Descriptor line: `div.text-muted` or `div.text-muted.small`

```html
<div class="d-flex justify-content-between align-items-center mb-3">
  <div>
    <h2 class="mb-0">Page Title</h2>
    <div class="text-muted">Optional descriptor line</div>
  </div>
</div>
```

### Primary content structure
- `.card.mt-3`
- `.card-body`
- Page content

Avoid nested cards unless they represent a real sub-section.

## 2. Cards and Spacing Rules

### Card baseline
- Use `.card.mt-3` for the first major content block
- Use `.card-body` for padding
- Do not nest `.card-body` inside another `.card-body`

### Sub-section cards
- Use internal cards only when splitting a page into meaningful sections
- Section headers should be structural, not alert-like

### Card header styling
- `bg-danger-subtle text-dark`
- `bg-warning-subtle text-dark`
- `bg-success-subtle text-dark`
- `bg-primary-subtle text-dark`

Avoid full-strength alert headers such as `bg-danger text-white`.

```html
<div class="card-header bg-success-subtle text-dark fw-semibold">
  Section Title
</div>
```

## 3. Tables

### Table base style
- `table table-sm table-striped mb-0 align-middle`
- Wrap in `.table-responsive` when needed
- Use `thead.table-light` for headers

### Actions column
- Use `btn btn-sm btn-outline-primary`
- Apply width hints only when necessary

### Links in tables
- Default to standard link styling
- Use `text-decoration-none` only when clarity improves

## 4. Tabs

### Placement
- Tabs live inside a card header row or equivalent
- Use Bootstrap tabs consistently

### Behavior
- Default active tab matches page purpose
- URL hash navigation always takes priority
- If `tx_id` is present, force Transactions tab open

### Hash mapping
- `#details`
- `#engagements`
- `#followups`
- `#transactions`

## 5. Dashboard Metric Cards

### Visual language
- Cards remain neutral
- Meaning conveyed via left borders
- Numbers remain black

### Border standards
- Overdue: `border-start border-2 border-danger`
- Upcoming: `border-start border-2 border-warning`
- Active: `border-start border-2 border-success`
- Total: `border-start border-2 border-primary`

```html
<div class="card text-center h-100 border-start border-2 border-success">
  <div class="card-body">
    <div class="text-muted small">Active Contacts</div>
    <div class="fs-4 fw-bold text-dark">{{ active_contacts|length }}</div>
  </div>
</div>
```

## 6. Transactions UI Standards

### Split view
- Left pane is a selector only
- Columns: Address, Type, Status, Select
- No Open column

### Right pane
- Primary detail view
- View / Edit action lives here
- New fields added here first

### Selection
- Selected row visually distinct
- Left border accent preferred

## 7. Engagements UI Standards

### Form layout
- `row g-3 align-items-end`
- Transcript and summary collapsed by default

### Log presentation
- Columns: When, Type, Details, Actions
- Use View / Edit label consistently

## 8. Follow-ups UI Standards

### Placement
- Follow-ups are first-class on Dashboard
- Avoid separate follow-up dashboard pages

### Styling
- Subtle semantic headers
- Match dashboard table styling

## 9. Scripts and JavaScript

### Placement
- Scripts at bottom of templates is acceptable
- Consistency over exact placement

### DOM readiness
- Tab and hash logic must run after DOMContentLoaded

## 10. Global Indicators

### Footer
- Display `Ulysses CRM v{{ APP_VERSION }}`
- Explicit environment indicator: LOCAL or PROD

## 11. Pre-Commit UI Checklist

- No duplicate `.container` wrappers
- Page header uses title plus muted descriptor
- First content block is `.card.mt-3`
- No nested `.card-body`
- Tables use standard classes
- Tabs support hash navigation
- Action labels are consistent
- No em dashes in UI text
