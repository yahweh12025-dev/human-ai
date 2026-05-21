#!/bin/bash
# Auto-push script for Hermes agent - safe version that avoids leaking secrets
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] Starting auto-push check"

# Ensure we are on a branch we can push to (usually main or master)
# Optionally fetch latest to avoid divergent branch issues
git fetch origin --quiet

# Update tracked files only (safe because .env, personal_template/ etc. are ignored)
git add -u

# Check if there are any changes to commit
if ! git diff-index --quiet HEAD --; then
    TIMESTAMP=$(date -u +'%Y-%m-%d_%H-%M-%S')
    git commit -m "auto update" || echo "Commit failed (maybe no changes?)"
    # Push to origin (assuming main branch; adjust if needed)
    git push origin HEAD --quiet
    echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] Push completed"
else
    echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] No changes to push"
fi
