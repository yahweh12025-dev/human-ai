#!/bin/bash
# guicompiler.sh — Automate MetaEditor GUI compilation via xdotool
# Usage: ./guicompiler.sh [file.mq5]
#   If no file given, compiles MasterMetalsEA.mq5

DISPLAY="${DISPLAY:-:11.0}"
WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"
MT5_DIR="C:\\Program Files\\MetaTrader 5"
MQL5_EXPERTS="$HOME/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts"

FILE="${1:-MasterMetalsEA.mq5}"
BASENAME="${FILE%.mq5}"
SRC="$MQL5_EXPERTS/$FILE"
EX5="$MQL5_EXPERTS/${BASENAME}.ex5"

# Ensure source exists in MT5 Experts dir
if [ ! -f "$SRC" ]; then
    PROJECT_SRC="$(dirname "$0")/$FILE"
    if [ -f "$PROJECT_SRC" ]; then
        cp "$PROJECT_SRC" "$SRC"
    else
        echo "Error: $FILE not found in $MQL5_EXPERTS or $(dirname "$0")"
        exit 1
    fi
fi

rm -f "$EX5"

env WINEPREFIX="$WINEPREFIX" wine "$MT5_DIR\\MetaEditor64.exe" "$MT5_DIR\\MQL5\\Experts\\$FILE" &
ME_PID=$!

for i in $(seq 1 30); do
    sleep 1
    WID=$(xdotool search --name "MetaEditor" 2>/dev/null | head -1)
    [ -n "$WID" ] && break
done

if [ -z "$WID" ]; then
    echo "Error: MetaEditor window did not appear"
    exit 1
fi

xdotool windowactivate "$WID"
sleep 2
xdotool key F7
sleep 8

if [ -f "$EX5" ]; then
    echo "SUCCESS: ${BASENAME}.ex5 ($(stat -c%s "$EX5") bytes)"
else
    echo "WARNING: .ex5 not generated — check for compilation errors"
fi

xdotool key --window "$WID" Alt+F4
sleep 2
kill "$ME_PID" 2>/dev/null
