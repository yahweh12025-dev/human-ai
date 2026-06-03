# MetalCryptoEAv5 — Autonomous MT5 Trading EA

## Overview

MetalCryptoEAv5 is an MQL5 Expert Advisor for MetaTrader 5 that trades BTCUSD, XAUUSD, and XAGUSD. It runs inside a Docker container (`mt5_autonomous_node`) with KasmVNC for visual access, nginx reverse proxy, and a Python companion agent for signal generation.

## Key Changes from v4 → v5

| Feature | v4 | v5 |
|---------|----|----|
| MagicNumber | 123456 | 123457 |
| Version | 4.01 | 5.00 |
| Trailing Stop | Generic 0.8×ATR (all symbols) | Symbol-aware multipliers (XAU:0.5, XAG:0.6, BTC:0.8) |
| Hard Stop Loss | `InpMaxDollarRisk` (entry cap only) | `InpHardSL_USD` (entry cap + runtime force-close) |
| Loss Tracking | None | Consecutive loss tracking (MAX_CONSECUTIVE_LOSSES=3) |
| Python Agent | 333 lines (v1, basic) | 427 lines (v2, with loss halt mechanism) |

## Container Info

- **Container**: `mt5_autonomous_node` (running)
- **Wine prefix**: `/config/.wine` (owned by `abc:abc`, UID 911)
- **MT5 terminal**: terminal64.exe (PID 364, started with `/config/startup.ini`)
- **Status file**: `/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/mt5_status.json` (UTF-16 LE)
- **Signal file**: `/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/python_signal.json`

## Account Status

- **Account**: 52878487 (LIVE)
- **Balance**: $3,872.95
- **Equity**: $3,861.33
- **Open positions**: 1 XAUUSD SELL 0.02 @ 4500.32 (-$11.62)

## Services

| Service | Port | Status | Notes |
|---------|------|--------|-------|
| nginx (HTTP) | 3000 | ✅ | Proxies to KasmVNC, auth_basic disabled |
| nginx (HTTPS) | 3001 | ✅ | SSL, same proxy target |
| KasmVNC (HTTP) | 6900 | ✅ | `-disableBasicAuth -SecurityTypes None` |
| KasmVNC (WebSocket) | 6901 | ✅ | VNC WebSocket connection |
| mt5linux (RPC) | 8001 | ❌ | `-w` flag syntax error in startup; not needed by v2 agent |

## EA Files (inside Docker)

```
/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts/
├── MetalCryptoEAv4.mq5  (14,204 bytes) — source
├── MetalCryptoEAv4.ex5  (51,142 bytes) — compiled
├── MetalCryptoEAv5.mq5  (19,079 bytes) — source
└── MetalCryptoEAv5.ex5  (53,392 bytes) — compiled
```

## Compilation

The compile script at `/config/compile_ea_internal.sh` compiles the EA using `MetaEditor64.exe` under Wine:

```bash
export WINEPREFIX=/config/.wine
export DISPLAY=:1
EA_NAME="MetalCryptoEAv5"
# ... runs MetaEditor64.exe with /compile flag
```

**Must run as `abc` user** (not root). Use: `docker exec mt5_autonomous_node su abc -c "bash /config/compile_ea_internal.sh"`

## Python Agent

The v2 agent at `/config/mt5_agent_standalone.py` (427 lines) reads `mt5_status.json` and generates signals to `python_signal.json`. Features:

- UTF-16 LE status file parsing (handles BOM)
- Consecutive loss tracking with trading halt after 3 losses
- RSI + EMA regime filter for entry signals
- Symbol-aware SL/TP calculation
- Weekend session filter for metals

## VNC Access

URL: `http://localhost:3000` (or `https://localhost:3001`)

**History**: nginx auth_basic was initially blocking access (returned 401). Disabled by commenting out auth_basic directives in `/etc/nginx/sites-enabled/default` on 2026-06-02. KasmVNC handles its own authentication.

## Startup Sequence

1. Container starts → s6-overlay runs init scripts
2. KasmVNC starts on port 6900/6901
3. nginx starts on port 3000/3001 (proxies to KasmVNC)
4. MT5 terminal64.exe starts with `/config/startup.ini`
5. startup.ini attaches MetalCryptoEAv5 to BTCUSD M5 chart
6. Python agent reads status.json and generates signals

## Commit History

- `MetalCryptoEAv5` MagicNumber: `123457`
- v4 EA continues to run on container boot until v5 deployment

## Files Changed

| File | Path | Change |
|------|------|--------|
| MetalCryptoEAv5.mq5 | Experts/ | New file (v5 source) |
| startup.ini | /config/ | Updated Expert=MetalCryptoEAv5 |
| compile_ea_internal.sh | /config/ | Updated EA_NAME to MetalCryptoEAv5 |
| mt5_agent_standalone.py | /config/ | Upgraded to v2 (427 lines) |
| default (nginx) | /etc/nginx/sites-enabled/ | Disabled auth_basic |
