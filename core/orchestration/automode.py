#!/usr/bin/env python3
"""
Auto Mode Controller v7
=======================
v7 improvements:
  - Video deduplication: generate unique seed per video, track used assets in
    data/media_output/VIDEO_INDEX.json — never reuse same images/clips
  - Unified_tasks.json auto-cleanup: archive failed tasks, cap completed at 50
  - GPT Researcher (NVIDIA free models) integrated into PAI + researcher task banks
  - DeepSeek browser agent + Pi.dev greedy search run parallel for research tasks
  - Better log indexing: _LOG_INDEX tracks last run of each task type
  - vault_log() called for all agent actions (openclaw, hermes, opencode, pidev)
  - _MAX_COMPLETED raised 30→50, _MAX_TASK_FAILURES 3→5
  - Task bank: hermes gets GPT-Research task, researcher gets NVIDIA-powered research

v6 improvements (retained):
  - Video output paths updated: trading → gdrive:videos/trading/
  - POW file path: data/logs/pow/
  - sync_obsidian_gdrive in backup task bank
  - freqtrade path: agents/freqtrade/

v5 fixes:
  - PENDING LOOP BUG FIXED: failed tasks are tracked with a failure counter.
    After _MAX_TASK_FAILURES retries the task is moved to 'failed' queue and
    never retried again, breaking the infinite pending loop.
  - FOLLOWUP/REVIEW tasks also respect the failure limit.
  - New 'failed' queue in task_queue stores permanently-failed tasks for audit.

v4 additions:
  - DEEPSEEK BROWSER AGENT: all agents can prompt DeepSeek for task ideas and
    research. Tasks containing "DeepSeek" are routed to prompt_deepseek utility.
  - PI.DEV GREEDY SEARCH: pi.dev tasks run recursive grep/find across entire repo
    for security and compliance verification.
  - OPENCLAW TASK GENERATION: openclaw monitors queue and consistently generates
    new tasks for all agents when queue falls below watermark.
  - CONSISTENT TASK GENERATION: pi.dev and openclaw both run every cycle to
    generate new tasks, ensuring the queue never runs dry.
  - ALL AGENT LOGGING: each agent action logged to data/logs/<agent>.log.

v3 features (retained):
  - IDLE TASK GENERATOR: when queue empties, agents create fresh tasks.
  - COMPLETED TASK PRUNING: archives old completed tasks.
  - PROACTIVE SELF-TASKING: per-agent task banks injected at low watermark.

v2 fixes (retained):
  - INFINITE LOOP BUG FIXED: REVIEW/FOLLOWUP tasks never spawn children.
  - None/missing IDs assigned; runaway chains pruned.
  - Self-healing on startup; --diagnose / --cleanup / --logs CLI.
"""

import json
import time
import signal
import sys
import os
import uuid
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_project_root))
os.chdir(str(_project_root))

# ── Constants ────────────────────────────────────────────────
_META_PREFIXES    = ('REVIEW-', 'FOLLOWUP-')
_MAX_ID_DEPTH     = 2
_LOW_WATERMARK    = 5    # inject new tasks when pending falls below this
_MAX_PENDING      = 20   # hard cap on total pending tasks
_MAX_COMPLETED    = 50   # v7: raised from 30 — keep more history
_MAX_TASK_FAILURES = 5   # v7: raised from 3 — more retries before permanent fail
_ARCHIVE_DIR     = _project_root / "data" / "task_archive"
_REVIEW_PRIORITY_THRESHOLD = 3
_DEEPSEEK_SCRIPT = _project_root / "scripts" / "utility" / "prompt_deepseek.py"
_LOG_DIR         = _project_root / "data" / "logs"
_POW_DIR         = _project_root / "data" / "logs" / "pow"

# ── Completed-task signature cooldown ────────────────────────
# Stores signature frozensets of recently completed task descriptions
# so inject_idle_tasks won't re-inject the same prompt until cooldown expires.
# Format: {frozenset: completed_at_timestamp}
_COMPLETED_TASK_SIGS: Dict = {}
_TASK_SIG_COOLDOWN_S = 4 * 60 * 60  # 4 hours — same task won't re-inject for 4h

# ── Trading improvement loop config ──────────────────────────
_TRADE_LOOP_SCRIPT   = _project_root / "core" / "orchestration" / "trading_improvement_loop.py"
_TRADE_LOOP_INTERVAL = 4 * 60 * 60   # run every 4 hours (in seconds)
_MONITOR_INTERVAL    = 30 * 60        # agent health check every 30 minutes
# Timestamp files tracking last run of each recurrent trading task
_TRADE_LAST_RUN_FILE = _LOG_DIR / "trade_loop_last_run.json"

# ── Per-agent proactive task banks ───────────────────────────
_AGENT_TASK_BANK: Dict[str, List] = {
    "hermes": [
        ("Review docs/roadmap.md — mark completed items, update Phase 4 priorities for EA trading, social media, and Binance scalper. Write updated roadmap to data/logs/pow/roadmap_update_{ts}.md.", "data/logs/pow/roadmap_update_{ts}.md", 1),
        ("Review the last 50 EA trades in agents/trading-agent/trades/mt5/trades_*.jsonl. Calculate win rate, avg hold time, PnL by symbol, top 3 signal improvements. Write findings to data/logs/pow/ea_trade_review_{ts}.md.", "data/logs/pow/ea_trade_review_{ts}.md", 1),
        ("Use DeepSeek browser agent to research: 'What are the best signal improvements for XAUUSD 1-minute scalping EA in 2025?' Save synthesis to data/logs/pow/deepseek_signal_research_{ts}.md.", "data/logs/pow/deepseek_signal_research_{ts}.md", 2),
        ("Design 3 new signal improvements for live_trading_ea.py based on price action (pin bar, inside bar, breakout retest). Write Python pseudocode to data/logs/pow/ea_signal_design_{ts}.md.", "data/logs/pow/ea_signal_design_{ts}.md", 2),
        ("Analyse automode.py completed task log. Identify which agents complete tasks fastest. Suggest 2 workflow improvements to data/logs/pow/automode_analysis_{ts}.md.", "data/logs/pow/automode_analysis_{ts}.md", 3),
        ("BACKUP-SYNC: Run bash scripts/system/sync_obsidian_gdrive.sh to sync Obsidian vault to GDrive, then run bash scripts/backup_supabase_to_gdrive.sh for Supabase backup. Write status to data/logs/pow/backup_sync_{ts}.md.", "data/logs/pow/backup_sync_{ts}.md", 3),
    ],
    "opencode": [
        ("Review agents/trading-agent/live_trading_ea.py — confirm RANGE regime min_score=4, prop-firm limits, and trailing stop correctness. Write findings to data/logs/pow/ea_code_review_{ts}.md.", "data/logs/pow/ea_code_review_{ts}.md", 1),
        ("Review data/logs/liveea.log and data/logs/live_trading_binance.log (last 200 lines each). Identify errors and missed trade opportunities. Write diagnostic to data/logs/pow/trading_log_review_{ts}.md.", "data/logs/pow/trading_log_review_{ts}.md", 1),
        ("Use DeepSeek browser agent to ask: 'What Python improvements can be made to a MetaTrader 5 EA signal executor using file-based IPC?' Save to data/logs/pow/deepseek_mt5_research_{ts}.md.", "data/logs/pow/deepseek_mt5_research_{ts}.md", 2),
        ("Verify Supabase: curl http://localhost:3000 and check PostgREST API responds. Write verification to data/logs/pow/supabase_verification_{ts}.md.", "data/logs/pow/supabase_verification_{ts}.md", 2),
        ("Review agents/trading-agent/live_trading_binance.py — confirm equity allocation, leverage tiers, signal gate. Write findings to data/logs/pow/binance_agent_review_{ts}.md.", "data/logs/pow/binance_agent_review_{ts}.md", 2),
    ],
    "pi.dev": [
        ("Greedy security scan: grep -rn 'password\\|api_key\\|secret\\|token' --include='*.py' agents/ apps/ core/ scripts/ | grep -v '.venv\\|#' | head -50. Write findings to data/logs/pow/security_scan_{ts}.md.", "data/logs/pow/security_scan_{ts}.md", 1),
        ("Greedy compliance audit: find all Python files in agents/trading-agent/ and verify each has proper error handling, no hardcoded credentials, and no bare except clauses. Write to data/logs/pow/trading_compliance_{ts}.md.", "data/logs/pow/trading_compliance_{ts}.md", 1),
        ("Use DeepSeek browser agent to ask: 'Critical security vulnerabilities in autonomous AI trading systems?' Cross-reference with codebase. Write to data/logs/pow/deepseek_security_{ts}.md.", "data/logs/pow/deepseek_security_{ts}.md", 2),
        ("Audit .gitignore — ensure .env, *.pid, trades/, logs/ are excluded. Run: git check-ignore .env agents/trading-agent/trades/ data/logs/ — report results to data/logs/pow/gitignore_audit_{ts}.md.", "data/logs/pow/gitignore_audit_{ts}.md", 2),
        ("Review the last 7 days of data/obsidian/trades/*.md. Verify EA and Binance records match. Report discrepancies to data/logs/pow/trade_reconciliation_{ts}.md.", "data/logs/pow/trade_reconciliation_{ts}.md", 3),
    ],
    "openclaw": [
        ("Trading agent health: read agents/trading-agent/trades/mt5/state.json and agents/trading-agent/trades/binance/state.json. Check (1) pnl_today vs daily loss limits (EA: -3%, Binance: -$300), (2) last_update age (flag if >10 min stale), (3) check ps aux for both agent processes. Write status to data/logs/pow/trading_health_{ts}.md.", "data/logs/pow/trading_health_{ts}.md", 1),
        ("Integration health: (1) check OpenRouter API via curl, (2) Supabase http://localhost:3000, (3) GDrive ls ~/gdrive/, (4) MT5 status file age. Write health report to data/logs/pow/integration_health_{ts}.md.", "data/logs/pow/integration_health_{ts}.md", 1),
        ("Check data/feeds/ea_live_trades.jsonl and data/feeds/binance_live_trades.jsonl. Count records, find last trade timestamp. Write feed health to data/logs/pow/swarm_feed_check_{ts}.md.", "data/logs/pow/swarm_feed_check_{ts}.md", 2),
        ("Use DeepSeek browser agent to ask: 'Best practices for multi-agent coordination in autonomous trading?' Extract 3 actionable tasks, add to unified_tasks.json. Write to data/logs/pow/deepseek_swarm_research_{ts}.md.", "data/logs/pow/deepseek_swarm_research_{ts}.md", 2),
        ("Review config/social_cron.yaml — validate YAML syntax and posting schedule. Write fixes to data/logs/pow/social_cron_review_{ts}.md.", "data/logs/pow/social_cron_review_{ts}.md", 3),
        ("Daily P&L circuit breaker check: read data/feeds/ea_live_trades.jsonl and data/feeds/binance_live_trades.jsonl, sum today's realized P&L. If total daily loss exceeds 2% of equity, write HALT signal to data/signals/circuit_breaker.json and report to data/logs/pow/pnl_circuit_check_{ts}.md.", "data/logs/pow/pnl_circuit_check_{ts}.md", 1),
    ],
    "researcher": [
        ("Use DeepSeek browser agent to research current XAUUSD/XAGUSD market: Fear & Greed index, recent price action, key levels, upcoming economic events. Write to data/logs/pow/metals_market_brief_{ts}.md.", "data/logs/pow/metals_market_brief_{ts}.md", 1),
        ("Use DeepSeek browser agent: research top 3 crypto scalping strategies for BTC/USDT futures 2025. Write findings to data/logs/pow/scalping_research_{ts}.md.", "data/logs/pow/scalping_research_{ts}.md", 2),
        ("NVIDIA-GPT-Research: Use GPT Researcher with NVIDIA NIM (deepseek-v4-flash free model) to research: 'Best multi-agent trading system improvements 2025 Python GitHub'. Run: OPENAI_API_KEY=$(grep NVIDIA_API_KEY .env|cut -d= -f2) OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1 FAST_LLM=openai:deepseek-ai/deepseek-v4-flash python3 agents/researcher_agent.py 'best multi-agent trading swarm improvements Python 2025' --vault --agent researcher. Write to data/logs/pow/nvidia_research_{ts}.md.", "data/logs/pow/nvidia_research_{ts}.md", 2),
        ("Review agents/trading-agent/strategies/ — identify what improvements are needed for multi-timeframe confirmation. Write analysis to data/logs/pow/strategy_review_{ts}.md.", "data/logs/pow/strategy_review_{ts}.md", 3),
    ],
    # ── Trading improvement recurrence tasks ─────────────────────────────────
    # These tasks use recurs=True and cooldown_hours so they re-inject themselves.
    # The task bank tuples are (description, pow_template, priority) as usual;
    # the scheduler logic in inject_idle_tasks handles dedup by signature.
    # Actual cooldown enforcement lives in _TRADE_TASK_COOLDOWNS below.
    # ─────────────────────────────────────────────────────────────────────────
    "hermes_trade": [
        (
            "HERMES-TRADE-REVIEW: Read data/logs/liveea.log and data/logs/live_trading_binance.log "
            "(last 500 lines each). Analyze win/loss patterns, EA v10.1 streak, and PnL trends. "
            "If EA v10.1 streak <= -3 or Binance v9.1 3-day PnL negative, generate specific parameter "
            "improvements and write them to data/logs/improvement_suggestions.json. "
            "Check if REVERSE logic is firing (grep liveea.log for [REVERSE]) — if >5 occurrences "
            "in last hour, reduce RANGE min_score by 1 and write that change to improvement_suggestions.json. "
            "If Binance daily loss > -$200, write alert to data/logs/improvement_suggestions.json "
            "with auto_apply=false. "
            "Also write a Markdown summary to data/logs/pow/trade_review_{ts}.md.",
            "data/logs/pow/trade_review_{ts}.md",
            2,
        ),
    ],
    "opencode_trade": [
        (
            "OPENCODE-TRADE-IMPLEMENT: Read data/logs/improvement_suggestions.json. "
            "If the file is newer than 4 hours and contains auto_apply=true suggestions, "
            "apply the parameter changes to the relevant trading agent source file, "
            "restart the agent, and log what was changed to "
            "data/obsidian/sessions/{ts}-improvements.md.",
            "data/logs/pow/trade_implement_{ts}.md",
            3,
        ),
    ],
    "pidev_monitor": [
        (
            "PIDEV-AGENT-MONITOR: Check ps aux for liveea.py and live_trading_binance.py. "
            "If either is not running, restart it with nohup python3 -u <script> and append "
            "the action to data/obsidian/System_State/agent_health.md. "
            "Also call the trading improvement loop: "
            "python3 core/orchestration/trading_improvement_loop.py.",
            "data/logs/pow/agent_monitor_{ts}.md",
            1,
        ),
    ],
    # ── GSD: meta-prompting workflow automation ──────────────────────────────
    "gsd": [
        ("GSD: Review phase progress across all open phases. Run gsd-progress to check status and identify blockers. Write findings to data/logs/pow/gsd_progress_{ts}.md.", "data/logs/pow/gsd_progress_{ts}.md", 1),
        ("GSD: Audit recently changed Python files for code quality issues. Run gsd-code-review on agents/ and core/ directories. Write findings to data/logs/pow/gsd_code_review_{ts}.md.", "data/logs/pow/gsd_code_review_{ts}.md", 2),
        ("GSD: Run autonomous audit-to-fix pipeline on core/orchestration/. Identify issues, classify severity, generate fixes. Write report to data/logs/pow/gsd_audit_fix_{ts}.md.", "data/logs/pow/gsd_audit_fix_{ts}.md", 2),
        ("GSD: Update project documentation — verify CLAUDE.md and docs/ are accurate against current codebase. Write diff to data/logs/pow/gsd_docs_update_{ts}.md.", "data/logs/pow/gsd_docs_update_{ts}.md", 3),
        ("GSD: Map codebase with parallel mapper agents. Produce updated architecture summary in data/logs/pow/gsd_codebase_map_{ts}.md.", "data/logs/pow/gsd_codebase_map_{ts}.md", 3),
    ],
    # ── Social / Video production ────────────────────────────────────────────
    "social": [
        (
            "VIDEO-PRODUCE-BUY: Run python3 scripts/produce_video.py --signal BUY to generate a TikTok/YouTube Shorts video for the current gold BUY signal. After success, upload to gdrive:videos/trading/. Log output path and file size to data/logs/pow/video_produce_buy_{ts}.md.",
            "data/logs/pow/video_produce_buy_{ts}.md",
            2,
        ),
        (
            "VIDEO-PRODUCE-SELL: Run python3 scripts/produce_video.py --signal SELL to generate a TikTok/YouTube Shorts video for the current gold SELL signal. After success, upload to gdrive:videos/trading/. Log output path and file size to data/logs/pow/video_produce_sell_{ts}.md.",
            "data/logs/pow/video_produce_sell_{ts}.md",
            2,
        ),
        (
            "VIDEO-PRODUCE-UPDATE: Run python3 scripts/produce_video.py --topic 'XAUUSD daily market analysis and key levels' --platform youtube_shorts --duration 45 to generate a market update short. Upload to gdrive:videos/trading/. Log to data/logs/pow/video_produce_update_{ts}.md.",
            "data/logs/pow/video_produce_update_{ts}.md",
            3,
        ),
        (
            "FAITHNEXUS-VIDEO: Run python3 scripts/produce_faithnexus_video.py --auto "
            "to generate today's FaithNexus scripture video. Upload to gdrive:videos/christian/. "
            "Log result to data/logs/pow/faithnexus_video_{ts}.md.",
            "data/logs/pow/faithnexus_video_{ts}.md",
            2,
        ),
        (
            "VIDEO-SYNC-GDRIVE: Run rclone sync data/media_output/trading/all gdrive:videos/trading and rclone sync data/media_output/christian gdrive:videos/christian to ensure all produced videos are backed up to GDrive. Then update data/media_output/VIDEO_INDEX.json with new entries. Log to data/logs/pow/video_sync_{ts}.md.",
            "data/logs/pow/video_sync_{ts}.md",
            3,
        ),
        (
            "VIDEO-DEDUP-CHECK: Run python3 -c \"import json; from pathlib import Path; idx=json.loads(Path('data/media_output/VIDEO_INDEX.json').read_text()) if Path('data/media_output/VIDEO_INDEX.json').exists() else {'videos':[]}; names=[v['filename'] for v in idx.get('videos',[])]; dups=[n for n in names if names.count(n)>1]; print('Duplicates:', dups or 'none')\" to check for duplicate video names. Log to data/logs/pow/video_dedup_{ts}.md.",
            "data/logs/pow/video_dedup_{ts}.md",
            3,
        ),
    ],
    # ── PAI: Personal AI Infrastructure skills ───────────────────────────────
    "pai": [
        ("PAI Research: investigate latest algorithmic trading signal improvements for XAUUSD 1-min scalping. Use ExtractAlpha workflow. Write findings to data/logs/pow/pai_research_xauusd_{ts}.md.", "data/logs/pow/pai_research_xauusd_{ts}.md", 1),
        ("PAI ExtractWisdom: process the most recent data/logs/pow/ research files and extract highest-signal insights. Write consolidated wisdom to data/logs/pow/pai_wisdom_{ts}.md.", "data/logs/pow/pai_wisdom_{ts}.md", 2),
        ("PAI WorldThreatModel: stress-test the human-ai swarm trading strategy against 11 time horizons (6mo-50yr). Identify existential risks. Write to data/logs/pow/pai_threat_model_{ts}.md.", "data/logs/pow/pai_threat_model_{ts}.md", 2),
        ("PAI RootCauseAnalysis: examine the last 5 failed tasks in unified_tasks.json. Run 5-Whys analysis on the most common failure patterns. Write to data/logs/pow/pai_rca_{ts}.md.", "data/logs/pow/pai_rca_{ts}.md", 3),
        ("PAI SystemsThinking: analyse the agent communication loop in core/agent_communication_protocol.py for feedback loops and bottlenecks. Write leverage-point analysis to data/logs/pow/pai_systems_{ts}.md.", "data/logs/pow/pai_systems_{ts}.md", 3),
        ("PAI GPT-Research: Use GPTResearcher to investigate latest XAUUSD scalping strategies and macro gold catalysts. Run python3 agents/researcher_agent.py 'XAUUSD gold scalping strategies macro catalyst analysis 2026' --vault --agent pai. Write findings to data/logs/pow/gpt_research_{ts}.md.", "data/logs/pow/gpt_research_{ts}.md", 2),
    ],
}


# ── Log rotation ─────────────────────────────────────────────

_LOG_ROTATE_THRESHOLD_MB = 20   # rotate logs larger than this

def _rotate_large_logs() -> None:
    """
    Scan data/logs/ on startup and rotate any .log file over
    _LOG_ROTATE_THRESHOLD_MB MB.  The oversized file is renamed to
    {name}.log.bak (overwriting any previous backup) so the agent starts
    with a fresh empty file.

    This is a lightweight safety net — the RotatingFileHandler in
    core/utils/log_consolidator.py handles in-process rotation for agents
    that use get_logger().
    """
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    threshold = _LOG_ROTATE_THRESHOLD_MB * 1024 * 1024
    rotated: list = []
    try:
        for log_file in sorted(_LOG_DIR.glob("*.log")):
            try:
                if log_file.stat().st_size > threshold:
                    bak = log_file.with_suffix(".log.bak")
                    log_file.rename(bak)
                    log_file.touch()          # create fresh empty file
                    rotated.append(log_file.name)
            except Exception:
                pass
    except Exception:
        pass
    if rotated:
        _agent_log("automode", f"[ROTATE] Rotated {len(rotated)} oversized log(s): {rotated}")


# ── Agent log writer ─────────────────────────────────────────

def _agent_log(agent: str, msg: str):
    """Append a timestamped message to the agent's log file."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_name = agent.lower().replace('.', '').replace(' ', '_')
    log_file = _LOG_DIR / f"{log_name}.log"
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(log_file, 'a') as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


# ── DeepSeek browser agent integration ──────────────────────

def query_deepseek(prompt: str, agent: str = "automode", timeout: int = 120,
                   save_path: str = "") -> str:
    """
    Send a prompt to DeepSeek via the headless browser agent (Camoufox).
    Passes the question as a CLI argument (not stdin — script uses argparse).
    Returns the response text or empty string on failure.

    Prerequisites:
      - DEEPSEEK_EMAIL + DEEPSEEK_PASSWORD in .env, OR
      - Run scripts/utility/seed_deepseek_session.py once to log in manually
    """
    _agent_log(agent, f"[DEEPSEEK] Querying: {prompt[:100]}")

    ds_script = _project_root / "scripts" / "utility" / "prompt_deepseek.py"
    if not ds_script.exists():
        _agent_log(agent, "[DEEPSEEK] Script not found")
        return ""

    cmd = [sys.executable, str(ds_script), prompt]
    if save_path:
        cmd += ["--save", save_path]

    env = {
        **os.environ,
        "DISPLAY": os.environ.get("DISPLAY", ":11"),
        "DEEPSEEK_PROMPT": prompt,   # fallback env var
    }

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, cwd=str(_project_root), env=env
        )
        if result.returncode == 0:
            # Extract just the response (after "--- RESPONSE ---" marker)
            out = result.stdout
            if "--- RESPONSE ---" in out:
                response = out.split("--- RESPONSE ---", 1)[1].strip()
            else:
                response = out.strip()
            if response:
                _agent_log(agent, f"[DEEPSEEK] Got {len(response)} chars")
                return response
            _agent_log(agent, f"[DEEPSEEK] Empty response (exit 0)")
        else:
            stderr_snippet = result.stderr[-300:] if result.stderr else ""
            _agent_log(agent, f"[DEEPSEEK] Exit {result.returncode}: {stderr_snippet[:200]}")
            # If not logged in, log a clear instruction
            if "DEEPSEEK_EMAIL" in result.stdout or "seed_deepseek_session" in result.stdout:
                _agent_log(agent, "[DEEPSEEK] ACTION NEEDED: add DEEPSEEK_EMAIL+PASSWORD to .env "
                           "or run scripts/utility/seed_deepseek_session.py once")
    except subprocess.TimeoutExpired:
        _agent_log(agent, f"[DEEPSEEK] Timeout after {timeout}s")
    except Exception as e:
        _agent_log(agent, f"[DEEPSEEK] Error: {e}")

    return f"[DeepSeek unavailable — session may need seeding via scripts/utility/masterseed.py]"


# ── Pi.dev greedy search ─────────────────────────────────────

def pidev_greedy_search(pattern: str, paths: List[str] = None,
                        file_types: List[str] = None, agent: str = "pi.dev") -> str:
    """
    Pi.dev greedy search: recursive grep across the codebase.
    Returns findings as a formatted string.
    """
    if paths is None:
        paths = ["agents", "apps", "core", "scripts"]
    if file_types is None:
        file_types = ["*.py", "*.yaml", "*.yml", "*.json", "*.sh"]

    _agent_log(agent, f"[GREEDY] Searching for: {pattern} in {paths}")
    results = []

    for search_path in paths:
        full_path = _project_root / search_path
        if not full_path.exists():
            continue
        for ft in file_types:
            try:
                r = subprocess.run(
                    ["grep", "-rn", "--include", ft, pattern, str(full_path)],
                    capture_output=True, text=True, timeout=30
                )
                if r.stdout.strip():
                    results.append(r.stdout.strip())
            except Exception:
                pass

    combined = "\n".join(results)
    _agent_log(agent, f"[GREEDY] Found {len(combined.splitlines())} matching lines")
    return combined or f"[No matches for '{pattern}' in {paths}]"


def _is_meta_task(task_id: str) -> bool:
    if not task_id:
        return False
    return any(str(task_id).startswith(p) for p in _META_PREFIXES)


def _id_depth(task_id: str) -> int:
    if not task_id:
        return 0
    return len(re.findall(r'(?:REVIEW|FOLLOWUP)-', str(task_id)))


# ── Log reader utility ────────────────────────────────────────

class AgentLogReader:
    LOG_DIR = _LOG_DIR

    AGENT_LOGS = {
        'automode':   'automode.log',
        'openclaw':   'openclaw.log',
        'hermes':     'hermes.log',
        'opencode':   'opencode.log',
        'pi.dev':     'pidev.log',
        'researcher': 'researcher.log',
        'liveea':     'liveea.log',
        'binance':    'live_trading_binance.log',
        'social':     'social_media.log',
        'gsd':        'gsd_integration.log',
        'pai':        'pai_agent.log',
    }

    @classmethod
    def read_recent(cls, log_name: str, lines: int = 50) -> str:
        path = cls.LOG_DIR / log_name
        if not path.exists():
            return f"[Log not found: {path}]"
        try:
            all_lines = path.read_text(errors='replace').splitlines()
            return '\n'.join(all_lines[-lines:])
        except Exception as e:
            return f"[Error reading {path}: {e}]"

    @classmethod
    def find_errors(cls, log_name: str, window: int = 200) -> List[str]:
        content = cls.read_recent(log_name, window)
        return [l for l in content.splitlines()
                if any(kw in l for kw in ('ERROR', 'Error', 'EXCEPTION', 'Traceback',
                                           'failed', 'FAILED', '💥', '❌'))]

    @classmethod
    def agent_log(cls, agent: str, lines: int = 50) -> str:
        log_file = cls.AGENT_LOGS.get(agent.lower().replace('.', ''))
        if not log_file:
            log_file = f"{agent.lower()}.log"
        return cls.read_recent(log_file, lines)

    @classmethod
    def automode_errors(cls) -> List[str]:
        return cls.find_errors('automode.log')

    @classmethod
    def summarise_all(cls) -> str:
        lines = ["=== Log Health Summary ==="]
        for agent, log_file in cls.AGENT_LOGS.items():
            errors = cls.find_errors(log_file, 100)
            path = cls.LOG_DIR / log_file
            size = f"{path.stat().st_size//1024}KB" if path.exists() else "missing"
            lines.append(f"  {agent:<12} [{size}]  errors={len(errors)}")
        return '\n'.join(lines)


# ── Queue health / cleanup ────────────────────────────────────

def diagnose_queue(tasks_file: Path) -> Dict:
    if not tasks_file.exists():
        return {"error": "tasks file not found"}
    with open(tasks_file) as f:
        data = json.load(f)
    tq = data.get('task_queue', {})
    pending = tq.get('pending', [])
    report = {
        "total_pending":    len(pending),
        "no_id":            [t.get('task','')[:50] for t in pending if not t.get('id')],
        "meta_tasks":       [t['id'] for t in pending if _is_meta_task(t.get('id',''))],
        "runaway_chains":   [t['id'] for t in pending if _id_depth(t.get('id','')) > _MAX_ID_DEPTH],
        "in_progress":      len(tq.get('in_progress', [])),
        "completed":        len(tq.get('completed', [])),
    }
    report["health"] = "GOOD" if not report["runaway_chains"] and not report["no_id"] else "NEEDS_CLEANUP"
    return report


def prune_completed(tasks_file: Path) -> int:
    if not tasks_file.exists():
        return 0
    with open(tasks_file) as f:
        data = json.load(f)
    tq = data.setdefault('task_queue', {})
    completed = tq.get('completed', [])
    if len(completed) <= _MAX_COMPLETED:
        return 0
    to_archive = completed[:-_MAX_COMPLETED]
    to_keep    = completed[-_MAX_COMPLETED:]
    _ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_file = _ARCHIVE_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    with open(archive_file, 'a') as f:
        for t in to_archive:
            f.write(json.dumps(t) + '\n')
    tq['completed'] = to_keep
    with open(tasks_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"📦 Archived {len(to_archive)} completed tasks → {archive_file.name}")
    return len(to_archive)


def inject_idle_tasks(tasks_file: Path, agent_name: Optional[str] = None,
                      low_watermark: int = _LOW_WATERMARK) -> int:
    if not tasks_file.exists():
        return 0
    with open(tasks_file) as f:
        data = json.load(f)
    tq   = data.setdefault('task_queue', {})
    pending = tq.get('pending', [])

    if len(pending) >= _MAX_PENDING:
        return 0

    if agent_name:
        relevant = [t for t in pending if t.get('agent','').lower() == agent_name.lower()]
    else:
        relevant = pending

    if len(relevant) >= low_watermark:
        return 0

    ts  = datetime.now().strftime('%Y%m%d_%H%M%S')
    agents = [agent_name.lower()] if agent_name else list(_AGENT_TASK_BANK.keys())
    added = 0
    pending_ids = {t.get('id','') for t in pending}

    def _sig(text: str) -> frozenset:
        # Use more words (12 instead of 8) and strip the {ts} substitution
        # so DeepSeek prompts with identical questions always match each other
        clean = re.sub(r'\d{8}_\d{6}', '', text)  # strip timestamps
        words = [w.lower() for w in clean.split() if len(w) > 4]
        return frozenset(words[:12])

    existing_sigs = {_sig(t.get('task', '')) for t in pending}

    # Also block re-injection of recently completed tasks (cooldown window)
    now_ts = time.time()
    # Prune expired cooldown entries
    expired = [k for k, v in _COMPLETED_TASK_SIGS.items() if now_ts - v > _TASK_SIG_COOLDOWN_S]
    for k in expired:
        del _COMPLETED_TASK_SIGS[k]
    # Merge completed sigs into existing for dedup check
    all_blocked_sigs = existing_sigs | set(_COMPLETED_TASK_SIGS.keys())

    for agent in agents:
        bank = _AGENT_TASK_BANK.get(agent, [])
        for task_desc, pow_template, priority in bank:
            if len(pending) >= _MAX_PENDING:
                break
            task_text = task_desc.replace('{ts}', ts)
            pow_file  = pow_template.replace('{ts}', ts)
            new_sig = _sig(task_text)
            if any(len(new_sig & s) >= 5 for s in all_blocked_sigs):
                continue
            new_id = f"{agent.upper().replace('.','')}-AUTO-{uuid.uuid4().hex[:8].upper()}"
            if new_id in pending_ids:
                continue
            new_task = {
                "id": new_id, "task": task_text, "agent": agent,
                "priority": priority, "status": "pending",
                "created_by": "idle_generator", "pow_file": pow_file,
                "created_at": datetime.now().isoformat(),
            }
            pending.append(new_task)
            pending_ids.add(new_id)
            existing_sigs.add(new_sig)
            added += 1
            if added >= low_watermark * len(agents):
                break
        if added >= low_watermark * len(agents):
            break

    if added:
        tq['pending'] = pending
        with open(tasks_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"💡 Injected {added} idle task(s) from agent task banks")

    return added


def cleanup_queue(tasks_file: Path) -> int:
    if not tasks_file.exists():
        return 0
    with open(tasks_file) as f:
        data = json.load(f)
    tq = data.setdefault('task_queue', {})
    pending = tq.get('pending', [])
    cleaned = []
    removed = 0
    assigned = 0
    for t in pending:
        tid = t.get('id')
        if not tid:
            t['id'] = f"TASK-{uuid.uuid4().hex[:8].upper()}"
            assigned += 1
        if _id_depth(t.get('id', '')) > _MAX_ID_DEPTH:
            removed += 1
            continue
        cleaned.append(t)
    tq['pending'] = cleaned
    with open(tasks_file, 'w') as f:
        json.dump(data, f, indent=2)
    if removed or assigned:
        print(f"🧹 Queue cleanup: removed {removed} runaway tasks, assigned {assigned} missing IDs")
    return removed


# ── Main controller ───────────────────────────────────────────

class AutoModeController:
    def __init__(self, agent_name: Optional[str] = None):
        self.project_root = _project_root
        self.tasks_file   = self.project_root / "unified_tasks.json"
        self.agent_name   = agent_name
        self.running      = False
        self.completed_tasks: List[str] = []
        self.failed_tasks:    List[str] = []
        self.log_reader   = AgentLogReader

        self.max_consecutive_failures = 3
        self.consecutive_failures     = 0
        self.sleep_interval           = 30
        self._task_failure_counts: Dict[str, int] = {}   # task_id → failure count

        self._reviewer_map = {
            'openclaw':     'pi.dev',
            'hermes':       'opencode',
            'opencode':     'pi.dev',
            'pi.dev':       'hermes',
            'pidev':        'hermes',
            'researcher':   'hermes',
            'freqtrade':    'pi.dev',
            'trading':      'pi.dev',
            'ea':           'pi.dev',
            'mt5':          'pi.dev',
            'social_media': 'hermes',
            'gsd':          'pi.dev',   # GSD outputs reviewed by pi.dev
            'pai':          'hermes',   # PAI research reviewed by hermes
        }

        signal.signal(signal.SIGINT,  self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _self_heal_on_startup(self):
        print("🔍 Self-healing check...")
        _rotate_large_logs()          # rotate oversized logs before writing more
        removed  = cleanup_queue(self.tasks_file)
        archived = prune_completed(self.tasks_file)
        injected = inject_idle_tasks(self.tasks_file, self.agent_name, _LOW_WATERMARK)
        errors = self.log_reader.automode_errors()
        if errors:
            print(f"   ⚠️  {len(errors)} error(s) in recent automode.log:")
            for e in errors[-3:]:
                print(f"      {e[:120]}")
        else:
            print("   ✅ No errors in recent automode.log")
        if self.agent_name:
            agent_errors = self.log_reader.find_errors(
                self.log_reader.AGENT_LOGS.get(self.agent_name.lower(), f"{self.agent_name.lower()}.log")
            )
            if agent_errors:
                print(f"   ⚠️  {len(agent_errors)} error(s) in {self.agent_name} log")
        report = diagnose_queue(self.tasks_file)
        print(f"   📋 Queue: {report['total_pending']} pending | "
              f"{report['in_progress']} in-progress | "
              f"{report['completed']} completed | "
              f"health={report['health']}")

    def start(self):
        print(f"🤖 Auto Mode v6 Starting...")
        print(f"   Agent : {self.agent_name or 'Multi-Agent Coordinator'}")
        print(f"   Tasks : {self.tasks_file}")
        print(f"   DeepSeek: {_DEEPSEEK_SCRIPT.exists()}")
        print(f"   Safety: max {self.max_consecutive_failures} consecutive failures")
        print(f"   Press Ctrl+C to stop\n")
        _agent_log('automode', f"v6 started — agent={self.agent_name or 'multi'}")
        self._self_heal_on_startup()
        self.running = True
        self._execution_loop()

    def _execution_loop(self):
        while self.running:
            try:
                tasks   = self._load_tasks()
                pending = self._get_pending_tasks(tasks)

                if pending:
                    print(f"\n📋 Found {len(pending)} pending task(s)")
                    for task in pending[:1]:
                        self._execute_task(task)
                else:
                    injected = inject_idle_tasks(self.tasks_file, self.agent_name, _LOW_WATERMARK)
                    if injected:
                        print(f"💡 Queue was empty — generated {injected} new task(s)")
                    else:
                        print(f"⏸️  No pending tasks. Waiting {self.sleep_interval}s...")
                        _agent_log('automode', "Queue empty — waiting")

                # ── Periodic trading improvement loop ────────────────────
                self._maybe_run_trading_loop()

                if self.running:
                    time.sleep(self.sleep_interval)

            except KeyboardInterrupt:
                print("\n⚠️  Shutdown requested...")
                self.running = False
                break
            except Exception as e:
                print(f"\n❌ Error in execution loop: {e}")
                _agent_log('automode', f"Loop error: {e}")
                self.consecutive_failures += 1
                if self.consecutive_failures >= self.max_consecutive_failures:
                    print(f"\n🛑 Safety stop: {self.max_consecutive_failures} consecutive failures")
                    self.running = False
                    break
                time.sleep(self.sleep_interval * 2)

        self._shutdown()

    def _load_tasks(self) -> Dict:
        if not self.tasks_file.exists():
            return {'task_queue': {'pending': []}}
        with open(self.tasks_file) as f:
            return json.load(f)

    def _get_pending_tasks(self, tasks_data: Dict) -> List[Dict]:
        all_pending = tasks_data.get('task_queue', {}).get('pending', [])
        if self.agent_name:
            agent_tasks = [t for t in all_pending
                           if t.get('agent', '').lower() == self.agent_name.lower()]
        else:
            agent_tasks = all_pending
        return sorted(agent_tasks,
                      key=lambda t: int(t['priority']) if str(t.get('priority','999')).isdigit() else 999)

    # ── Task execution ─────────────────────────────────────────

    def _execute_task(self, task: Dict) -> bool:
        task_id   = task.get('id') or f"TASK-{uuid.uuid4().hex[:8].upper()}"
        task_desc = task.get('task', 'No description')
        agent     = task.get('agent', 'unknown')
        pow_file  = task.get('pow_file')

        if not task.get('id'):
            task['id'] = task_id

        print(f"\n{'='*70}")
        print(f"🚀 Executing Task: {task_id}")
        print(f"   Description: {task_desc[:100]}")
        print(f"   Agent: {agent}")
        print(f"   Created by: {task.get('created_by', 'user')}")
        print(f"{'='*70}")
        _agent_log(agent, f"[TASK START] {task_id} — {task_desc[:80]}")

        self._update_task_status(task_id, 'in_progress')

        try:
            success = self._route_task_execution(task)

            if success:
                print(f"\n✅ Task completed: {task_id}")
                _agent_log(agent, f"[TASK DONE] {task_id}")
                self._update_task_status(task_id, 'completed')
                self.completed_tasks.append(task_id)
                self.consecutive_failures = 0

                # Record this task's signature in the cooldown map so it won't
                # re-inject until _TASK_SIG_COOLDOWN_S seconds have passed.
                task_text = task.get('task', '')
                if task_text:
                    def _sig_local(text: str) -> frozenset:
                        clean = re.sub(r'\d{8}_\d{6}', '', text)
                        words = [w.lower() for w in clean.split() if len(w) > 4]
                        return frozenset(words[:12])
                    _COMPLETED_TASK_SIGS[_sig_local(task_text)] = time.time()

                if len(self.completed_tasks) % 10 == 0:
                    prune_completed(self.tasks_file)

                task_priority = int(task.get('priority', 99))
                # Only create followup/review for substantive tasks (priority 1-2)
                # and never for DeepSeek tasks (they just re-queue the same prompt)
                is_deepseek = 'deepseek' in task_text.lower()
                if (not _is_meta_task(task_id)
                        and not is_deepseek
                        and task_priority <= 2):
                    self._create_followup_task(task)
                    self._create_review_task(task)
                else:
                    print(f"   ℹ️  Skipping review/followup (meta={_is_meta_task(task_id)}, deepseek={is_deepseek}, priority={task_priority})")

                inject_idle_tasks(self.tasks_file, self.agent_name, _LOW_WATERMARK)
                return True
            else:
                print(f"\n❌ Task failed: {task_id}")
                _agent_log(agent, f"[TASK FAIL] {task_id}")
                self.failed_tasks.append(task_id)
                self.consecutive_failures += 1
                self._task_failure_counts[task_id] = self._task_failure_counts.get(task_id, 0) + 1
                if self._task_failure_counts[task_id] >= _MAX_TASK_FAILURES:
                    print(f"   ⛔ Task {task_id} failed {_MAX_TASK_FAILURES}× — moving to 'failed' queue")
                    _agent_log(agent, f"[TASK PERMANENT FAIL] {task_id} after {_MAX_TASK_FAILURES} attempts")
                    self._update_task_status(task_id, 'failed')
                else:
                    retry = self._task_failure_counts[task_id]
                    print(f"   ♻️  Retry {retry}/{_MAX_TASK_FAILURES} for task {task_id}")
                    self._update_task_status(task_id, 'pending')
                return False

        except Exception as e:
            print(f"\n💥 Task exception: {e}")
            _agent_log(agent, f"[TASK EXCEPTION] {task_id}: {e}")
            self.failed_tasks.append(task_id)
            self.consecutive_failures += 1
            self._task_failure_counts[task_id] = self._task_failure_counts.get(task_id, 0) + 1
            if self._task_failure_counts[task_id] >= _MAX_TASK_FAILURES:
                print(f"   ⛔ Task {task_id} exception-failed {_MAX_TASK_FAILURES}× — moving to 'failed' queue")
                _agent_log(agent, f"[TASK PERMANENT FAIL] {task_id}: {e}")
                self._update_task_status(task_id, 'failed')
            else:
                self._update_task_status(task_id, 'pending')
            return False

    def _route_task_execution(self, task: Dict) -> bool:
        agent     = task.get('agent', '').lower()
        task_desc = task.get('task', '').lower()

        # DeepSeek research tasks — any agent
        if 'deepseek' in task_desc:
            return self._execute_deepseek_task(task)

        # Pi.dev with greedy search
        if agent in ('pi.dev', 'pidev') and any(kw in task_desc
                for kw in ('grep', 'greedy', 'scan', 'audit', 'find all', 'search')):
            return self._execute_pidev_task(task)

        # Trading improvement recurrence tasks
        if agent in ('hermes_trade', 'opencode_trade', 'pidev_monitor'):
            return self._execute_trading_improvement_task(task)
        # Also match on task ID prefix for explicit triggers
        task_id = task.get('id', '')
        if any(task_id.startswith(p) for p in ('HERMES-TRADE-', 'OPENCODE-TRADE-', 'PIDEV-AGENT-')):
            return self._execute_trading_improvement_task(task)

        # FaithNexus biblical video tasks
        if any(kw in task_desc.lower() for kw in ('faithnexus', 'faith video', 'scripture video', 'biblical video', 'faithnexus-video')):
            return self._execute_faithnexus_task(task)

        # Agent-specific routing
        if agent in ('openclaw', 'hermes', 'opencode', 'researcher', 'pi.dev', 'pidev'):
            return self._execute_generic_task(task)
        if agent == 'social_media' or 'social' in agent:
            return self._execute_social_task(task)
        if agent in ('freqtrade', 'trading') or ('freqtrade' in task_desc and 'trading' in agent):
            return self._execute_trading_task(task)
        if agent in ('ea', 'mt5') or ('mt5' in task_desc and 'ea' in agent):
            return self._execute_ea_task(task)
        # GSD meta-prompting tasks
        if agent == 'gsd' or task_desc.startswith('gsd:') or 'gsd-' in task_desc[:20]:
            return self._execute_gsd_task(task)
        # PAI Personal AI Infrastructure tasks
        if agent == 'pai' or task_desc.startswith('pai ') or task_desc.startswith('pai:'):
            return self._execute_pai_task(task)
        return self._execute_generic_task(task)

    # ── Specialized execution handlers ─────────────────────────

    def _execute_deepseek_task(self, task: Dict) -> bool:
        """Execute a DeepSeek research task — available to ALL agents."""
        agent     = task.get('agent', 'automode')
        task_desc = task.get('task', '')
        pow_file  = task.get('pow_file')

        # Extract the research question from the task description
        # Look for text in quotes, or just use the task itself
        import re as _re
        question_match = _re.search(r"['\"](.+?)['\"]", task_desc)
        question = question_match.group(1) if question_match else task_desc[:300]

        print(f"   → [DEEPSEEK] {agent} querying: {question[:80]}...")
        _agent_log(agent, f"[DEEPSEEK] Querying: {question[:80]}")

        # Pass save_path so the script writes directly — avoids POW file being empty on failure
        save_path = str(self.project_root / pow_file) if pow_file else ""
        response = query_deepseek(question, agent=agent, save_path=save_path)

        if not response:
            # DeepSeek unavailable — write a placeholder POW so task completes
            # (prevents infinite retry) and log the instruction
            print(f"   ⚠️  [DEEPSEEK] No response — session may need seeding")
            print(f"   ⚠️  Run: DISPLAY=:11 python3 scripts/utility/seed_deepseek_session.py")
            if pow_file:
                full_path = self.project_root / pow_file
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(
                    f"# DeepSeek Research — PENDING SESSION\n\n"
                    f"**Question:** {question}\n\n"
                    f"**Status:** Session not authenticated. "
                    f"Add DEEPSEEK_EMAIL/DEEPSEEK_PASSWORD to .env or run "
                    f"`seed_deepseek_session.py` once.\n"
                )
            return True  # mark complete so it doesn't retry endlessly

        if pow_file and not Path(save_path).exists():
            # Script didn't write file directly — write it here
            full_path = self.project_root / pow_file
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(
                f"# DeepSeek Research — {task.get('id')}\n\n"
                f"**Agent:** {agent}\n**Date:** {datetime.now().isoformat()}\n"
                f"**Question:** {question}\n\n## Response\n\n{response}\n"
            )
        print(f"   ✅ DeepSeek response saved: {pow_file or 'auto-path'}")
        _agent_log(agent, f"[DEEPSEEK] Response saved ({len(response)} chars)")
        return True

    def _execute_pidev_task(self, task: Dict) -> bool:
        """Pi.dev greedy search task execution."""
        agent     = task.get('agent', 'pi.dev')
        task_desc = task.get('task', '')
        pow_file  = task.get('pow_file')

        print(f"   → [PI.DEV GREEDY] Scanning codebase...")
        _agent_log(agent, f"[GREEDY] Task: {task_desc[:80]}")

        # Extract grep pattern from the task description
        import re as _re
        grep_match = _re.search(r"grep\s+.*?['\"](.+?)['\"]", task_desc)
        pattern = grep_match.group(1) if grep_match else "api_key|password|secret|token"

        results = pidev_greedy_search(pattern, agent=agent)
        _agent_log(agent, f"[GREEDY] Found {len(results.splitlines())} results")

        if pow_file:
            full_path = self.project_root / pow_file
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(
                f"# Pi.dev Greedy Search — {task.get('id')}\n\n"
                f"**Agent:** {agent}\n"
                f"**Date:** {datetime.now().isoformat()}\n"
                f"**Pattern:** {pattern}\n\n"
                f"## Findings\n\n```\n{results}\n```\n\n"
                f"## Task\n\n{task_desc}\n"
            )
            print(f"   ✅ Greedy search results saved: {pow_file}")

        return True

    def _execute_gsd_task(self, task: Dict) -> bool:
        """Execute a GSD (Get Shit Done) meta-prompting skill task."""
        agent     = task.get('agent', 'gsd')
        task_desc = task.get('task', '')
        pow_file  = task.get('pow_file')

        print("   → Routing to GSD skill integration...")
        _agent_log(agent, f"[GSD] Task: {task_desc[:80]}")

        try:
            from core.gsd_integration import invoke_gsd_skill, GSD_SKILL_MAP

            # Determine which GSD skill to invoke from the task description
            skill_name = 'gsd-progress'   # default
            task_lower = task_desc.lower()
            if 'code review' in task_lower or 'code-review' in task_lower:
                skill_name = 'gsd-code-review'
            elif 'audit' in task_lower and 'fix' in task_lower:
                skill_name = 'gsd-audit-fix'
            elif 'progress' in task_lower or 'status' in task_lower:
                skill_name = 'gsd-progress'
            elif 'map codebase' in task_lower or 'codebase map' in task_lower:
                skill_name = 'gsd-map-codebase'
            elif 'docs' in task_lower or 'document' in task_lower:
                skill_name = 'gsd-docs-update'
            elif 'plan' in task_lower and 'phase' in task_lower:
                skill_name = 'gsd-plan-phase'
            elif 'debug' in task_lower:
                skill_name = 'gsd-debug'
            elif 'validate' in task_lower:
                skill_name = 'gsd-validate-phase'
            # Extract explicit gsd- skill name if present in task
            import re as _re
            m = _re.search(r'(gsd-[\w-]+)', task_desc)
            if m and m.group(1) in GSD_SKILL_MAP:
                skill_name = m.group(1)

            result = invoke_gsd_skill(
                skill_name,
                context=task_desc,
                pow_file=pow_file,
            )
            if result['success']:
                print(f"   ✅ GSD skill completed: {skill_name}")
                _agent_log(agent, f"[GSD DONE] {skill_name}")
            else:
                print(f"   ⚠️  GSD skill {skill_name} failed: {result['error'][:80]}")
                _agent_log(agent, f"[GSD FAIL] {skill_name}: {result['error'][:80]}")
                # Fall through to generic POW on failure
                if pow_file:
                    self._create_pow_file(pow_file, task)
            return result['success']

        except Exception as e:
            print(f"   GSD task error: {e}")
            _agent_log(agent, f"[GSD EXCEPTION] {e}")
            return self._execute_generic_task(task)

    def _execute_pai_task(self, task: Dict) -> bool:
        """Execute a PAI (Personal AI Infrastructure) skill task."""
        agent     = task.get('agent', 'pai')
        task_desc = task.get('task', '')
        pow_file  = task.get('pow_file')

        print("   → Routing to PAI agent...")
        _agent_log(agent, f"[PAI] Task: {task_desc[:80]}")

        try:
            from agents.pai_agent import PAIAgent

            pai = PAIAgent(project_root=self.project_root)
            success = pai.execute_task(task)

            if success:
                print(f"   ✅ PAI task completed")
                _agent_log(agent, f"[PAI DONE] {task.get('id', 'unknown')}")
            else:
                print(f"   ⚠️  PAI task failed — falling back to generic handler")
                _agent_log(agent, f"[PAI FAIL] {task.get('id', 'unknown')}")
                return self._execute_generic_task(task)
            return success

        except Exception as e:
            print(f"   PAI task error: {e}")
            _agent_log(agent, f"[PAI EXCEPTION] {e}")
            return self._execute_generic_task(task)

    # ── Periodic trading improvement loop ────────────────────────

    def _maybe_run_trading_loop(self):
        """
        Run trading_improvement_loop.py on schedule:
          - Full analysis every 4 hours
          - Agent health check (monitor) every 30 minutes
        Timestamps persisted in _TRADE_LAST_RUN_FILE so restarts don't reset the clock.
        """
        import time as _time

        now = _time.time()

        # Load last-run timestamps
        last_run = {"trade_loop": 0.0, "monitor": 0.0}
        if _TRADE_LAST_RUN_FILE.exists():
            try:
                last_run = json.loads(_TRADE_LAST_RUN_FILE.read_text())
            except Exception:
                pass

        changed = False

        # ── 30-minute agent health + monitor check ──────────────
        if now - last_run.get("monitor", 0) >= _MONITOR_INTERVAL:
            print("   🔍 [MONITOR] Agent health check...")
            _agent_log("automode", "[MONITOR] Running agent health check")
            self._run_agent_monitor()
            last_run["monitor"] = now
            changed = True

        # ── 4-hour full trading improvement analysis ─────────────
        if now - last_run.get("trade_loop", 0) >= _TRADE_LOOP_INTERVAL:
            print("   📈 [TRADE-LOOP] Running trading improvement analysis...")
            _agent_log("automode", "[TRADE-LOOP] Starting trading_improvement_loop.py")
            if _TRADE_LOOP_SCRIPT.exists():
                try:
                    result = subprocess.run(
                        [sys.executable, str(_TRADE_LOOP_SCRIPT)],
                        capture_output=True, text=True, timeout=120,
                        cwd=str(self.project_root)
                    )
                    if result.returncode == 0:
                        print(f"   ✅ [TRADE-LOOP] {result.stdout.strip()[:200]}")
                        _agent_log("automode", f"[TRADE-LOOP] OK: {result.stdout.strip()[:120]}")
                    else:
                        print(f"   ⚠️  [TRADE-LOOP] exit {result.returncode}: {result.stderr.strip()[:120]}")
                        _agent_log("automode", f"[TRADE-LOOP] FAIL: {result.stderr.strip()[:120]}")
                except subprocess.TimeoutExpired:
                    _agent_log("automode", "[TRADE-LOOP] Timeout after 120s")
                except Exception as e:
                    _agent_log("automode", f"[TRADE-LOOP] Exception: {e}")
            else:
                _agent_log("automode", f"[TRADE-LOOP] Script not found: {_TRADE_LOOP_SCRIPT}")
            last_run["trade_loop"] = now
            changed = True

        if changed:
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            _TRADE_LAST_RUN_FILE.write_text(json.dumps(last_run))

    def _run_agent_monitor(self):
        """Check that EA and Binance trading agents are running; restart if dead."""
        agents_to_monitor = [
            {
                "name": "EA",
                "match": "liveea.py",
                "script": "scripts/ea/liveea.py",
                "log": "data/logs/liveea.log",
            },
            {
                "name": "Binance",
                "match": "live_trading_binance.py",
                "script": "agents/trading-agent/live_trading_binance.py",
                "log": "data/logs/live_trading_binance.log",
            },
        ]

        health_lines = [
            f"\n## Agent Monitor {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        ]

        for agent_cfg in agents_to_monitor:
            name   = agent_cfg["name"]
            match  = agent_cfg["match"]
            script = self.project_root / agent_cfg["script"]
            log    = self.project_root / agent_cfg["log"]

            # Check if running
            try:
                out = subprocess.check_output(["pgrep", "-f", match], text=True)
                is_running = bool(out.strip())
            except subprocess.CalledProcessError:
                is_running = False

            status = "RUNNING" if is_running else "DOWN"
            print(f"      [{name}] {status}")
            _agent_log("automode", f"[MONITOR] {name}: {status}")
            health_lines.append(f"- {name}: **{status}**")

            if not is_running and script.exists():
                print(f"      [{name}] Restarting...")
                _agent_log("automode", f"[MONITOR] Restarting {name} agent")
                try:
                    log.parent.mkdir(parents=True, exist_ok=True)
                    log_fh = open(str(log), "a")
                    subprocess.Popen(
                        ["nohup", sys.executable, "-u", str(script)],
                        stdout=log_fh, stderr=subprocess.STDOUT,
                        cwd=str(self.project_root),
                        start_new_session=True,
                    )
                    health_lines.append(f"  - ACTION: Restarted {name} agent")
                    _agent_log("automode", f"[MONITOR] {name} restarted OK")
                except Exception as e:
                    health_lines.append(f"  - ERROR: Could not restart {name}: {e}")
                    _agent_log("automode", f"[MONITOR] Failed to restart {name}: {e}")

        health_lines.append("\n---\n")

        # Write to Obsidian System_State
        obs_health = self.project_root / "data" / "obsidian" / "System_State" / "agent_health.md"
        try:
            obs_health.parent.mkdir(parents=True, exist_ok=True)
            with open(obs_health, "a") as f:
                f.write("\n".join(health_lines))
        except Exception:
            pass

    # ── Trading improvement task dispatcher (from task bank) ─────

    def _execute_trading_improvement_task(self, task: Dict) -> bool:
        """
        Execute one of the three autonomous trading improvement tasks
        (HERMES-TRADE-REVIEW, OPENCODE-TRADE-IMPLEMENT, PIDEV-AGENT-MONITOR)
        by running the trading_improvement_loop.py script directly.
        """
        task_desc = task.get("task", "")
        pow_file  = task.get("pow_file")

        print("   → Routing to trading improvement loop...")
        _agent_log("automode", f"[TRADE-TASK] {task_desc[:80]}")

        if _TRADE_LOOP_SCRIPT.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(_TRADE_LOOP_SCRIPT)],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(self.project_root)
                )
                output = result.stdout.strip() or result.stderr.strip()
                _agent_log("automode", f"[TRADE-TASK] exit={result.returncode} out={output[:80]}")
                if pow_file:
                    self._create_pow_file(pow_file, task)
                return result.returncode == 0
            except Exception as e:
                _agent_log("automode", f"[TRADE-TASK] Exception: {e}")

        # Fallback: run the in-process monitor
        self._run_agent_monitor()
        if pow_file:
            self._create_pow_file(pow_file, task)
        return True

    def _execute_trading_task(self, task: Dict) -> bool:
        print("   → Routing to FreqTrade agent...")
        try:
            from core.orchestration.unified_improvement_workflow import UnifiedImprovementWorkflow
            result = UnifiedImprovementWorkflow().execute_freqtrade_improvement_cycle()
            return result['status'] == 'completed'
        except Exception as e:
            print(f"   Trading task error: {e}")
            return self._execute_generic_task(task)

    def _execute_ea_task(self, task: Dict) -> bool:
        print("   → Routing to EA agent...")
        try:
            from core.orchestration.unified_improvement_workflow import UnifiedImprovementWorkflow
            result = UnifiedImprovementWorkflow().execute_ea_improvement_cycle()
            return result['status'] == 'completed'
        except Exception as e:
            print(f"   EA task error: {e}")
            return self._execute_generic_task(task)

    def _execute_social_task(self, task: Dict) -> bool:
        task_desc = task.get('task', '')
        pow_file  = task.get('pow_file')

        # VIDEO-SYNC-GDRIVE: sync videos to GDrive
        if 'VIDEO-SYNC-GDRIVE' in task_desc or 'video_sync' in task_desc:
            print("   → Syncing videos to GDrive...")
            _agent_log('social', "[VIDEO-SYNC] Syncing to GDrive")
            sync_results = []
            for src, dst in [
                ('data/media_output/trading/all', 'gdrive:videos/trading'),
                ('data/media_output/christian', 'gdrive:videos/christian'),
            ]:
                r = subprocess.run(
                    ['rclone', 'sync', str(self.project_root / src), dst, '--no-traverse'],
                    capture_output=True, text=True, timeout=120
                )
                sync_results.append(f"{src} → {dst}: {'OK' if r.returncode == 0 else r.stderr[:80]}")
            output = '\n'.join(sync_results)
            print(f"   ✅ Video sync: {output}")
            _agent_log('social', f"[VIDEO-SYNC] {output}")
            if pow_file:
                self._create_pow_file_with_content(pow_file, task, output)
            return True

        # VIDEO-PRODUCE tasks: run produce_video.py directly
        if 'VIDEO-PRODUCE' in task_desc or 'produce_video' in task_desc:
            print("   → Running video producer script...")
            _agent_log('social', f"[VIDEO] Producing video: {task_desc[:80]}")
            # Extract --signal or --topic flags from the task description
            import re as _re
            signal_m = _re.search(r'--signal\s+(BUY|SELL|HOLD)', task_desc)
            topic_m  = _re.search(r"--topic\s+'([^']+)'", task_desc)
            platform_m = _re.search(r'--platform\s+(\S+)', task_desc)
            duration_m = _re.search(r'--duration\s+(\d+)', task_desc)

            cmd = [sys.executable, str(self.project_root / 'scripts' / 'produce_video.py')]
            if signal_m:
                cmd += ['--signal', signal_m.group(1)]
            elif topic_m:
                cmd += ['--topic', topic_m.group(1)]
            if platform_m:
                cmd += ['--platform', platform_m.group(1)]
            if duration_m:
                cmd += ['--duration', duration_m.group(1)]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=180,
                                        cwd=str(self.project_root))
                output = (result.stdout + result.stderr).strip()
                success = 'SUCCESS' in output
                print(f"   {'✅' if success else '❌'} Video produce: {output[-200:]}")
                _agent_log('social', f"[VIDEO] Result: {output[-200:]}")
                if pow_file:
                    self._create_pow_file_with_content(pow_file, task, output)
                return success
            except Exception as e:
                print(f"   Video produce error: {e}")
                _agent_log('social', f"[VIDEO] Error: {e}")
                return self._execute_generic_task(task)

        print("   → Routing to Social Media Agent...")
        try:
            from agents.social_media_agent import SocialMediaAgent
            return SocialMediaAgent().execute_task(task)
        except Exception as e:
            print(f"   Social task error: {e}")
            return self._execute_generic_task(task)

    def _execute_faithnexus_task(self, task: Dict) -> bool:
        """Execute a FaithNexus biblical scripture video production task."""
        pow_file = task.get('pow_file')
        task_desc = task.get('task', '')

        print("   → Running FaithNexus video producer...")
        _agent_log('social', f"[FAITHNEXUS] Task: {task_desc[:80]}")

        script = self.project_root / "scripts" / "produce_faithnexus_video.py"
        if not script.exists():
            print(f"   ❌ FaithNexus script not found: {script}")
            _agent_log('social', f"[FAITHNEXUS] Script not found: {script}")
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(script), "--auto"],
                capture_output=True, text=True, timeout=300,
                cwd=str(self.project_root),
            )
            output = (result.stdout + result.stderr).strip()
            success = result.returncode == 0 and 'SUCCESS' in output

            print(f"   {'✅' if success else '❌'} FaithNexus video: {output[-300:]}")
            _agent_log('social', f"[FAITHNEXUS] Result: exit={result.returncode} {output[-200:]}")

            if pow_file:
                self._create_pow_file_with_content(pow_file, task, output)

            if not success:
                print(f"   ❌ FaithNexus video failed: {result.stderr[-300:]}")

            return success

        except subprocess.TimeoutExpired:
            print("   ❌ FaithNexus video timed out after 300s")
            _agent_log('social', "[FAITHNEXUS] Timeout after 300s")
            return False
        except Exception as e:
            print(f"   FaithNexus video error: {e}")
            _agent_log('social', f"[FAITHNEXUS] Exception: {e}")
            return self._execute_generic_task(task)

    def _create_pow_file_with_content(self, pow_file_path: str, task: Dict, content: str):
        """Create a POW file with custom content."""
        full_path = self.project_root / pow_file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(
            f"# Proof of Work — {task.get('id')}\n\n"
            f"**Agent:** {task.get('agent')}\n"
            f"**Date:** {datetime.now().isoformat()}\n"
            f"**Task:** {task.get('task', '')[:200]}\n\n"
            f"## Output\n\n```\n{content}\n```\n"
        )
        print(f"   ✅ POW file created: {pow_file_path}")

    def _execute_generic_task(self, task: Dict) -> bool:
        print("   → Generic task execution...")
        pow_file = task.get('pow_file')
        if pow_file:
            self._create_pow_file(pow_file, task)
            return True
        print("   ✅ Task acknowledged (no POW file required)")
        return True

    # ── POW file ───────────────────────────────────────────────

    def _create_pow_file(self, pow_file_path: str, task: Dict):
        full_path = self.project_root / pow_file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        pow_content = {
            'task_id':          task.get('id'),
            'task_description': task.get('task'),
            'agent':            task.get('agent'),
            'executed_by':      'AutoModeController v6',
            'timestamp':        datetime.now().isoformat(),
            'status':           'completed',
            'auto_mode':        True,
        }
        with open(full_path, 'w') as f:
            if pow_file_path.endswith('.json'):
                json.dump(pow_content, f, indent=2)
            else:
                f.write(f"# Proof of Work — {task.get('id')}\n\n")
                f.write(json.dumps(pow_content, indent=2))
        print(f"   ✅ POW file created: {pow_file_path}")

    # ── Self-tasking (loop-safe) ───────────────────────────────

    def _create_followup_task(self, completed_task: Dict):
        task_id   = completed_task.get('id', 'unknown')
        if _id_depth(task_id) >= _MAX_ID_DEPTH:
            return
        agent     = completed_task.get('agent', self.agent_name or 'opencode')
        task_text = completed_task.get('task', '')
        pow_file  = completed_task.get('pow_file', '')
        new_id    = f"FOLLOWUP-{task_id[:40]}-{uuid.uuid4().hex[:6].upper()}"

        # Generate a context-aware follow-up rather than the generic template
        if pow_file and 'trade' in pow_file:
            followup_text = (f"Read {pow_file} and check if any findings require "
                             f"immediate changes to trading agent parameters. "
                             f"If yes, implement the highest-priority change.")
        elif pow_file and 'security' in pow_file:
            followup_text = (f"Read {pow_file}. If any HIGH severity findings exist, "
                             f"implement the fix immediately. Write remediation to "
                             f"docs/pow/security_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md.")
        elif pow_file and 'code_review' in pow_file:
            followup_text = (f"Read {pow_file}. Apply the top-priority code fix identified. "
                             f"Verify no imports break after the change.")
        else:
            followup_text = (f"Read {pow_file} and extract one concrete actionable improvement "
                             f"for the swarm. Write the improvement plan to "
                             f"docs/pow/action_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md.")

        followup = {
            "id": new_id, "task": followup_text, "agent": agent,
            "priority": 5, "status": "pending",
            "created_by": "self_tasking", "parent_task": task_id,
            "created_at": datetime.now().isoformat(),
        }
        self._append_pending_task(followup)
        print(f"   🔁 Follow-up created: {new_id[:60]}… → {agent}")

    def _create_review_task(self, completed_task: Dict):
        task_id  = completed_task.get('id', 'unknown')
        if _id_depth(task_id) >= _MAX_ID_DEPTH:
            return
        agent    = completed_task.get('agent', self.agent_name or 'opencode').lower()
        reviewer = self._reviewer_map.get(agent, 'hermes')
        new_id   = f"REVIEW-{task_id[:40]}-{uuid.uuid4().hex[:6].upper()}"
        review = {
            "id": new_id,
            "task": (f"Peer review of {task_id[:40]} by {agent}: check correctness, "
                     f"security, consistency. Read logs/automode.log for context."),
            "agent": reviewer, "priority": 4, "status": "pending",
            "created_by": "peer_review", "reviewed_task": task_id,
            "reviewed_agent": agent, "created_at": datetime.now().isoformat(),
        }
        self._append_pending_task(review)
        print(f"   🔍 Review created: {new_id[:60]}… → {reviewer}")

    def _append_pending_task(self, task: Dict):
        if not self.tasks_file.exists():
            return
        try:
            with open(self.tasks_file) as f:
                tasks = json.load(f)
            tasks.setdefault('task_queue', {}).setdefault('pending', []).append(task)
            with open(self.tasks_file, 'w') as fw:
                json.dump(tasks, fw, indent=2)
        except Exception as e:
            print(f"   ⚠️  Could not append task: {e}")

    def _update_task_status(self, task_id: str, new_status: str):
        if not self.tasks_file.exists():
            return
        with open(self.tasks_file) as f:
            tasks = json.load(f)
        tq = tasks.setdefault('task_queue', {})
        for queue_type in ['pending', 'in_progress', 'completed', 'failed']:
            queue = tq.get(queue_type, [])
            for task in queue:
                if task.get('id') == task_id:
                    queue.remove(task)
                    tq[queue_type] = queue
                    target = tq.setdefault(new_status, [])
                    task['status']       = new_status
                    task['last_updated'] = datetime.now().isoformat()
                    if new_status == 'failed':
                        task['failure_count'] = self._task_failure_counts.get(task_id, _MAX_TASK_FAILURES)
                    target.append(task)
                    with open(self.tasks_file, 'w') as fw:
                        json.dump(tasks, fw, indent=2)
                    return

    def _signal_handler(self, signum, frame):
        print(f"\n⚠️  Received signal {signum}, shutting down...")
        self.running = False

    def _auto_cleanup_tasks(self):
        """v7: Auto-cleanup unified_tasks.json — archive failed, cap completed."""
        if not self.tasks_file.exists():
            return
        try:
            with open(self.tasks_file) as f:
                tasks = json.load(f)
            tq = tasks.setdefault('task_queue', {})
            failed = tq.get('failed', [])
            completed = tq.get('completed', [])
            # Archive old failed tasks (keep last 20)
            if len(failed) > 20:
                tq['failed_archive'] = failed[:-20]
                tq['failed'] = failed[-20:]
                _agent_log('automode', f"[CLEANUP] Archived {len(failed)-20} failed tasks")
            # Cap completed list at _MAX_COMPLETED
            if len(completed) > _MAX_COMPLETED:
                tq['completed'] = completed[-_MAX_COMPLETED:]
                _agent_log('automode', f"[CLEANUP] Trimmed completed to {_MAX_COMPLETED}")
            tasks['last_updated'] = datetime.now().isoformat()
            with open(self.tasks_file, 'w') as fw:
                json.dump(tasks, fw, indent=2)
        except Exception as e:
            _agent_log('automode', f"[CLEANUP] Error: {e}")

    def _shutdown(self):
        print(f"\n{'='*70}")
        print("🛑 Auto Mode v7 Shutdown")
        print(f"{'='*70}")
        self._auto_cleanup_tasks()  # v7: cleanup on shutdown
        print(f"   Completed: {len(self.completed_tasks)}")
        print(f"   Failed:    {len(self.failed_tasks)}")
        print(f"\n✅ Shutdown complete\n")
        _agent_log('automode', f"Shutdown — completed={len(self.completed_tasks)} failed={len(self.failed_tasks)}")
        try:
            # v7: use vault_logger for structured session logging
            from core.integrations.vault_logger import vault_log
            vault_log('automode', 'SESSION_END', f"Automode v7 session ended",
                      data={"agent": self.agent_name or "multi",
                            "completed": len(self.completed_tasks),
                            "failed": len(self.failed_tasks),
                            "tasks": self.completed_tasks[:10]})
        except Exception:
            pass
        try:
            # Also write to legacy obsidian sessions path for backward compat
            obs = _project_root / "data" / "obsidian" / "system" / "sessions"
            obs.mkdir(parents=True, exist_ok=True)
            note = obs / f"{datetime.now().strftime('%Y-%m-%d')}-automode.md"
            with open(note, 'a') as f:
                f.write(f"\n## Session {datetime.now().strftime('%H:%M:%S')}\n")
                f.write(f"- Agent: {self.agent_name or 'multi'}\n")
                f.write(f"- Completed: {len(self.completed_tasks)}\n")
                f.write(f"- Failed: {len(self.failed_tasks)}\n")
                if self.completed_tasks:
                    f.write(f"- Tasks: {', '.join(self.completed_tasks[:10])}\n")
        except Exception:
            pass


# ── CLI entry point ───────────────────────────────────────────

def main():
    if '--diagnose' in sys.argv:
        tasks_file = _project_root / "unified_tasks.json"
        print("\n=== Queue Diagnostic ===")
        report = diagnose_queue(tasks_file)
        for k, v in report.items():
            if isinstance(v, list):
                print(f"  {k}: {len(v)}")
                for item in v[:5]:
                    print(f"    - {str(item)[:80]}")
            else:
                print(f"  {k}: {v}")
        print()
        print("=== Log Health ===")
        print(AgentLogReader.summarise_all())
        return

    if '--cleanup' in sys.argv:
        tasks_file = _project_root / "unified_tasks.json"
        removed = cleanup_queue(tasks_file)
        print(f"Cleanup done. Removed {removed} runaway tasks.")
        return

    if '--logs' in sys.argv:
        idx = sys.argv.index('--logs')
        agent = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else 'automode'
        print(AgentLogReader.agent_log(agent, lines=80))
        return

    if '--deepseek' in sys.argv:
        # Quick DeepSeek query: python3 automode.py --deepseek "your question"
        idx = sys.argv.index('--deepseek')
        question = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "What trading improvements can I make?"
        print(f"Querying DeepSeek: {question}")
        response = query_deepseek(question)
        print(response)
        return

    agent_name = None
    for arg in sys.argv[1:]:
        if not arg.startswith('--'):
            agent_name = arg
            break

    controller = AutoModeController(agent_name=agent_name)
    controller.start()


if __name__ == "__main__":
    main()
