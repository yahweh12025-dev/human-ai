#!/usr/bin/env bash
# Mount Google Drive via rclone FUSE
# Run at login or via cron: @reboot /home/yahwehatwork/human-ai/scripts/system/mount_gdrive.sh

MOUNT_POINT="$HOME/gdrive"
LOG="/tmp/rclone-gdrive.log"

mkdir -p "$MOUNT_POINT"

if mount | grep -q "rclone.*$MOUNT_POINT"; then
    echo "gdrive already mounted at $MOUNT_POINT"
    exit 0
fi

rclone mount gdrive: "$MOUNT_POINT" \
    --vfs-cache-mode writes \
    --daemon \
    --log-file "$LOG"

sleep 2
if mount | grep -q "rclone.*$MOUNT_POINT"; then
    echo "gdrive mounted at $MOUNT_POINT"
else
    echo "ERROR: gdrive mount failed — check $LOG"
    exit 1
fi
