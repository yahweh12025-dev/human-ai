#!/usr/bin/env python3
"""
Trading Improvement Loop — autonomous analysis + suggestion generator
=====================================================================
Called by automode.py every 4 hours (via _maybe_run_trading_loop) to keep
both trading agents improving without manual intervention.

Actions performed each run:
  1. Read EA and Binance state files + today's trade JSONL
  2. Analyse win/loss streak, PnL by coin, and 3-day trend
  3. Check that both agent processes are alive; restart any that are dead
  4. Write improvement suggestions to data/logs/improvement_suggestions.json
  5. Append a Markdown summary to data/obsidian/sessions/YYYY-MM-DD-automode.md

Can also be run standalone:
    python3 core/orchestration/trading_improvement_loop.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUGGESTIONS_FILE = PROJECT_ROOT / "data" / "logs" / "improvement_suggestions.json"
OBSIDIAN_SESSION = PROJECT_ROOT / "data" / "obsidian" / "sessions"
OBSIDIAN_SESSION.mkdir(parents=True, exist_ok=True)

# ── State readers ─────────────────────────────────────────────

def _safe_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        return {}


def read_ea_state() -> dict:
    return _safe_json(PROJECT_ROOT / "agents/trading-agent/trades/mt5/state.json")


def read_binance_state() -> dict:
    return _safe_json(PROJECT_ROOT / "agents/trading-agent/trades/binance/state.json")


def read_today_binance_trades(now: datetime) -> dict:
    """Return per-symbol PnL dict from today's binance trade JSONL."""
    today = now.strftime("%Y%m%d")
    trades_file = PROJECT_ROOT / f"agents/trading-agent/trades/binance/trades_{today}.jsonl"
    coin_pnl: dict[str, float] = {}
    if not trades_file.exists():
        return coin_pnl
    for line in trades_file.read_text(errors="replace").splitlines():
        try:
            t = json.loads(line)
            if t.get("type") == "EXIT":
                sym = t.get("symbol", "UNKNOWN")
                coin_pnl[sym] = coin_pnl.get(sym, 0.0) + float(t.get("pnl", 0))
        except Exception:
            pass
    return coin_pnl


def read_3day_binance_pnl() -> float:
    """Sum PnL from the last 3 days of Binance trade files."""
    now = datetime.now(timezone.utc)
    total = 0.0
    for delta in range(3):
        day = (now - timedelta(days=delta)).strftime("%Y%m%d")
        f = PROJECT_ROOT / f"agents/trading-agent/trades/binance/trades_{day}.jsonl"
        if not f.exists():
            continue
        for line in f.read_text(errors="replace").splitlines():
            try:
                t = json.loads(line)
                if t.get("type") == "EXIT":
                    total += float(t.get("pnl", 0))
            except Exception:
                pass
    return total


# ── Process management ────────────────────────────────────────

def is_running(match: str) -> bool:
    try:
        out = subprocess.check_output(["pgrep", "-f", match], text=True)
        return bool(out.strip())
    except subprocess.CalledProcessError:
        return False


def restart_agent(script_rel: str, log_rel: str) -> str:
    """
    Kill any existing instance and launch a fresh one with nohup.
    Returns a human-readable action string.
    """
    name = Path(script_rel).name
    script_path = PROJECT_ROOT / script_rel
    log_path    = PROJECT_ROOT / log_rel

    if not script_path.exists():
        return f"SKIP restart {name} — script not found at {script_path}"

    # Kill existing
    subprocess.run(["pkill", "-f", name], capture_output=True)
    time.sleep(2)

    # Restart
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        log_fh = open(str(log_path), "a")
        subprocess.Popen(
            ["nohup", sys.executable, "-u", str(script_path)],
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
            start_new_session=True,
        )
        return f"RESTARTED {name}"
    except Exception as e:
        return f"FAILED to restart {name}: {e}"


# ── Main analysis ─────────────────────────────────────────────

def analyze_and_suggest() -> dict:
    now = datetime.now(timezone.utc)

    ea      = read_ea_state()
    binance = read_binance_state()

    ea_streak  = ea.get("streak", 0)
    ea_pnl     = ea.get("total_pnl", 0.0)
    ea_trades  = ea.get("trade_count", 0)

    binance_pnl    = binance.get("total_pnl", 0.0)
    binance_trades = binance.get("trade_count", 0)

    coin_pnl       = read_today_binance_trades(now)
    binance_3d_pnl = read_3day_binance_pnl()

    suggestions:  list[dict] = []
    actions_taken: list[str] = []

    # ── EA: process check + analysis ─────────────────────────
    if not is_running("liveea.py"):
        action = restart_agent("scripts/ea/liveea.py", "data/logs/liveea.log")
        actions_taken.append(action)

    if ea_streak <= -5:
        suggestions.append({
            "agent":      "EA",
            "type":       "streak_recovery",
            "message":    f"EA streak={ea_streak} (≤-5). Reset streak to -3 in state.json.",
            "auto_apply": True,
            "params": {
                "state_file":   "agents/trading-agent/trades/mt5/state.json",
                "streak_reset": -3,
            },
        })
    elif ea_streak <= -3:
        suggestions.append({
            "agent":      "EA",
            "type":       "streak_warning",
            "message":    f"EA streak={ea_streak} (≤-3). Monitor closely; consider tightening min_score.",
            "auto_apply": False,
            "params": {},
        })

    # ── Binance: process check + analysis ────────────────────
    if not is_running("live_trading_binance.py"):
        action = restart_agent(
            "agents/trading-agent/live_trading_binance.py",
            "data/logs/live_trading_binance.log",
        )
        actions_taken.append(action)

    if binance_3d_pnl < -50:
        suggestions.append({
            "agent":      "Binance",
            "type":       "3day_pnl_negative",
            "message":    f"Binance 3-day PnL = ${binance_3d_pnl:.2f} (< -$50). Review open positions and reduce exposure.",
            "auto_apply": False,
            "params":     {"3day_pnl": binance_3d_pnl},
        })

    worst_coin = (
        min(coin_pnl, key=lambda k: coin_pnl[k]) if coin_pnl else None
    )
    if worst_coin and coin_pnl[worst_coin] < -30:
        suggestions.append({
            "agent":      "Binance",
            "type":       "remove_coin",
            "message":    (
                f"Remove {worst_coin} from today's trading "
                f"(PnL = ${coin_pnl[worst_coin]:.2f})."
            ),
            "auto_apply": False,
            "params":     {"coin": worst_coin, "today_pnl": coin_pnl[worst_coin]},
        })

    # ── Write suggestions JSON ────────────────────────────────
    output = {
        "generated_at":      now.isoformat(),
        "ea_streak":         ea_streak,
        "ea_total_pnl":      ea_pnl,
        "ea_trades":         ea_trades,
        "binance_total_pnl": binance_pnl,
        "binance_3d_pnl":    binance_3d_pnl,
        "binance_trades":    binance_trades,
        "coin_pnl_today":    coin_pnl,
        "suggestions":       suggestions,
        "actions_taken":     actions_taken,
    }

    SUGGESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUGGESTIONS_FILE.write_text(json.dumps(output, indent=2))

    # ── Obsidian daily session log ────────────────────────────
    day_file = OBSIDIAN_SESSION / f"{now.strftime('%Y-%m-%d')}-automode.md"
    try:
        with open(day_file, "a") as f:
            f.write(f"\n## Trading Loop {now.strftime('%H:%M:%S UTC')}\n")
            f.write(f"- EA: streak={ea_streak} pnl=${ea_pnl:.2f} trades={ea_trades}\n")
            f.write(
                f"- Binance: pnl=${binance_pnl:.2f} "
                f"3d_pnl=${binance_3d_pnl:.2f} "
                f"trades={binance_trades}\n"
            )
            for a in actions_taken:
                f.write(f"- ACTION: {a}\n")
            for s in suggestions:
                f.write(
                    f"- SUGGESTION [{s['agent']}|{s['type']}]: {s['message']}\n"
                )
            if not actions_taken and not suggestions:
                f.write("- All systems nominal.\n")
            f.write("\n---\n")
    except Exception as e:
        print(f"[TradingLoop] Warning: could not write Obsidian log: {e}", file=sys.stderr)

    # ── Console summary ───────────────────────────────────────
    print(
        f"[TradingLoop] EA streak={ea_streak} pnl=${ea_pnl:.2f} | "
        f"Binance 3d_pnl=${binance_3d_pnl:.2f}"
    )
    print(
        f"[TradingLoop] suggestions={len(suggestions)} "
        f"actions={len(actions_taken)}"
    )
    if actions_taken:
        for a in actions_taken:
            print(f"[TradingLoop]   ACTION: {a}")
    if suggestions:
        for s in suggestions:
            print(f"[TradingLoop]   SUGGESTION [{s['agent']}]: {s['message']}")

    return output


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    result = analyze_and_suggest()
    print(json.dumps(result, indent=2))
