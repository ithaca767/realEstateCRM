#!/bin/bash

set -u

cd "$(dirname "$0")" || exit 1

echo
echo "============================================================"
echo " ULYSSES CRM - DEVELOPMENT RESUME"
echo "============================================================"

echo
echo "===== REPOSITORY ====="
printf "Branch:      "
git branch --show-current

printf "Commit:      "
git rev-parse --short HEAD

printf "Origin:      "
git rev-parse --short origin/main 2>/dev/null || echo "unavailable"

if git diff --quiet && git diff --cached --quiet; then
    if [ -z "$(git ls-files --others --exclude-standard)" ]; then
        echo "Working tree: CLEAN"
    else
        echo "Working tree: DIRTY - untracked files present"
    fi
else
    echo "Working tree: DIRTY - tracked changes present"
fi

LOCAL_HEAD="$(git rev-parse HEAD 2>/dev/null)"
ORIGIN_HEAD="$(git rev-parse origin/main 2>/dev/null || true)"

if [ -n "$ORIGIN_HEAD" ]; then
    if [ "$LOCAL_HEAD" = "$ORIGIN_HEAD" ]; then
        echo "Origin status: UP TO DATE"
    else
        AHEAD="$(git rev-list --count origin/main..HEAD 2>/dev/null || echo "?")"
        BEHIND="$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "?")"
        echo "Origin status: ahead $AHEAD / behind $BEHIND"
    fi
else
    echo "Origin status: UNKNOWN"
fi

echo
echo "===== APPLICATION ====="

if [ -f version.py ]; then
    grep -E '^(APP_VERSION|TERMS_VERSION)[[:space:]]*=' version.py || true
else
    echo "version.py not found"
fi

echo
echo "===== ENVIRONMENT ====="

if [ -n "${VIRTUAL_ENV:-}" ]; then
    echo "Virtualenv:  ACTIVE"
    echo "Path:        $VIRTUAL_ENV"
else
    echo "Virtualenv:  NOT ACTIVE"
fi

printf "Python:      "
python3 --version 2>/dev/null || echo "unavailable"

if [ -f .env ]; then
    echo ".env:        PRESENT"
else
    echo ".env:        MISSING"
fi

echo
echo "===== RECENT COMMITS ====="
git log -5 --oneline

echo
echo "===== PROJECT STATE ====="

if [ -f PROJECT_STATE.md ]; then
    sed -n '/## RESUME HERE/,$p' PROJECT_STATE.md
else
    echo "PROJECT_STATE.md not found"
fi

echo
echo "============================================================"
echo " END ULYSSES RESUME"
echo "============================================================"
echo
