#!/bin/bash
# Quick EA attachment & status checker

STATUS_FILE="/home/yahwehatwork/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/mt5_status.json"
SIGNAL_FILE="/home/yahwehatwork/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/python_signal.json"

echo "════════════════════════════════════════════════════════════"
echo "MetalEA_v3 Status Checker"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if MT5 is running
if ps aux | grep -q "terminal64.exe"; then
    echo "[✓] MT5 terminal is RUNNING"
else
    echo "[✗] MT5 terminal NOT running"
    exit 1
fi

# Check if status file exists and has data
if [ -f "$STATUS_FILE" ]; then
    SIZE=$(stat -c%s "$STATUS_FILE" 2>/dev/null)
    MTIME=$(stat -c%y "$STATUS_FILE" 2>/dev/null | cut -d. -f1)
    
    if [ "$SIZE" -gt 50 ]; then
        echo "[✓] MetalEA_v3 is ATTACHED and SENDING DATA"
        echo "    File size: $SIZE bytes"
        echo "    Last update: $MTIME"
        echo ""
        echo "=== Current Status ==="
        cat "$STATUS_FILE" | python3 -m json.tool 2>/dev/null || cat "$STATUS_FILE"
        echo ""
        echo "[✓✓✓] EA IS LIVE AND READY!"
    else
        echo "[✗] Status file empty ($SIZE bytes)"
        echo "    MetalEA_v3 may not be attached yet"
        echo "    Last update: $MTIME"
    fi
else
    echo "[✗] Status file not found"
    echo "    MetalEA_v3 not attached to chart"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
