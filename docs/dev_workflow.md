# Ulysses CRM Development Workflow

This document defines the **single source of truth workflow** for developing Ulysses CRM. Its purpose is to prevent file-state confusion, accidental deletions, and branch drift when working across sessions and devices.

---

## Core Principle

**We trust the repo, not memory and not chat history.**

All decisions are anchored to the current state of the Git repository.

---

## Session Start Checklist (Required)

At the beginning of any Ulysses CRM development session, run:

```bash
git status
git branch
```

Or, if available:

```bash
crmstate
```

Paste the output into the chat. This establishes ground truth for:
- Active branch
- Clean or dirty working tree
- Other existing branches

Until this output changes, it is treated as authoritative.

---

## Checkpoint Rule (Non‑Negotiable)

Before any of the following actions:
- Deleting a file
- Moving a file
- Refactoring routes or models
- Renaming templates

You must create a checkpoint commit:

```bash
git add -A
git commit -m "Checkpoint before <brief description>"
```

This makes all changes reversible and removes risk.

---

## File Architecture Rule

At any given time, **routes live in exactly one place**:

- Either inside `app.py`
- Or inside a dedicated module (e.g. `routes/engagements.py`)

Never mix both approaches in the same phase of development.

If architecture changes, it must be explicit and documented in-chat.

---

## Files Changed Declaration

Any time files are added, edited, or deleted during a session, paste this block:

```text
FILES CHANGED:
- added:
- edited:
- deleted:
BRANCH:
```

This anchors conversation state to repo reality.

---

## Repo Reality Check (When Files Are Involved)

When there is any uncertainty about what exists, run and paste one of the following:

```bash
git status
ls -la
```

For deeper checks:

```bash
find . -maxdepth 2 -type f | sort
```

Chat memory must always yield to filesystem output.

---

## Experiments and Scratch Work

Temporary or experimental files must live outside production paths.

Recommended:
- Use a `scratch/` directory
- Add it to `.gitignore`

Rule: **no experiments inside active route or template folders**.

---

## Branch Discipline

- Development happens on one branch at a time
- Branch changes must be explicitly stated
- Deploy targets must match the active branch

If branch changes, rerun `crmstate` and paste output.

---

## Responsibility Split

**Developer (Dennis):**
- Paste objective repo output when asked
- Run checkpoint commits before destructive actions

**Assistant (ChatGPT):**
- Track branch and file state once anchored
- Refer only to confirmed files and paths
- Stop destructive actions without checkpoints

---

## Golden Rule

If something feels unclear:

**Stop. Check the repo. Paste output. Then proceed.**

This workflow is designed to eliminate drift, confusion, and rework while keeping development fast and safe.

