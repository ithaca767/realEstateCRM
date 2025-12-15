#!/bin/bash

echo "🧹 Resetting local environment..."

deactivate 2>/dev/null
rm -rf venv

echo "✅ Virtual environment removed"
echo "➡️  Run ./setup_local.sh to rebuild"

