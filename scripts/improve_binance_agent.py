#!/usr/bin/env python3
"""
Auto-tune Binance trading agent every 6 hours.
Analyzes recent performance and adjusts key parameters.
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRADES_DIR = PROJECT_ROOT / "agents" / "trading-agent" / "trades" / "binance"
LOG_FILE = PROJECT_ROOT / "data" / "logs" / "live_trading_binance.log"
AGENT_FILE = PROJECT_ROOT / "agents" / "trading-agent" / "live_trading_binance.py"

# How many recent log lines to analyze
LOG_SAMPLE_LINES = 5000

def tail_lines(path: Path, n: int) -> list[str]:
    try:
        with open(path, 'r', errors='ignore') as f:
            lines = f.readlines()
            return lines[-n:] if len(lines) >= n else lines
    except Exception:
        return []

def analyze_performance() -> dict:
    """Compute metrics from recent logs and today's trades."""
    lines = tail_lines(LOG_FILE, LOG_SAMPLE_LINES)
    total_exits = 0
    wins = 0
    losses = 0
    timeout_count = 0
    sl_fail_count = 0
    lowvol_count = 0

    for line in lines:
        if "[WARN] Exchange SL order failed" in line:
            sl_fail_count += 1
        if "[LOWVOL]" in line:
            lowvol_count += 1
        if "-> EXIT [" in line:
            total_exits += 1
            if "[TIMEOUT]" in line:
                timeout_count += 1
            # Determine win/loss from PnL sign
            m = re.search(r'PnL=\$([+-]?\d+\.\d+)', line)
            if m:
                pnl = float(m.group(1))
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1

    # Today's PnL from JSONL
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    trades_file = TRADES_DIR / f"trades_{today_str}.jsonl"
    total_pnl_today = 0.0
    if trades_file.exists():
        for line in trades_file.read_text(errors='replace').splitlines():
            try:
                t = json.loads(line)
                if t.get("type") == "EXIT":
                    total_pnl_today += float(t.get("pnl", 0))
            except Exception:
                pass

    metrics = {
        "total_exits": total_exits,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / total_exits if total_exits > 0 else 0.0,
        "timeout_rate": timeout_count / total_exits if total_exits > 0 else 0.0,
        "lowvol_ratio": lowvol_count / len(lines) if lines else 0.0,
        "sl_fail_ratio": sl_fail_count / max(total_exits, 1),
        "total_pnl_today": total_pnl_today,
    }
    return metrics

def read_current_params() -> dict:
    """Extract current tunable parameters from the agent file."""
    content = AGENT_FILE.read_text(errors='replace')
    # Regex to find assignments
    def get_val(name):
        pattern = rf'^{name}\s*=\s*(.+?)(?:#|$)'
        m = re.search(pattern, content, re.MULTILINE)
        if m:
            val_str = m.group(1).strip()
            try:
                return float(val_str)
            except ValueError:
                return val_str
        return None

    params = {
        "MIN_STRENGTH": get_val("MIN_STRENGTH"),
        "VOL_FILTER_MULT": get_val("VOL_FILTER_MULT"),
        "ASIAN_VOL_MULT": get_val("ASIAN_VOL_MULT"),
        "MAX_OPEN": get_val("MAX_OPEN"),
        "MAX_HOLD_S": get_val("MAX_HOLD_S"),
    }
    return params

def adjust_params(metrics: dict, current: dict) -> dict:
    """Decide new parameter values based on metrics."""
    new = current.copy()
    # MIN_STRENGTH adjustment
    wr = metrics["win_rate"]
    if wr < 0.35:
        new_min = max(0.35, current.get("MIN_STRENGTH", 0.5) - 0.05)
        new["MIN_STRENGTH"] = round(new_min, 2)
    elif wr > 0.50:
        new_min = min(0.60, current.get("MIN_STRENGTH", 0.5) + 0.05)
        new["MIN_STRENGTH"] = round(new_min, 2)
    # VOL_FILTER_MULT: if too much lowvol, relax
    if metrics["lowvol_ratio"] > 0.7:
        new_vol = max(0.5, current.get("VOL_FILTER_MULT", 1.0) - 0.1)
        new["VOL_FILTER_MULT"] = round(new_vol, 2)
        new_asian = max(1.0, current.get("ASIAN_VOL_MULT", 1.5) - 0.2)
        new["ASIAN_VOL_MULT"] = round(new_asian, 2)
    # MAX_HOLD_S: if timeout rate high, reduce hold time
    if metrics["timeout_rate"] > 0.4:
        new_hold = max(90, current.get("MAX_HOLD_S", 130) - 10)
        new["MAX_HOLD_S"] = new_hold
    # PnL-based open slots and equity
    pnl_today = metrics["total_pnl_today"]
    if pnl_today > 100:
        new_max_open = min(10, current.get("MAX_OPEN", 5) + 1)
        new["MAX_OPEN"] = new_max_open
    elif pnl_today < -100:
        new_max_open = max(3, current.get("MAX_OPEN", 5) - 1)
        new["MAX_OPEN"] = new_max_open
    return new

def generate_patch(old: dict, new: dict) -> str:
    """Create a unified diff patch to update the agent file."""
    lines = []
    lines.append("*** Begin Patch")
    lines.append(f"*** Update File: {AGENT_FILE.relative_to(PROJECT_ROOT)}")
    for key, old_val in old.items():
        if key not in new:
            continue
        new_val = new[key]
        if old_val == new_val:
            continue
        # Format value appropriately
        if isinstance(new_val, float):
            old_str = f"{old_val:.6f}".rstrip('0').rstrip('.') if '.' in str(old_val) else str(old_val)
            new_str = f"{new_val:.6f}".rstrip('0').rstrip('.') if '.' in str(new_val) else str(new_val)
        else:
            old_str = str(old_val)
            new_str = str(new_val)
        lines.append(f"@@ adjust {key}")
        lines.append(f"-{key} = {old_str}")
        lines.append(f"+{key} = {new_str}")
    lines.append("*** End Patch")
    return "\n".join(lines)

def apply_patch(patch_text: str) -> bool:
    """Apply patch using the patch tool."""
    try:
        result = subprocess.run(
            ["hermes", "patch", "-"],
            input=patch_text,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=60
        )
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"Patch failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error applying patch: {e}")
        return False

def restart_binance_service():
    """Restart the Binance systemd service."""
    try:
        subprocess.run(["systemctl", "restart", "binance"], check=True)
        print("Binance service restarted.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to restart binance service: {e}")

def main():
    print(f"[{datetime.now()}] Starting Binance auto-improvement run...")
    metrics = analyze_performance()
    print(f"Metrics: {json.dumps(metrics, indent=2)}")
    current = read_current_params()
    print(f"Current params: {json.dumps(current, indent=2)}")
    new_params = adjust_params(metrics, current)
    print(f"Proposed params: {json.dumps(new_params, indent=2)}")

    if new_params == current:
        print("No parameter changes needed. Exiting.")
        return 0

    patch_text = generate_patch(current, new_params)
    print("Generated patch. Applying...")
    if apply_patch(patch_text):
        print("Patch applied successfully. Restarting binance service...")
        restart_binance_service()
        return 0
    else:
        print("Patch application failed. Not restarting service.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
