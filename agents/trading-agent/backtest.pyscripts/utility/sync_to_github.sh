#!/bin/bash

# Script to sync local human-ai repo to GitHub every 2 hours
# Updates repo_tree.txt, adds all changes, commits and pushes

cd /home/yahwehatwork/human-ai

# Update the repository tree view
echo "Updating repository tree view..."
./scripts/utility/update_tree.sh

# Check if there are any changes
if ! git diff-index --quiet HEAD --; then
    echo "Changes detected. Staging all files..."
    git add -A
    
    # Create commit message with timestamp
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    COMMIT_MSG="Auto-sync: $TIMESTAMP"
    
    echo "Committing changes..."
    git commit -m "$COMMIT_MSG"
    
    echo "Pushing to GitHub..."
    git push origin main
    
    echo "Sync completed at $TIMESTAMP"
else
    echo "No changes detected. Skipping commit and push."
fi

# Log the sync attempt
echo "Sync attempt at $(date): $(if ! git diff-index --quiet HEAD --; then echo 'Changes synced'; else echo 'No changes'; fi)" >> /home/yahwehatwork/human-ai/sync_log.txt