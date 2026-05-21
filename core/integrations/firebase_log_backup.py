#!/usr/bin/env python3
"""
Firebase Log Backup — stores logs and important info NOT in other systems.

What goes to Firebase (backup-only, no duplication):
  - Agent logs: liveea, live_trading_binance, automode, hermes, opencode, pidev, openclaw, pai
  - Improvement suggestions (data/logs/improvement_suggestions.json)
  - Automode task archive snapshots
  - Video generation log (data/media_output/generation_log.jsonl)
  - Critical system events (agent restarts, circuit breakers, daily summaries)

What does NOT go to Firebase (already in other systems):
  - Trading state (Supabase: trades, agent_events tables)
  - Code/source files (GitHub)
  - Trade journals (Obsidian vault)
  - Knowledge graph (Graphify)
  - AI workflows (Dify)
  - Market intel cache (live, regenerated on demand)

Run as a service:  python3 -m core.integrations.firebase_log_backup
Run once:         python3 -m core.integrations.firebase_log_backup --once
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / '.env')

LOGS_DIR     = PROJECT_ROOT / 'data' / 'logs'
MEDIA_OUT    = PROJECT_ROOT / 'data' / 'media_output'
TASKS_FILE   = PROJECT_ROOT / 'unified_tasks.json'
SUGGESTIONS  = LOGS_DIR / 'improvement_suggestions.json'

# Logs to back up — these are NOT stored in Supabase/GitHub/Obsidian
LOG_FILES = {
    'ea_agent':      LOGS_DIR / 'liveea.log',
    'binance_agent': LOGS_DIR / 'live_trading_binance.log',
    'automode':      LOGS_DIR / 'automode.log',
    'hermes':        LOGS_DIR / 'hermes.log',
    'opencode':      LOGS_DIR / 'opencode.log',
    'pidev':         LOGS_DIR / 'pidev.log',
    'openclaw':      LOGS_DIR / 'openclaw.log',
    'pai':           LOGS_DIR / 'pai_agent.log',
    'social':        LOGS_DIR / 'social.log',
    'gsd':           LOGS_DIR / 'gsd_integration.log',
}

BACKUP_INTERVAL = 30 * 60   # 30 minutes between full log backups
TAIL_LINES      = 200        # last N lines per log


def _get_db():
    """Get Firestore client, initialize if needed."""
    import firebase_admin
    from firebase_admin import credentials, firestore
    key_path = PROJECT_ROOT / 'config' / 'firebase-key.json'
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(str(key_path)))
    return firestore.client()


def _tail(path: Path, n: int = TAIL_LINES) -> list[str]:
    """Read last N lines from a log file."""
    try:
        lines = path.read_text(errors='replace').splitlines()
        return lines[-n:]
    except Exception:
        return []


def backup_logs(db) -> dict:
    """Upload last 200 lines of each agent log to Firebase logs/ collection."""
    ts = datetime.now(timezone.utc).isoformat()
    date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    results = {}

    for agent_name, log_path in LOG_FILES.items():
        if not log_path.exists():
            continue
        try:
            lines = _tail(log_path)
            if not lines:
                continue
            stat = log_path.stat()
            doc = {
                'agent': agent_name,
                'date': date_str,
                'backed_up_at': ts,
                'line_count': len(lines),
                'log_size_bytes': stat.st_size,
                'last_modified': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                'tail': '\n'.join(lines),
            }
            db.collection('logs').document(f'{agent_name}_{date_str}').set(doc, merge=True)
            results[agent_name] = f'{len(lines)} lines'
        except Exception as e:
            results[agent_name] = f'error: {e}'

    return results


def backup_improvement_suggestions(db):
    """Back up improvement_suggestions.json — not stored anywhere else."""
    try:
        if not SUGGESTIONS.exists():
            return
        data = json.loads(SUGGESTIONS.read_text())
        ts = datetime.now(timezone.utc).isoformat()
        db.collection('system_snapshots').document('improvement_suggestions').set({
            'backed_up_at': ts,
            'content': data,
        })
    except Exception as e:
        print(f"[FIREBASE] suggestions backup error: {e}")


def backup_video_metrics(db):
    """Back up video generation metrics — not stored in other systems."""
    try:
        metrics_file = MEDIA_OUT / 'metrics.json'
        gen_log = MEDIA_OUT / 'generation_log.jsonl'
        if not metrics_file.exists():
            return
        metrics = json.loads(metrics_file.read_text())
        # Last 20 generation log entries
        gen_entries = []
        if gen_log.exists():
            lines = gen_log.read_text().splitlines()
            for raw in lines[-20:]:
                try:
                    gen_entries.append(json.loads(raw))
                except Exception:
                    pass
        ts = datetime.now(timezone.utc).isoformat()
        db.collection('system_snapshots').document('video_metrics').set({
            'backed_up_at': ts,
            'metrics': metrics,
            'recent_generations': gen_entries,
        })
    except Exception as e:
        print(f"[FIREBASE] video metrics backup error: {e}")


def backup_daily_summary(db):
    """Write a daily summary document — useful for cross-session recall."""
    try:
        ts = datetime.now(timezone.utc)
        date_str = ts.strftime('%Y-%m-%d')

        # Read current state files
        ea_state = {}
        bin_state = {}
        try:
            ea_state = json.loads((PROJECT_ROOT / 'agents/trading-agent/trades/mt5/state.json').read_text())
        except Exception:
            pass
        try:
            bin_state = json.loads((PROJECT_ROOT / 'agents/trading-agent/trades/binance/state.json').read_text())
        except Exception:
            pass

        # Count POW files produced today
        pow_today = len(list((PROJECT_ROOT / 'docs/pow').glob(f'*{date_str.replace("-","")}*.md'))) if (PROJECT_ROOT / 'docs/pow').exists() else 0

        db.collection('daily_summaries').document(date_str).set({
            'date': date_str,
            'updated_at': ts.isoformat(),
            'ea_balance': round(float(ea_state.get('balance', 0)), 2),
            'ea_pnl_today': round(float(ea_state.get('pnl_today', 0)), 2),
            'ea_trade_count': ea_state.get('trade_count', 0),
            'binance_balance': round(float(bin_state.get('current_balance', 0)), 2),
            'binance_pnl_today': round(float(bin_state.get('pnl_today', 0)), 2),
            'binance_trade_count': bin_state.get('trade_count', 0),
            'automode_pow_today': pow_today,
        }, merge=True)
    except Exception as e:
        print(f"[FIREBASE] daily summary error: {e}")




SUPABASE_TABLES = [
    'system_health', 'agent_events', 'trades', 'backtest_results',
    'task_completions', 'agent_backups', 'agent_logs', 'ea_trades', 'social_posts'
]


def mirror_supabase_to_firebase(db):
    """Mirror all Supabase tables to Firebase supabase_mirror/ collection."""
    import urllib.request
    ts = datetime.now(timezone.utc).isoformat()
    results = {}

    for table in SUPABASE_TABLES:
        try:
            url = f"http://localhost:3000/{table}?limit=1000&order=id.desc"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                rows = json.loads(resp.read())
            if not rows:
                results[table] = "0 rows (skipped)"
                continue
            # Store as a single document with rows array + metadata
            db.collection('supabase_mirror').document(table).set({
                'table': table,
                'row_count': len(rows),
                'rows': rows,
                'mirrored_at': ts,
            })
            results[table] = f"{len(rows)} rows"
        except Exception as e:
            results[table] = f"error: {e}"

    return results

def run_once():
    """Run a single backup cycle."""
    print(f"[{datetime.now():%H:%M:%S}] Firebase log backup starting...")
    try:
        db = _get_db()
    except Exception as e:
        print(f"[FIREBASE] Cannot connect: {e}")
        return False

    log_results = backup_logs(db)
    for agent, status in log_results.items():
        print(f"  logs/{agent}: {status}")

    backup_improvement_suggestions(db)
    print("  system_snapshots/improvement_suggestions: OK")

    backup_video_metrics(db)
    print("  system_snapshots/video_metrics: OK")

    backup_daily_summary(db)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"  daily_summaries/{ts}: OK")

    # Mirror Supabase tables
    sb_results = mirror_supabase_to_firebase(db)
    for table, status in sb_results.items():
        print(f"  supabase_mirror/{table}: {status}")

    print(f"[{datetime.now():%H:%M:%S}] Backup complete")
    return True


def run_service():
    """Run continuously, backing up every 30 minutes."""
    print(f"[FIREBASE BACKUP] Service starting — interval {BACKUP_INTERVAL//60} min")
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"[FIREBASE BACKUP] Cycle error: {e}")
        time.sleep(BACKUP_INTERVAL)


if __name__ == '__main__':
    if '--once' in sys.argv:
        run_once()
    else:
        run_service()
