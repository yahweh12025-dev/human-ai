#!/usr/bin/env python3
"""
push_binance_trades.py
Offline utility: parse Binance trading agent JSONL logs from the trades/binance directory,
and push trade events to a dedicated Supabase table `public.binance_trades`.

This mirrors the approach used by mt5_node/tools/push_mt5_trades.py.

Usage:
    python3 push_binance_trades.py [--log-dir PATH] [--lookback-days N] [--dry-run]
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG_DIR = Path(__file__).parent / "trades" / "binance"

def _sanitize_text(value: str) -> str:
    """Escape single quotes for psql literal strings."""
    return value.replace("'", "''")

def _run_psql(sql: str) -> bool:
    """
    Run a single SQL statement via psql inside the Hermes-managed
    supabase-selfhosted-db-1 container.
    Returns True on success, False otherwise.
    """
    env = os.environ.copy()
    env.setdefault("PGCONNECT_TIMEOUT", "5")
    try:
        result = subprocess.run(
            ["docker", "exec", "supabase-selfhosted-db-1", "psql", "-U", "postgres", "-d", "human_ai", "-c", sql],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        combined = (result.stdout or "") + (result.stderr or "")
        if "INSERT" in combined or "CREATE TABLE" in combined:
            return True
        print(f"[PSQL] unexpected output: {combined[:200]}", flush=True)
        return False
    except subprocess.TimeoutExpired:
        print("[PSQL] timeout", flush=True)
        return False
    except FileNotFoundError:
        print("[PSQL] docker/psql not found", flush=True)
        return False
    except Exception as exc:
        print(f"[PSQL] {exc}", flush=True)
        return False

def ensure_table():
    """Create binance_trades table if it does not exist."""
    sql = """
    CREATE TABLE IF NOT EXISTS public.binance_trades (
        id BIGSERIAL PRIMARY KEY,
        agent TEXT NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        amount NUMERIC NOT NULL,
        price NUMERIC NOT NULL,
        data JSONB,
        timestamp TIMESTAMPTZ NOT NULL
    );
    """
    _run_psql(sql)

def collect_trades(log_dir: Path, lookback_days: int = 30) -> list:
    """
    Walk trades_YYYYMMDD.jsonl files within the lookback window and yield trade dicts.
    """
    if not log_dir.is_dir():
        return []
    cutoff_ts = datetime.now(timezone.utc).timestamp() - (lookback_days * 86400)
    trades = []
    # Match files like trades_20260520.jsonl
    for file in sorted(log_dir.glob("trades_*.jsonl")):
        try:
            file_mtime = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if file_mtime.timestamp() < cutoff_ts:
            continue
        try:
            with file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        trade = json.loads(line)
                        # Normalize: ensure required keys exist
                        trades.append(trade)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[WARN] reading {file}: {e}", flush=True)
    return trades

def push_trades(trades: list, dry_run: bool = False) -> int:
    """
    Insert trades into public.binance_trades.
    Each trade is deduplicated by (symbol, side, order_id, timestamp) within this run.
    """
    if not trades:
        return 0
    ensure_table()
    pushed = 0
    seen = set()
    for t in trades:
        symbol = t.get("symbol", "").strip()
        side = t.get("side", "").strip().upper()
        # qty: the field is 'qty' in our logs; also known as amount
        qty = t.get("qty")
        if qty is None:
            # fallback to 'amount' if present
            qty = t.get("amount", 0)
        price = t.get("price", 0)
        ts = t.get("timestamp")
        if not ts:
            ts = datetime.now(timezone.utc).isoformat()
        order_id = t.get("order_id")

        dedup_key = (symbol, side, order_id, ts)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Build data JSONB with all remaining fields
        data_fields = {k: v for k, v in t.items() if k not in ("symbol", "side", "qty", "amount", "price", "timestamp")}
        data_json = json.dumps(data_fields)

        sql = (
            "INSERT INTO public.binance_trades (agent, symbol, side, amount, price, data, timestamp) VALUES ("
            f"'{_sanitize_text('binance')}', "
            f"'{_sanitize_text(symbol)}', "
            f"'{_sanitize_text(side)}', "
            f"{qty}, "
            f"{price}, "
            f"'{_sanitize_text(data_json)}'::jsonb, "
            f"'{_sanitize_text(ts)}'"
            ") ON CONFLICT (symbol, side, timestamp) DO NOTHING;"
        )
        if dry_run:
            print(f"[DRY-RUN] {side} {symbol} {qty}@{price} ts={ts}", flush=True)
        else:
            if _run_psql(sql):
                pushed += 1
            else:
                print(f"[PUSH] Failed: {symbol} @ {price}", flush=True)
    return pushed

def main():
    parser = argparse.ArgumentParser(description="Push Binance trade logs to Supabase")
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR), help="Directory containing trades_*.jsonl files")
    parser.add_argument("--lookback-days", type=int, default=7, help="How many days of logs to process")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without DB insert")
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    if not log_dir.is_dir():
        print(f"[ERROR] Log dir not found: {log_dir}", flush=True)
        sys.exit(1)

    trades = collect_trades(log_dir, lookback_days=args.lookback_days)
    print(f"[PUSH] Collected {len(trades)} trades.", flush=True)
    if not trades:
        return

    # De-duplicate globally across files (some days may overlap)
    seen_global = set()
    unique_trades = []
    for t in trades:
        symbol = t.get("symbol", "")
        side = t.get("side", "").upper()
        price = t.get("price")
        ts = t.get("timestamp")
        key = (symbol, side, price, ts)
        if key not in seen_global:
            seen_global.add(key)
            unique_trades.append(t)
    print(f"[PUSH] {len(unique_trades)} unique after dedup.", flush=True)

    pushed = push_trades(unique_trades, dry_run=args.dry_run)
    print(f"[PUSH] Pushed {pushed}/{len(unique_trades)}.", flush=True)

if __name__ == "__main__":
    main()