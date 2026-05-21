#!/usr/bin/env bash
# Start MT5 terminal in workspace 2 headlessly
export DISPLAY="${1:-:10}"
MT5_DIR="$HOME/.wine/drive_c/Program Files/MetaTrader 5"

# Kill any stale instance
pkill -f terminal64 2>/dev/null
sleep 2

# Start Xvfb if not running
if ! pgrep -f "Xvfb $DISPLAY" >/dev/null; then
    Xvfb $DISPLAY -screen 0 1280x1024x24 -ac &>/dev/null &
    sleep 1
fi

# Start MT5
wine "$MT5_DIR/terminal64.exe" /portable &>/dev/null &
MT5_PID=$!

# Wait for window, then move to workspace 2
for i in $(seq 1 30); do
    MT5_WIN=$(wmctrl -l 2>/dev/null | grep -E "52878487|MetaTrader" | head -1 | awk '{print $1}')
    if [ -n "$MT5_WIN" ]; then
        wmctrl -i -r "$MT5_WIN" -t 1
        echo "[MT5] Window $MT5_WIN moved to workspace 2 (PID $MT5_PID)"
        break
    fi
    sleep 2
done
echo "[MT5] Started on display $DISPLAY"
