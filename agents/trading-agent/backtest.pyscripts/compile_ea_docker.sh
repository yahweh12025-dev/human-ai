#!/bin/bash
# ════════════════════════════════════════════════════════════════════════════
# compile_ea_docker.sh — Compile MQ5 EA inside Docker container (headless)
# ════════════════════════════════════════════════════════════════════════════
# Usage: bash ./compile_ea_docker.sh <container_name> <ea_name> [timeout]
# Example: bash ./compile_ea_docker.sh mt5_autonomous_node MetalEA_v3 120
# ════════════════════════════════════════════════════════════════════════════

set -euo pipefail

CONTAINER_NAME="${1:-mt5_autonomous_node}"
EA_NAME="${2:-MetalEA_v3}"
TIMEOUT="${3:-120}"

# Container paths
CONTAINER_EXPERTS_DIR="/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts"
CONTAINER_METAEDITOR="/config/.wine/drive_c/Program Files/MetaTrader 5/metaeditor64.exe"
CONTAINER_LOG="/config/MetaEditor_compile.log"
WIN_MQ5_PATH="C:\\\\Program Files\\\\MetaTrader 5\\\\MQL5\\\\Experts\\\\${EA_NAME}.mq5"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

# ────────────────────────────────────────────────────────────────────────────
# Checks
# ────────────────────────────────────────────────────────────────────────────

log "Container: $CONTAINER_NAME"
log "EA Name: $EA_NAME"
log "Timeout: ${TIMEOUT}s"

# Verify container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    die "Container '$CONTAINER_NAME' not running"
fi
log "✓ Container running"

# Verify .mq5 file exists in container
rc=$(docker exec "$CONTAINER_NAME" test -f "$CONTAINER_EXPERTS_DIR/$EA_NAME.mq5" && echo 0 || echo 1)
if [ "$rc" != "0" ]; then
    die ".mq5 not found: $CONTAINER_EXPERTS_DIR/$EA_NAME.mq5"
fi
log "✓ MQ5 file exists"

# ────────────────────────────────────────────────────────────────────────────
# Remove stale .ex5
# ────────────────────────────────────────────────────────────────────────────

log "Removing stale .ex5 if present..."
docker exec "$CONTAINER_NAME" rm -f "$CONTAINER_EXPERTS_DIR/$EA_NAME.ex5" 2>/dev/null || true

# ────────────────────────────────────────────────────────────────────────────
# Compile via Wine/MetaEditor (headless)
# ────────────────────────────────────────────────────────────────────────────

log "Compiling $EA_NAME.mq5 via Wine/MetaEditor (headless)..."

COMPILE_CMD="wine \"$CONTAINER_METAEDITOR\" /compile:\"$WIN_MQ5_PATH\" /log:\"$CONTAINER_LOG\""

# Execute with timeout
timeout "$TIMEOUT" docker exec -u 911 "$CONTAINER_NAME" \
    bash -c "$COMPILE_CMD" 2>&1 | head -50 || {
    RC=$?
    if [ $RC -eq 124 ]; then
        log "Compilation timed out after ${TIMEOUT}s (this is normal if compiling in background)"
    fi
}

log "Compilation process initiated"

# ────────────────────────────────────────────────────────────────────────────
# Wait for .ex5 file to appear
# ────────────────────────────────────────────────────────────────────────────

log "Waiting for ${EA_NAME}.ex5 (max ${TIMEOUT}s)..."

DEADLINE=$((SECONDS + TIMEOUT))
while [ $SECONDS -lt $DEADLINE ]; do
    if docker exec "$CONTAINER_NAME" test -f "$CONTAINER_EXPERTS_DIR/$EA_NAME.ex5" 2>/dev/null; then
        SIZE=$(docker exec "$CONTAINER_NAME" stat -c%s "$CONTAINER_EXPERTS_DIR/$EA_NAME.ex5" 2>/dev/null || echo "?")
        log "✓ SUCCESS: ${EA_NAME}.ex5 compiled (${SIZE} bytes)"
        
        # Show compile log snippet if available
        log "Attempting to read compile log..."
        docker exec "$CONTAINER_NAME" tail -10 "$CONTAINER_LOG" 2>/dev/null | grep -i "error\|warning\|success" | head -3 || true
        
        exit 0
    fi
    
    sleep 2
done

log "✗ Timeout: ${EA_NAME}.ex5 not created within ${TIMEOUT}s"
log "Checking compilation log for errors..."
docker exec "$CONTAINER_NAME" cat "$CONTAINER_LOG" 2>/dev/null | tail -20 || echo "(log not available)"

exit 1
