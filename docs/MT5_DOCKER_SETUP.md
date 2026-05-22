# MetalEA_v3 Containerized Trading System

Complete guide to running the autonomous MT5 EA trading system inside Docker.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Host System                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  /home/yahwehatwork/mt5_node/                        │   │
│  │  ├─ docker-compose.yaml                             │   │
│  │  ├─ deploy_and_test.sh (compile pipeline test)      │   │
│  │  └─ trading_workspace/ (volume mount)               │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│           (Docker volume mount)                              │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ~/human-ai/                                         │   │
│  │  ├─ liveea_docker.py (launcher with Docker support) │   │
│  │  ├─ scripts/compile_ea_docker.sh (headless compile) │   │
│  │  └─ agents/trading-agent/                           │   │
│  │     ├─ mq5/MetalEA_v3.mq5 (EA source)              │   │
│  │     └─ live_trading_ea.py (main trading loop)       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                             │
                    (docker cp, docker exec)
                             │
            ┌────────────────▼─────────────────┐
            │   Docker Container               │
            │   mt5_autonomous_node            │
            │                                  │
            │  /config/.wine/drive_c/          │
            │  └─ Program Files/MetaTrader 5/  │
            │     ├─ metaeditor64.exe (compiler)
            │     ├─ terminal64.exe (MT5 trading)
            │     └─ MQL5/                     │
            │        ├─ Experts/               │
            │        │  ├─ MetalEA_v3.mq5     │
            │        │  └─ MetalEA_v3.ex5     │
            │        └─ Files/                 │
            │           ├─ python_signal.json  │
            │           ├─ python_result.json  │
            │           └─ mt5_status.json     │
            └─────────────────────────────────┘
```

## Setup Steps

### Step 1: Verify Docker Container is Running

```bash
cd ~/mt5_node
docker-compose up -d
docker ps | grep mt5_autonomous_node
```

Expected output:
```
...  mt5_autonomous_node  ...  Up X minutes  0.0.0.0:3000->3000/tcp
```

### Step 2: Test the Compile Pipeline

```bash
cd ~/mt5_node
./deploy_and_test.sh
```

This will:
- Create a test EA file
- Compile it headlessly
- Verify the output binary

Expected output:
```
✓ SUCCESS! Compiled binary created:
-rw-r--r-- 1 abc abc 5.7K May 22 07:41 /config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts/PipelineTestEA.ex5
```

### Step 3: Launch MetalEA_v3

```bash
python3 ~/human-ai/liveea_docker.py
```

The launcher will:

1. **PHASE 0** - Preflight checks
   - Verifies container is running
   - Checks EA source exists

2. **PHASE 1** - Deploy EA
   - Copies `MetalEA_v3.mq5` to container's Experts folder

3. **PHASE 2** - Compile EA (headless)
   - Runs `wine metaeditor64.exe /compile:...` inside container
   - Generates `MetalEA_v3.ex5`

4. **PHASE 3** - Manual MT5 Attachment
   - Opens http://localhost:3000 in your browser
   - Login: `trader` / `SecureTradePassword2026!`
   - In MT5 Navigator:
     1. Press `Ctrl+N` to open Navigator
     2. Find "Expert Advisors" → "MetalEA_v3"
     3. Double-click to attach to XAUUSD chart
     4. Accept EA properties dialog
     5. Enable AutoTrading (green button on toolbar)

5. **PHASE 4** - Test Trade
   - Sends a TEST_BUY signal to verify execution
   - Auto-closes after 60 seconds
   - Confirms bidirectional communication works

6. **MAIN LOOP** - Live Trading
   - Python trading loop starts
   - Sends signals via `python_signal.json`
   - Monitors MT5 status via `mt5_status.json`

## File Communication Protocol

### Python → MT5 Signals

**File**: `/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/python_signal.json`

**Format**:
```json
{
  "id": "sig_20260522_123456",
  "action": "BUY|SELL|CLOSE_POSITION|CLOSE_ALL",
  "symbol": "XAUUSD",
  "lot": 0.01,
  "sl": 2380.50,
  "tp": 2390.00,
  "timestamp": "2026-05-22T07:45:32Z"
}
```

### MT5 → Python Results

**File**: `/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/python_result.json`

**Format**:
```json
{
  "sig_id": "sig_20260522_123456",
  "success": true,
  "ts": "2026-05-22 07:45:35",
  "action": "BUY"
}
```

### MT5 Status (Monitored by Python)

**File**: `/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/mt5_status.json`

**Format**:
```json
{
  "account": 12345678,
  "balance": 5000.00,
  "equity": 5150.50,
  "xauusd_bid": 2385.30,
  "xagusd_bid": 29.45,
  "open_positions": 2,
  "last_signal_id": "sig_20260522_123456",
  "timestamp": "2026-05-22 07:45:32"
}
```

## Logs and Monitoring

### Log Files

```
~/human-ai/data/logs/
├─ liveea_docker.log        # Launcher phase logs
├─ liveea_nohup.log         # Background execution logs
└─ (other application logs)
```

### Obsidian Vault (Markdown Notes)

```
~/human-ai/data/obsidian/trades/
├─ 2026-05-22-ea_launch.md  # Launch events
├─ 2026-05-22-ea_trade.md   # Trade confirmations
└─ 2026-05-22-ea_stop.md    # Stop events
```

### Container Logs

```bash
docker logs -f mt5_autonomous_node | tail -100
```

### Inside Container

```bash
docker exec mt5_autonomous_node cat /config/MetaEditor_compile.log
docker exec mt5_autonomous_node cat /config/.wine/drive_c/Program\ Files/MetaTrader\ 5/logs/20260522.log
```

## Troubleshooting

### Compilation Fails

1. Check container is running: `docker ps | grep mt5_autonomous_node`
2. Verify Wine is functional: `docker exec mt5_autonomous_node wine --version`
3. Check MetaEditor exists: `docker exec mt5_autonomous_node test -f "/config/.wine/drive_c/Program Files/MetaTrader 5/metaeditor64.exe" && echo "Found" || echo "Not found"`
4. Review compile log: `docker exec mt5_autonomous_node tail -50 /config/MetaEditor_compile.log`

### EA Not Attaching

1. Verify EA compiled: `docker exec mt5_autonomous_node ls -lh "/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts/MetalEA_v3.ex5"`
2. Check MT5 in browser: http://localhost:3000
3. Manually attach: Navigator → Expert Advisors → MetalEA_v3 → Double-click
4. Enable AutoTrading (green button)

### No Price Updates

1. Check mt5_status.json is being written: `docker exec mt5_autonomous_node ls -lh "/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/mt5_status.json"`
2. Read latest status: `docker exec mt5_autonomous_node cat "/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/mt5_status.json"`
3. Ensure XAUUSD chart is open in MT5 and symbo is subscribed to price data

## Commands Reference

```bash
# Start container
cd ~/mt5_node && docker-compose up -d

# Stop container
cd ~/mt5_node && docker-compose down

# View MT5 UI (VNC)
# Open browser: http://localhost:3000
# Login: trader / SecureTradePassword2026!

# Launch EA (automatic deployment + compilation)
python3 ~/human-ai/liveea_docker.py

# Compile EA directly (for testing)
bash ~/human-ai/scripts/compile_ea_docker.sh mt5_autonomous_node MetalEA_v3

# Verify pipeline (full test)
cd ~/mt5_node && ./deploy_and_test.sh

# Monitor container logs
docker logs -f mt5_autonomous_node

# Connect to container shell
docker exec -it mt5_autonomous_node bash

# List compiled EAs
docker exec mt5_autonomous_node ls -lh "/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts/"

# Stop all EA processes
docker exec mt5_autonomous_node pkill -f "python|metaeditor|terminal"
```

## Performance Notes

- **Compilation time**: 5-15 seconds (first run) per EA
- **Signal latency**: < 2 seconds from Python to MT5 execution
- **Status update frequency**: Every tick (refreshed by mt5_status.json)
- **Container memory**: ~2-3GB (includes X11, KasmVNC, Wine)
- **CPU usage**: 10-30% idle, up to 60-80% during compilation/trading

## Next Steps

1. ✓ Verify Docker setup is working
2. ✓ Test EA compilation pipeline
3. ✓ Launch MetalEA_v3 and attach to MT5
4. Run live trading with automated signal generation
5. Monitor logs and adjust parameters
6. Scale to other symbols (XAGUSD, EURUSD, GBPUSD)

## Security Notes

⚠️ **Important**:

1. **Credentials**: Never share your IC Markets demo credentials
2. **MT5 Access**: Change the KasmVNC password in `docker-compose.yaml`
3. **Network**: Container listens on localhost only (ports 3000, 8001)
4. **Backups**: Regularly backup `~/mt5_node/trading_workspace/` (MT5 history)

---

**Last Updated**: 2026-05-22  
**Version**: MetalEA_v3 + Docker v1.0
