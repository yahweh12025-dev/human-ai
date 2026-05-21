#!/usr/bin/env bash
# ============================================================
# compile_ea.sh — Compile an MQ5 EA via MetaEditor GUI automation
# CONFIRMED WORKING: MetaEditor opens, navigates to file, F7 compiles — 0 errors
# Usage:  bash ~/human-ai/scripts/compile_ea.sh [display_num] [ea_name]
#   display_num : X display number (default 11)
#   ea_name     : EA filename without extension (default MetalEA_v2)
#
# Requires: MT5 terminal running on display :11, xdotool, wmctrl
# ============================================================
set -euo pipefail

DISPLAY_NUM="${1:-11}"
EA_NAME="${2:-MetalEA_v2}"
export DISPLAY=":$DISPLAY_NUM"

MT5_DIR="/home/yahwehatwork/.wine/drive_c/Program Files/MetaTrader 5"
MQ5_PATH="$MT5_DIR/MQL5/Experts/${EA_NAME}.mq5"
EX5_PATH="$MT5_DIR/MQL5/Experts/${EA_NAME}.ex5"
WIN_MQ5_PATH="C:\\Program Files\\MetaTrader 5\\MQL5\\Experts\\${EA_NAME}.mq5"
LOG="$MT5_DIR/logs/metaeditor.log"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

# ── Checks ──────────────────────────────────────────────────
[ -f "$MQ5_PATH" ] || die ".mq5 not found at $MQ5_PATH"
command -v xdotool >/dev/null || die "xdotool not installed"
command -v wmctrl  >/dev/null || die "wmctrl not installed"

# ── Find MT5 window ──────────────────────────────────────────
MT5_WIN=$(wmctrl -l 2>/dev/null | grep -i "ICMarket\|MetaTrader\|52878487" | head -1 | awk '{print $1}')
if [ -z "$MT5_WIN" ]; then
    die "MT5 terminal window not found on display $DISPLAY. Is MT5 running?"
fi
log "MT5 window: $MT5_WIN"

# Remove stale .ex5 so we can detect fresh compile
rm -f "$EX5_PATH"

# ── Open MetaEditor (F4) ─────────────────────────────────────
log "Opening MetaEditor via F4..."
wmctrl -ia "$MT5_WIN"
sleep 0.8
xdotool windowfocus --sync "$MT5_WIN"
sleep 0.3
xdotool key --window "$MT5_WIN" F4
sleep 4

ME_WIN=$(wmctrl -l 2>/dev/null | grep "MetaEditor" | head -1 | awk '{print $1}')
[ -z "$ME_WIN" ] && die "MetaEditor window did not open"
log "MetaEditor window: $ME_WIN"

# ── Open MetalEA.mq5 (Ctrl+O) ───────────────────────────────
log "Opening ${EA_NAME}.mq5..."
wmctrl -ia "$ME_WIN"
sleep 0.5
xdotool windowfocus --sync "$ME_WIN"
sleep 0.3
xdotool key --window "$ME_WIN" ctrl+o
sleep 2

OPEN_WIN=$(wmctrl -l 2>/dev/null | grep " Open$" | head -1 | awk '{print $1}')
[ -z "$OPEN_WIN" ] && die "File open dialog did not appear"

wmctrl -ia "$OPEN_WIN"
sleep 0.3
xdotool windowfocus --sync "$OPEN_WIN"
sleep 0.2
xdotool key --window "$OPEN_WIN" ctrl+a
sleep 0.1
xdotool type --window "$OPEN_WIN" --clearmodifiers "$WIN_MQ5_PATH"
sleep 0.3
xdotool key --window "$OPEN_WIN" Return
sleep 2

# Verify dialog closed
if wmctrl -l 2>/dev/null | grep -q " Open$"; then
    die "File open dialog still open — path may be wrong"
fi
log "File opened successfully"

# ── Compile (F7) ─────────────────────────────────────────────
log "Compiling with F7..."
wmctrl -ia "$ME_WIN"
sleep 0.3
xdotool windowfocus --sync "$ME_WIN"
sleep 0.2
xdotool key --window "$ME_WIN" F7

# ── Wait for .ex5 ────────────────────────────────────────────
log "Waiting for ${EA_NAME}.ex5..."
for i in $(seq 1 30); do
    sleep 1
    if [ -f "$EX5_PATH" ]; then
        SIZE=$(stat -c%s "$EX5_PATH")
        log "SUCCESS: ${EA_NAME}.ex5 compiled in ${i}s (${SIZE} bytes)"
        # Show last compile log entry
        python3 -c "
data=open('$LOG','rb').read().decode('utf-16-le','replace')
lines=[l.strip() for l in data.split('\n') if '${EA_NAME}' in l or 'Compile' in l]
if lines: print('  Log: ' + lines[-1])
" 2>/dev/null || true
        break
    fi
    [ $((i % 5)) -eq 0 ] && log "  still waiting... ${i}s"
done

[ -f "$EX5_PATH" ] || die "Compile failed — ${EA_NAME}.ex5 not created after 30s. Check MT5 MetaEditor for errors."

# ── Close MetaEditor ─────────────────────────────────────────
log "Closing MetaEditor..."
xdotool key --window "$ME_WIN" alt+F4
sleep 1

log "Done. ${EA_NAME}.ex5 is ready."
