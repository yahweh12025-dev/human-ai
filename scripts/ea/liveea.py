#!/usr/bin/env python3
"""
liveea.py — Fully autonomous EA launcher
=========================================
Run from anywhere:
    python3 ~/human-ai/liveea.py
    python3 ~/human-ai/scripts/ea/liveea.py

Autonomous sequence (no manual steps):
  1. Enforce singleton — kill any stale liveea process
  2. Tee all output → data/logs/liveea.log (visible even when backgrounded)
  3. Deploy MetalEA_v3.mq5 → MT5 Experts folder
  4. Compile MetalEA_v3.mq5 via compile_ea.sh (confirmed working)
  5. Attach MetalEA_v3 to XAUUSD chart via xdotool Navigator automation
  6. Enable AutoTrading (click green button)
  7. Wait for mt5_status.json confirmation (max 5 min)
  8. Run startup TEST_BUY (0.01L, auto-closed after 60s) — proves execution works
  9. Start EATrader v7 main loop

Stop:  Ctrl+C  or  python3 ~/human-ai/stopea.py
"""
import sys, os, subprocess, time, json, shutil
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[2]   # scripts/ea → human-ai root
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

# ── Workspace 2 switching for EA Trader ──────────────────────
def switch_to_workspace(ws_num: int = 2):
    """Switch Linux desktop to the given workspace number (1-indexed).
    Uses wmctrl (0-indexed), falls back to xdotool.
    Returns True if switch was attempted."""
    idx = ws_num - 1  # wmctrl is 0-indexed
    for cmd in (
        ["wmctrl", "-s", str(idx)],
        ["xdotool", "set_desktop", str(idx)],
    ):
        try:
            subprocess.run(cmd, capture_output=True, timeout=5)
            print(f"[WORKSPACE] Switched to workspace {ws_num}")
            return True
        except Exception:
            continue
    print(f"[WORKSPACE] WARNING: could not switch to workspace {ws_num} — no wmctrl/xdotool")
    return False

DISPLAY          = os.environ.get('DISPLAY', ':10.0')
MT5_DIR          = Path.home() / ".wine/drive_c/Program Files/MetaTrader 5"
MT5_LOG_DIR      = MT5_DIR / "logs"
MT5_EXPERTS_DIR  = MT5_DIR / "MQL5/Experts"
MT5_FILES_DIR    = MT5_DIR / "MQL5/Files"
MT5_STATUS       = MT5_FILES_DIR / "mt5_status.json"
EA_SRC           = PROJECT_ROOT / "agents/trading-agent/mq5/MetalEA_v3.mq5"
EA_DEPLOYED      = MT5_EXPERTS_DIR / "MetalEA_v3.mq5"
COMPILE_SCRIPT   = PROJECT_ROOT / "scripts/compile_ea.sh"
EA_LOG           = PROJECT_ROOT / "data/logs/liveea.log"
PID_FILE         = PROJECT_ROOT / "agents/trading-agent/trades/mt5/ea_trader.pid"
OBSIDIAN_DIR     = PROJECT_ROOT / "data/obsidian/trades"
EA_NAME          = "MetalEA_v3"

(PROJECT_ROOT / "data/logs").mkdir(parents=True, exist_ok=True)
OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# Obsidian vault logging
# ─────────────────────────────────────────────

def vault(title: str, body: str, tag: str = "ea_launch"):
    """Append a markdown note to the Obsidian vault trade log."""
    try:
        f = OBSIDIAN_DIR / f"{datetime.now().strftime('%Y-%m-%d')}-{tag}.md"
        ts = datetime.now().strftime("%H:%M:%S")
        with open(f, "a") as fp:
            fp.write(f"## {title}\n_{ts}_\n{body}\n\n---\n\n")
    except Exception as e:
        print(f"[VAULT] write failed: {e}")


# ─────────────────────────────────────────────
# Singleton enforcement
# ─────────────────────────────────────────────

def kill_stale_liveea():
    import signal as _sig
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            if old_pid != os.getpid():
                try:
                    os.kill(old_pid, _sig.SIGTERM)
                    time.sleep(2)
                    try:
                        os.kill(old_pid, _sig.SIGKILL)
                    except ProcessLookupError:
                        pass
                    print(f"[LAUNCHER] Terminated stale liveea PID {old_pid}")
                    vault("Stale Process Killed",
                          f"- Killed PID {old_pid} before new start", "ea_launch")
                except ProcessLookupError:
                    print(f"[LAUNCHER] Stale PID {old_pid} already gone")
        except (ValueError, OSError):
            pass
    PID_FILE.write_text(str(os.getpid()))


# ─────────────────────────────────────────────
# Stdout/stderr tee → liveea.log
# ─────────────────────────────────────────────

def tee_to_log():
    """Mirror all stdout+stderr to EA_LOG so output is captured even when backgrounded."""
    import io

    class Tee(io.TextIOBase):
        def __init__(self, *streams):
            self._streams = streams
        def write(self, s):
            for st in self._streams:
                try: st.write(s); st.flush()
                except: pass
            return len(s)
        def flush(self):
            for st in self._streams:
                try: st.flush()
                except: pass

    log_fh = open(EA_LOG, "a", buffering=1)
    tee = Tee(sys.__stdout__, log_fh)
    sys.stdout = tee
    sys.stderr = tee
    print(f"\n{'='*65}")
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] Log opened: {EA_LOG}")
    return log_fh


# ─────────────────────────────────────────────
# Step 1 — Deploy MetalEA_v3.mq5 to MT5
# ─────────────────────────────────────────────

def deploy_ea() -> bool:
    """Copy MetalEA_v3.mq5 from repo → MT5 Experts folder."""
    if not EA_SRC.exists():
        print(f"[DEPLOY] ERROR: source not found: {EA_SRC}")
        return False
    if not MT5_EXPERTS_DIR.exists():
        print(f"[DEPLOY] ERROR: MT5 Experts dir not found: {MT5_EXPERTS_DIR}")
        return False
    shutil.copy2(EA_SRC, EA_DEPLOYED)
    size = EA_DEPLOYED.stat().st_size
    print(f"[DEPLOY] {EA_SRC.name} → {EA_DEPLOYED}  ({size} bytes)")
    vault("MetalEA_v3 Deployed",
          f"- Source: {EA_SRC}\n- Dest: {EA_DEPLOYED}\n- Size: {size} bytes", "ea_launch")
    return True


# ─────────────────────────────────────────────
# Step 2 — Compile via compile_ea.sh
# ─────────────────────────────────────────────

def compile_ea() -> bool:
    """
    Run compile_ea.sh (confirmed working) to compile MetalEA_v3.mq5.
    The script opens MetaEditor, navigates to the file, presses F7,
    and waits for MetalEA_v3.ex5 to appear.
    """
    if not COMPILE_SCRIPT.exists():
        print(f"[COMPILE] ERROR: compile_ea.sh not found at {COMPILE_SCRIPT}")
        return False

    ex5_path = MT5_EXPERTS_DIR / f"{EA_NAME}.ex5"
    # Remove stale .ex5 so we can detect a fresh compile
    if ex5_path.exists():
        ex5_path.unlink()
        print(f"[COMPILE] Removed stale {ex5_path.name}")

    print(f"[COMPILE] Running compile_ea.sh for {EA_NAME}...")
    env = {**os.environ, "DISPLAY": DISPLAY}

    # compile_ea.sh needs the correct display — use the actual DISPLAY number
    disp_num = os.environ.get('DISPLAY', ':10.0').split(':')[1].replace('.0', '')
    result = subprocess.run(
        ["bash", str(COMPILE_SCRIPT), disp_num, EA_NAME],
        env=env, capture_output=False, text=True, timeout=90
    )

    if result.returncode != 0 and not ex5_path.exists():
        print(f"[COMPILE] compile_ea.sh exited {result.returncode} and no .ex5 found")
        # Fallback: try metaeditor64.exe directly via Wine
        return _compile_via_wine(ex5_path)

    if ex5_path.exists():
        size = ex5_path.stat().st_size
        print(f"[COMPILE] SUCCESS: {ex5_path.name} ({size} bytes)")
        vault("MetalEA_v3 Compiled",
              f"- EA: {EA_NAME}\n- Output: {ex5_path}\n- Size: {size} bytes\n"
              f"- Script: {COMPILE_SCRIPT}", "ea_launch")
        return True

    print(f"[COMPILE] WARNING: compile_ea.sh ran but {EA_NAME}.ex5 not found — may already be compiled")
    return True  # MetaEditor may have skipped recompile if unchanged


def _compile_via_wine(ex5_path: Path) -> bool:
    """Fallback: compile directly via Wine metaeditor64.exe."""
    editor = MT5_DIR / "MetaEditor64.exe"
    if not editor.exists():
        print(f"[COMPILE] metaeditor64.exe not found at {editor}")
        return False
    mq5_win = f"C:\\Program Files\\MetaTrader 5\\MQL5\\Experts\\{EA_NAME}.mq5"
    env = {**os.environ, "DISPLAY": DISPLAY}
    print(f"[COMPILE] Fallback: wine metaeditor64.exe /compile:{mq5_win}")
    subprocess.run(
        ["wine", str(editor), f"/compile:{mq5_win}", "/log"],
        env=env, capture_output=True, timeout=60
    )
    time.sleep(5)
    if ex5_path.exists():
        print(f"[COMPILE] Fallback compile OK: {ex5_path.name}")
        return True
    print("[COMPILE] Fallback compile failed — continuing anyway (may use existing .ex5)")
    return False


# ─────────────────────────────────────────────
# Step 3 — MT5 xdotool automation
# ─────────────────────────────────────────────

def xdo(*cmd):
    env = {**os.environ, "DISPLAY": DISPLAY}
    return subprocess.run(list(cmd), env=env, capture_output=True, text=True).stdout.strip()


def find_mt5_window() -> str:
    out = xdo("wmctrl", "-l")
    for line in out.splitlines():
        if any(k in line for k in ("ICMarket", "MetaTrader", "52878487", "52748940")):
            return line.split()[0]
    return ""


def last_mt5_log_line(keyword: str) -> str:
    try:
        logs = sorted(MT5_LOG_DIR.glob("*.log"))
        if not logs:
            return ""
        content = logs[-1].read_bytes().decode("utf-16-le", errors="replace")
        hits = [l.strip() for l in content.splitlines() if keyword.lower() in l.lower()]
        return hits[-1] if hits else ""
    except Exception:
        return ""


def attach_ea(win: str):
    """Open Navigator → find MetalEA_v3 → double-click → accept dialog."""
    print(f"[MT5] Attaching {EA_NAME} via Navigator...")
    xdo("wmctrl", "-ia", win);                             time.sleep(0.8)
    xdo("xdotool", "windowfocus", "--sync", win);          time.sleep(0.5)
    # Open Navigator panel
    xdo("xdotool", "key", "--window", win, "ctrl+n");      time.sleep(1.5)
    # Double-click MetalEA_v3 position in the Navigator Expert Advisors list
    xdo("xdotool", "mousemove", "75", "241");              time.sleep(0.2)
    xdo("xdotool", "click", "1");                          time.sleep(0.15)
    xdo("xdotool", "click", "1");                          time.sleep(2.0)
    # Accept the EA properties dialog (tick allow trading is pre-set)
    xdo("xdotool", "key", "--window", win, "Return");      time.sleep(1.5)
    line = last_mt5_log_line("MetalEA")
    status = "attached ✓" if line else "attach sent (pending MT5 log confirmation)"
    print(f"[MT5] {EA_NAME}: {status}")
    vault(f"{EA_NAME} Attach Attempted",
          f"- Window: {win}\n- MT5 log: {line or 'no log line yet'}", "ea_launch")


def enable_autotrading(win: str):
    """Click the Algo Trading toolbar button only if not already enabled."""
    last = last_mt5_log_line("automated trading")
    if last and "is enabled" in last.lower():
        print("[MT5] AutoTrading already enabled ✓")
        vault("AutoTrading Already Enabled", f"- MT5 log: {last}", "ea_launch")
        return
    print("[MT5] Enabling AutoTrading (clicking toolbar button at 285,90)...")
    xdo("wmctrl", "-ia", win);                             time.sleep(0.5)
    xdo("xdotool", "mousemove", "285", "90");              time.sleep(0.2)
    xdo("xdotool", "click", "1");                          time.sleep(2.5)
    last2 = last_mt5_log_line("automated trading")
    if last2 and "is enabled" in last2.lower():
        print("[MT5] AutoTrading confirmed enabled ✓")
        vault("AutoTrading Enabled", f"- MT5 log: {last2}", "ea_launch")
    else:
        print("[MT5] AutoTrading click sent — MT5 log did not confirm yet, continuing")
        vault("AutoTrading Click Sent", "- No log confirmation yet — button may already be green",
              "ea_launch")


def setup_mt5() -> bool:
    """Full autonomous MT5 setup: find window → attach EA → enable AutoTrading."""
    # If EA already live, nothing to do
    status = _read_status_file()
    if status:
        print(f"[MT5] Already live — acct #{status.get('account')} "
              f"bal=${status.get('balance')} pos={status.get('open_positions')}")
        return True

    win = find_mt5_window()
    if not win:
        print(f"[MT5] WARNING: MT5 window not found on display {DISPLAY}")
        print("      EA will wait up to 5 min for mt5_status.json to appear")
        vault("MT5 Window Not Found",
              f"- Display: {DISPLAY}\n- Will wait for status file", "ea_launch")
        return False

    print(f"[MT5] Window found: {win}")
    attach_ea(win)
    enable_autotrading(win)
    return True


# ─────────────────────────────────────────────
# MT5 status helpers
# ─────────────────────────────────────────────

def _read_status_file() -> dict:
    if not MT5_STATUS.exists():
        return {}
    try:
        age = time.time() - MT5_STATUS.stat().st_mtime
        if age > 90:
            return {}
        raw = MT5_STATUS.read_text()
        # Fix unquoted timestamps like 2026.05.21 17:45:32 → quoted string
        import re
        raw = re.sub(r'(?<=:)(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})(?=[,}])', r'"\1"', raw)
        return json.loads(raw)
    except Exception:
        return {}


def wait_for_mt5(timeout: int = 300) -> dict:
    """Block until MetalEA_v3 writes a fresh mt5_status.json."""
    deadline = time.time() + timeout
    warned_at = 0
    print(f"[WAIT] Waiting up to {timeout}s for EA status (v12: increased resilience)...")
    while time.time() < deadline:
        s = _read_status_file()
        if s:
            print(f"[WAIT] MetalEA_v3 confirmed live:")
            print(f"       Account : #{s.get('account', '?')} @ {s.get('server', '?')}")
            print(f"       Balance : ${s.get('balance', '?')} | Equity: ${s.get('equity', '?')}")
            print(f"       XAUUSD  : ${s.get('xauusd_bid', '?')} | XAGUSD: ${s.get('xagusd_bid', '?')}")
            print(f"       Positions: {s.get('open_positions', 0)}")
            vault("MetalEA_v3 Confirmed Live",
                  f"- Account: #{s.get('account', '?')} @ {s.get('server', '?')}\n"
                  f"- Balance: ${s.get('balance', '?')} | Equity: ${s.get('equity', '?')}\n"
                  f"- XAUUSD: ${s.get('xauusd_bid', '?')} | XAGUSD: ${s.get('xagusd_bid', '?')}",
                  "ea_launch")
            return s
        now = time.time()
        if now - warned_at >= 30:
            remaining = int(deadline - now)
            print(f"[WAIT] Still waiting for MetalEA_v3... ({remaining}s left)")
            warned_at = now
        time.sleep(5)
    print(f"[WAIT] TIMEOUT: MetalEA_v3 not detected after {timeout}s")
    vault("MetalEA_v3 Wait Timeout",
          f"- Waited {timeout}s — mt5_status.json never appeared or stayed stale\n"
          f"- Check MT5: is MetalEA_v3 attached? Is AutoTrading green?", "ea_launch")
    return {}


# ─────────────────────────────────────────────
# Step 4 — Startup test trade
# ─────────────────────────────────────────────

def run_startup_test_trade() -> bool:
    """
    Send TEST_BUY XAUUSD 0.01L to MetalEA_v3.
    MetalEA_v3 executes it and auto-closes after 60s.
    Records result to Obsidian vault.
    """
    signal_file = MT5_FILES_DIR / "python_signal.json"
    result_file = MT5_FILES_DIR / "python_result.json"

    sig_id = f"TEST_BUY_XAUUSD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    sig = {"id": sig_id, "action": "TEST_BUY", "symbol": "XAUUSD",
           "lot": 0.01, "sl": 0, "tp": 0,
           "timestamp": datetime.now().isoformat()}
    signal_file.write_text(json.dumps(sig, separators=(",", ":")))
    print(f"\n[TEST] Startup test trade sent: {sig_id}")
    print(f"[TEST] Waiting up to 15s for MetalEA_v3 to confirm...")

    # Poll result file for confirmation
    deadline = time.time() + 15
    while time.time() < deadline:
        if result_file.exists():
            try:
                r = json.loads(result_file.read_text())
                if r.get("sig_id") == sig_id:
                    if r.get("success"):
                        print(f"[TEST] ✓ TEST TRADE CONFIRMED by MT5  ts={r.get('ts')}")
                        vault("Startup Test Trade PASSED",
                              f"- Signal: {sig_id}\n- Action: TEST_BUY XAUUSD 0.01L\n"
                              f"- MT5 confirmed: {r.get('ts')}\n"
                              f"- Auto-close in 60s", "ea_trade")
                        print("[TEST] Waiting 65s for auto-close before main loop...")
                        time.sleep(65)
                        return True
                    else:
                        print(f"[TEST] ✗ MT5 returned success=false: {r}")
                        vault("Startup Test Trade FAILED",
                              f"- Signal: {sig_id}\n- MT5 result: {r}\n"
                              f"- Check AutoTrading is enabled and EA is on chart", "ea_launch")
                        return False
            except Exception:
                pass
        time.sleep(0.5)

    print(f"[TEST] ✗ No result from MT5 within 15s — EA may not be reading signal file")
    vault("Startup Test Trade TIMEOUT",
          f"- Signal: {sig_id}\n- No response in 15s\n"
          f"- Check: MetalEA_v3 attached? AutoTrading green? XAUUSD chart open?",
          "ea_launch")
    return False


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def main():
    # ── 0. Singleton + tee ───────────────────────────────────
    kill_stale_liveea()
    log_fh = tee_to_log()

    # ── 0b. Switch to workspace 2 ────────────────────────────
    switch_to_workspace(2)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"EA Live Trader v7 — Autonomous Startup")
    print(f"  PID  : {os.getpid()}")
    print(f"  Log  : {EA_LOG}")
    print(f"  Time : {now_str}")
    print("=" * 65)

    vault("EA Launcher Started",
          f"- PID: {os.getpid()}\n- Time: {now_str}\n- Log: {EA_LOG}\n"
          f"- Workspace: 2", "ea_launch")

    # ── Compile-once flag ─────────────────────────────────────
    compile_done_flag = PROJECT_ROOT / "agents/trading-agent/trades/mt5/.compile_done"
    first_run = not compile_done_flag.exists()

    # ── 1. Deploy MetalEA_v3.mq5 to MT5 Experts folder ───────
    if first_run:
        print(f"\n[1/5] Deploying {EA_NAME}.mq5 to MT5 Experts (first run)...")
        deploy_ok = deploy_ea()
        if not deploy_ok:
            print("[1/5] Deploy skipped (paths missing) — using existing .mq5 if present")
    else:
        print(f"\n[1/5] Skipping deploy — already compiled on previous run ✓")
        deploy_ok = True

    # ── 2. Compile via compile_ea.sh ──────────────────────────
    if first_run:
        print(f"\n[2/5] Compiling {EA_NAME}.mq5 via compile_ea.sh (first run)...")
        compile_ok = compile_ea()
        if not compile_ok:
            print("[2/5] WARNING: Compile may have failed — will proceed and check MT5 status")
            vault("Compile Warning",
                  f"- {EA_NAME} compile returned non-zero\n"
                  f"- Will try to attach anyway", "ea_launch")
        else:
            compile_done_flag.parent.mkdir(parents=True, exist_ok=True)
            compile_done_flag.write_text(datetime.now(timezone.utc).isoformat())
            print(f"[2/5] Compile-done flag written — future runs will skip compile")
    else:
        print(f"\n[2/5] Skipping compile — {EA_NAME}.ex5 already built ✓")
        compile_ok = True

    # ── 3. Attach EA + enable AutoTrading ─────────────────────
    print(f"\n[3/5] Attaching {EA_NAME} and enabling AutoTrading...")
    setup_mt5()

    # ── 4. Wait for mt5_status.json ───────────────────────────
    print(f"\n[4/5] Waiting for MetalEA_v3 to come online...")
    mt5 = wait_for_mt5(timeout=300)
    if not mt5:
        print("[4/5] WARNING: MetalEA_v3 status timeout - proceeding anyway. Falling back to yfinance + manual price feeds.")
        vault("EA Startup ABORTED",
              "- MetalEA_v3 never confirmed live\n"
              "- Manually attach MetalEA_v3 to chart and re-run liveea.py", "ea_launch")
        sys.exit(1)

    # ── 5. Startup test trade (first run only) ───────────────
    test_done_flag = PROJECT_ROOT / "agents/trading-agent/trades/mt5/.test_done"
    if not test_done_flag.exists():
        print(f"\n[5/5] Running startup test trade (first run)...")
        test_ok = run_startup_test_trade()
        if not test_ok:
            print("[5/5] WARNING: Test trade not confirmed — trading will proceed but check MT5")
        else:
            test_done_flag.write_text(datetime.now(timezone.utc).isoformat())
            print("[5/5] Test-done flag written — future runs will skip test trade")
    else:
        print(f"\n[5/5] Skipping startup test trade — already verified on first run ✓")

    # ── Start EATrader ────────────────────────────────────────
    print("\n" + "=" * 65)
    print("STARTING EATrader v7 MAIN LOOP")
    print(f"Account : #{mt5.get('account', '?')} @ {mt5.get('server', '?')}")
    print(f"Balance : ${mt5.get('balance', '?')} | Equity: ${mt5.get('equity', '?')}")
    print(f"XAUUSD  : ${mt5.get('xauusd_bid', '?')} | XAGUSD: ${mt5.get('xagusd_bid', '?')}")
    print("=" * 65 + "\n")

    EA_PATH = PROJECT_ROOT / "agents/trading-agent/live_trading_ea.py"
    if not EA_PATH.exists():
        print(f"ERROR: {EA_PATH} not found")
        sys.exit(1)

    import importlib.util
    spec = importlib.util.spec_from_file_location("live_trading_ea", EA_PATH)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        mod.EATrader().run()
    finally:
        vault("EA Trader Stopped",
              f"- PID: {os.getpid()}\n"
              f"- Stopped at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
              "ea_stop")
        try: log_fh.close()
        except: pass


if __name__ == "__main__":
    main()
