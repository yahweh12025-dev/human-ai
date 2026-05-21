#!/bin/bash
# Backup self-hosted Supabase to Google Drive
# Run via cron: 0 */6 * * * /home/yahwehatwork/human-ai/scripts/backup_supabase_to_gdrive.sh

BACKUP_DIR="/home/yahwehatwork/gdrive/backups/supabase"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/human_ai_db_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

# Dump database
docker exec supabase-selfhosted-db-1 pg_dump -U postgres human_ai | gzip > "$BACKUP_FILE" 2>/dev/null

if [ $? -eq 0 ] && [ -f "$BACKUP_FILE" ]; then
    echo "$(date): Backup successful → $BACKUP_FILE ($(du -h $BACKUP_FILE | cut -f1))"
    # Keep only last 30 backups
    ls -t "$BACKUP_DIR"/human_ai_db_*.sql.gz | tail -n +31 | xargs rm -f 2>/dev/null
else
    echo "$(date): Backup FAILED - is Supabase running?"
    # Fallback: backup unified_tasks.json and logs
    cp /home/yahwehatwork/human-ai/unified_tasks.json "$BACKUP_DIR/unified_tasks_$TIMESTAMP.json"
fi
