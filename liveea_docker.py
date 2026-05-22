#!/usr/bin/env python3
"""
liveea_docker.py — Containerized MT5 EA Launcher (headless, no X11)
=======================================================================
This launcher is designed for the Docker containerized MT5 setup:
  - Deploys MetalEA_v3.mq5 into the container
  - Compiles via Wine/metaeditor64 headlessly (no xdotool)
  - Uses JSON file communication instead of GUI automation
  - Waits for mt5_status.json confirmation from the EA
  - Launches the Python trading loop

Usage:
    python3 ~/human-ai/liveea_docker.py [docker_container_name]
    
    Default container: mt5_autonomous_node
"""

import subprocess, sys, os, time, json, shutil, signal
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

# ────────────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────────────

CONTAINER_NAME  = sys.argv[1] if len(sys.argv) > 1 else "mt5_autonomous_node"
EA_NAME         = "MetalEA_v3"
EA_SOURCE       = PROJECT_ROOT / "agents/trading-agent/mq5/MetalEA_v3.mq5"
EA_LOG          = PROJECT_ROOT / "data/logs/liveea_docker.log"
PID_FILE        = PROJECT_ROOT / "agents/trading-agent/trades/mt5/ea_trader.pid"
OBSIDIAN_DIR    = PROJECT_ROOT / "data/obsidian/trades"

# Container paths
CONTAINER_EXPERTS_DIR = "/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts"
CONTAINER_FILES_DIR   = "/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files"
CONTAINER_METAEDITOR  = "/config/.wine/drive_c/Program Files/MetaTrader 5/metaeditor64.exe"

(PROJECT_ROOT / "data/logs").mkdir(parents=True, exist_ok=True)
OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────────────────────────────────
# Logging & utilities
# ────────────────────────────────────────────────────────────────────────────

def log_msg(level: str, msg: str):
    """Print and log message"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    formatted = f"[{timestamp}] [{level}] {msg}"
    print(formatted)
    
    with open(EA_LOG, "a") as f:
        f.write(formatted + "\n")

def vault(title: str, body: str, tag: str = "ea_launch"):
    """Log to Obsidian vault"""
    try:
        f = OBSIDIAN_DIR / f"{datetime.now().strftime('%Y-%m-%d')}-{tag}.md"
        ts = datetime.now().strftime("%H:%M:%S")
        with open(f, "a") as fp:
            fp.write(f"## {title}\n_{ts}_\n{body}\n\n---\n\n")
    except Exception as e:
        log_msg("WARN", f"Vault write failed: {e}")

def docker_exec(cmd: list, user: str = None, timeout: int = 60) -> tuple:
    """Execute command inside container, return (returncode, stdout, stderr)"""
    if user:
        docker_cmd = ["docker", "exec", "-u", user, CONTAINER_NAME] + cmd
    else:
        docker_cmd = ["docker", "exec", CONTAINER_NAME] + cmd
    
    try:
        result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=timeout)
        return (result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (124, "", f"Command timed out after {timeout}s")
    except Exception as e:
        return (-1, "", str(e))

def docker_cp_to(local_path: Path, container_path: str):
    """Copy file from host to container"""
    cmd = ["docker", "cp", str(local_path), f"{CONTAINER_NAME}:{container_path}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def container_running() -> bool:
    """Check if container is running"""
    result = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], 
                          capture_output=True, text=True)
    return CONTAINER_NAME in result.stdout

# ────────────────────────────────────────────────────────────────────────────
# Phase 1: Pre-flight checks
# ────────────────────────────────────────────────────────────────────────────

def preflight_check():
    """Verify container and prerequisites"""
    log_msg("INFO", "=" * 70)
    log_msg("INFO", "PHASE 0: PREFLIGHT CHECKS")
    log_msg("INFO", "=" * 70)
    
    if not EA_SOURCE.exists():
        log_msg("ERROR", f"EA source not found: {EA_SOURCE}")
        return False
    log_msg("INFO", f"✓ EA source: {EA_SOURCE}")
    
    if not container_running():
        log_msg("ERROR", f"Container '{CONTAINER_NAME}' not running")
        log_msg("INFO", "Start with: cd mt5_node && docker-compose up -d")
        return False
    log_msg("INFO", f"✓ Container running: {CONTAINER_NAME}")
    
    # Check if MT5 is initialized
    rc, _, _ = docker_exec(["test", "-f", CONTAINER_METAEDITOR])
    if rc != 0:
        log_msg("WARN", "MetaEditor not fully initialized yet, waiting...")
        time.sleep(5)
    
    vault("Preflight Checks Passed", f"- Container: {CONTAINER_NAME}\n- EA: {EA_SOURCE}")
    return True

# ────────────────────────────────────────────────────────────────────────────
# Phase 1: Deploy EA to container
# ────────────────────────────────────────────────────────────────────────────

def deploy_ea():
    """Copy MetalEA_v3.mq5 to container"""
    log_msg("INFO", "=" * 70)
    log_msg("INFO", f"PHASE 1: DEPLOYING {EA_NAME}.mq5")
    log_msg("INFO", "=" * 70)
    
    container_dest = f"{CONTAINER_EXPERTS_DIR}/{EA_NAME}.mq5"
    
    if docker_cp_to(EA_SOURCE, container_dest):
        size = EA_SOURCE.stat().st_size
        log_msg("INFO", f"✓ Deployed {EA_NAME}.mq5 → {container_dest} ({size} bytes)")
        vault(f"{EA_NAME} Deployed", f"- Size: {size} bytes\n- Dest: {container_dest}")
        return True
    else:
        log_msg("ERROR", f"Failed to copy {EA_NAME}.mq5 to container")
        return False

# ────────────────────────────────────────────────────────────────────────────
# Phase 2: Compile EA inside container (headless)
# ────────────────────────────────────────────────────────────────────────────

def compile_ea():
    """Compile MetalEA_v3.mq5 via Wine metaeditor64 (headless)"""
    log_msg("INFO", "=" * 70)
    log_msg("INFO", f"PHASE 2: COMPILING {EA_NAME}.mq5 (HEADLESS)")
    log_msg("INFO", "=" * 70)
    
    # Remove stale .ex5
    docker_exec(["rm", "-f", f"{CONTAINER_EXPERTS_DIR}/{EA_NAME}.ex5"])
    
    mq5_win_path = f"C:\\\\Program Files\\\\MetaTrader 5\\\\MQL5\\\\Experts\\\\{EA_NAME}.mq5"
    compile_cmd = [
        "wine", CONTAINER_METAEDITOR,
        f"/compile:{mq5_win_path}",
        "/log:/config/MetaEditor_compile.log"
    ]
    
    log_msg("INFO", f"Running: wine metaeditor64.exe /compile:{EA_NAME}.mq5 ...")
    rc, stdout, stderr = docker_exec(compile_cmd, user="911", timeout=120)
    
    if stdout:
        log_msg("DEBUG", f"Stdout: {stdout[:500]}")
    if stderr:
        log_msg("DEBUG", f"Stderr: {stderr[:500]}")
    
    # Wait for .ex5 file
    time.sleep(3)
    
    rc_check, _, _ = docker_exec(["test", "-f", f"{CONTAINER_EXPERTS_DIR}/{EA_NAME}.ex5"])
    if rc_check == 0:
        rc_size, size_str, _ = docker_exec(["stat", "-c%s", f"{CONTAINER_EXPERTS_DIR}/{EA_NAME}.ex5"])
        size = size_str.strip() if rc_size == 0 else "?"
        log_msg("INFO", f"✓ Compilation successful: {EA_NAME}.ex5 ({size} bytes)")
        vault(f"{EA_NAME} Compiled", f"- Binary size: {size} bytes\n- Path: {CONTAINER_EXPERTS_DIR}")
        return True
    else:
        log_msg("ERROR", f"Compilation failed: {EA_NAME}.ex5 not created")
        
        # Try to extract compile log for debugging
        rc_log, log_content, _ = docker_exec(["cat", "/config/MetaEditor_compile.log"])
        if rc_log == 0 and log_content:
            log_msg("ERROR", f"Compile log:\n{log_content[:500]}")
        
        vault(f"{EA_NAME} Compilation Failed",
              f"- Error: .ex5 not generated\n- Check Wine/MetaEditor logs in container")
        return False

# ────────────────────────────────────────────────────────────────────────────
# Phase 3: Verify MT5 connection
# ────────────────────────────────────────────────────────────────────────────

def wait_for_mt5_status(timeout: int = 300):
    """Wait for mt5_status.json from EA (indicates MT5 is connected)"""
    log_msg("INFO", "=" * 70)
    log_msg("INFO", "PHASE 3: WAITING FOR MT5 STATUS")
    log_msg("INFO", "=" * 70)
    
    deadline = time.time() + timeout
    attempt = 0
    
    while time.time() < deadline:
        attempt += 1
        
        # Check if status file exists in container
        rc, _, _ = docker_exec(["test", "-f", f"{CONTAINER_FILES_DIR}/mt5_status.json"])
        
        if rc == 0:
            # Read status from container
            rc_read, status_content, _ = docker_exec(["cat", f"{CONTAINER_FILES_DIR}/mt5_status.json"])
            if rc_read == 0 and status_content:
                try:
                    import re
                    # Fix unquoted timestamps
                    status_content = re.sub(r'(?<=:)(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})(?=[,}])', r'"\1"', status_content)
                    status = json.loads(status_content)
                    
                    log_msg("INFO", "✓ MetalEA_v3 CONFIRMED LIVE:")
                    log_msg("INFO", f"  Account  : #{status.get('account', '?')} ")
                    log_msg("INFO", f"  Balance  : ${status.get('balance', '?')}")
                    log_msg("INFO", f"  Equity   : ${status.get('equity', '?')}")
                    log_msg("INFO", f"  XAUUSD   : ${status.get('xauusd_bid', '?')}")
                    log_msg("INFO", f"  Positions: {status.get('open_positions', 0)}")
                    
                    vault("MetalEA_v3 Live",
                          f"- Account: #{status.get('account', '?')}\n"
                          f"- Balance: ${status.get('balance', '?')}\n"
                          f"- Equity: ${status.get('equity', '?')}")
                    return status
                except json.JSONDecodeError:
                    pass
        
        remaining = int(deadline - time.time())
        if attempt % 6 == 0:  # Log every ~30s
            log_msg("INFO", f"Waiting for MT5... ({remaining}s remaining, attempt {attempt})")
        
        time.sleep(5)
    
    log_msg("ERROR", f"TIMEOUT: MT5 status not received after {timeout}s")
    log_msg("ERROR", "MetalEA_v3 may not be attached to chart or AutoTrading not enabled")
    vault("MT5 Status Timeout",
          "- MetalEA_v3 never confirmed\n"
          "- Check: Is EA attached? Is AutoTrading green?")
    return None

# ────────────────────────────────────────────────────────────────────────────
# Phase 4: Test trade
# ────────────────────────────────────────────────────────────────────────────

def run_test_trade():
    """Send TEST_BUY signal and confirm execution"""
    log_msg("INFO", "=" * 70)
    log_msg("INFO", "PHASE 4: RUNNING TEST TRADE")
    log_msg("INFO", "=" * 70)
    
    sig_id = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    signal_json = {
        "id": sig_id,
        "action": "TEST_BUY",
        "symbol": "XAUUSD",
        "lot": 0.01,
        "sl": 0,
        "tp": 0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Write signal to container
    signal_file = f"{CONTAINER_FILES_DIR}/python_signal.json"
    signal_content = json.dumps(signal_json, separators=(",", ":"))
    
    # Use docker exec to write file
    docker_exec(["bash", "-c", f"cat > {signal_file} << 'EOF'\n{signal_content}\nEOF"], user="911")
    log_msg("INFO", f"Test signal sent: {sig_id}")
    
    # Wait for result
    result_file = f"{CONTAINER_FILES_DIR}/python_result.json"
    deadline = time.time() + 30
    
    while time.time() < deadline:
        rc, result_content, _ = docker_exec(["cat", result_file])
        if rc == 0 and result_content:
            try:
                result = json.loads(result_content)
                if result.get("sig_id") == sig_id:
                    if result.get("success"):
                        log_msg("INFO", "✓ TEST TRADE CONFIRMED")
                        log_msg("INFO", f"  Signal: {sig_id}")
                        log_msg("INFO", f"  MT5 Response: {result.get('ts')}")
                        vault("Test Trade Passed",
                              f"- Signal: {sig_id}\n"
                              f"- Action: TEST_BUY\n"
                              f"- Result: SUCCESS")
                        
                        # Wait for auto-close
                        log_msg("INFO", "Test trade will auto-close in 60s...")
                        time.sleep(65)
                        return True
                    else:
                        log_msg("ERROR", f"Test trade failed: {result}")
                        return False
            except json.JSONDecodeError:
                pass
        
        time.sleep(1)
    
    log_msg("WARN", "Test trade result not confirmed — proceeding anyway")
    vault("Test Trade Timeout", "- No confirmation from MT5\n- Will proceed with main loop")
    return True

# ────────────────────────────────────────────────────────────────────────────
# Main entry point
# ────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 70)
    print("MetalEA_v3 Docker Launcher v1.0")
    print(f"Container: {CONTAINER_NAME}")
    print(f"Log: {EA_LOG}")
    print("=" * 70 + "\n")
    
    # Phase 0: Preflight
    if not preflight_check():
        sys.exit(1)
    
    # Phase 1: Deploy
    if not deploy_ea():
        sys.exit(1)
    
    # Phase 2: Compile
    if not compile_ea():
        sys.exit(1)
    
    log_msg("INFO", "")
    log_msg("INFO", "NOTE: MetalEA_v3 requires manual attachment to XAUUSD chart in MT5")
    log_msg("INFO", "      Please visit http://localhost:3000 and:")
    log_msg("INFO", "      1. Open Navigator (Ctrl+N)")
    log_msg("INFO", "      2. Navigate to Expert Advisors → MetalEA_v3")
    log_msg("INFO", "      3. Double-click to attach to XAUUSD chart")
    log_msg("INFO", "      4. Enable AutoTrading (green button)")
    log_msg("INFO", "")
    
    vault("MetalEA_v3 Waiting for Attachment",
          "- Compiled successfully\n"
          "- Awaiting manual attachment to MT5\n"
          "- Please attach via Navigator in MT5")
    
    # Phase 3: Wait for MT5
    mt5_status = wait_for_mt5_status(timeout=300)
    if not mt5_status:
        log_msg("ERROR", "LAUNCHER ABORTED: MT5 connection failed")
        sys.exit(1)
    
    # Phase 4: Test trade
    if not run_test_trade():
        log_msg("WARN", "Test trade failed but continuing...")
    
    # Launch main EA trader loop
    log_msg("INFO", "=" * 70)
    log_msg("INFO", "LAUNCHING EA TRADER MAIN LOOP")
    log_msg("INFO", "=" * 70)
    
    EA_TRADER_PATH = PROJECT_ROOT / "agents/trading-agent/live_trading_ea.py"
    if not EA_TRADER_PATH.exists():
        log_msg("ERROR", f"EA trader not found: {EA_TRADER_PATH}")
        sys.exit(1)
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("live_trading_ea", EA_TRADER_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.EATrader().run()
    except Exception as e:
        log_msg("ERROR", f"EA Trader failed: {e}")
        sys.exit(1)
    finally:
        vault("EA Launcher Stopped",
              f"- Stopped at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_msg("INFO", "Interrupted by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        log_msg("ERROR", f"Unhandled exception: {e}")
        import traceback
        log_msg("ERROR", traceback.format_exc())
        sys.exit(1)
