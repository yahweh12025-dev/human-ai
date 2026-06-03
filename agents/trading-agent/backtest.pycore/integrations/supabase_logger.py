#!/usr/bin/env python3
"""
Supabase Integration Logger
Sends agent events, trade data, and system metrics to Supabase for persistence.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / '.env')


class SupabaseLogger:
    """
    Centralized Supabase logging for the Human-AI swarm.
    Handles agent events, trade logs, task completions, and system health.
    """

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.enabled = bool(self.url and self.key)

        if not self.enabled:
            logger.warning("Supabase credentials not configured - logging disabled")
            return

        try:
            from supabase import create_client
            self.client = create_client(self.url, self.key)
            logger.info(f"Supabase connected: {self.url}")
        except ImportError:
            logger.warning("supabase-py not installed. Using HTTP fallback.")
            self.client = None
        except Exception as e:
            logger.error(f"Supabase init failed: {e}")
            self.client = None
            self.enabled = False

    def log_agent_event(self, agent: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Log an agent event to Supabase"""
        record = {
            "agent": agent,
            "event_type": event_type,
            "data": json.dumps(data),
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self._insert("agent_events", record)

    def log_trade(self, agent: str, trade_data: Dict[str, Any]) -> bool:
        """Log a trade execution"""
        record = {
            "agent": agent,
            "symbol": trade_data.get("symbol", ""),
            "side": trade_data.get("side", ""),
            "amount": trade_data.get("amount", 0),
            "price": trade_data.get("price", 0),
            "pnl": trade_data.get("pnl", 0),
            "data": json.dumps(trade_data),
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self._insert("trades", record)

    def log_task_completion(self, task_id: str, agent: str, result: Dict[str, Any]) -> bool:
        """Log a task completion"""
        record = {
            "task_id": task_id,
            "agent": agent,
            "status": result.get("status", "completed"),
            "data": json.dumps(result),
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self._insert("task_completions", record)

    def log_system_health(self, metrics: Dict[str, Any]) -> bool:
        """Log system health metrics"""
        record = {
            "metrics": json.dumps(metrics),
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self._insert("system_health", record)

    def log_social_post(self, platform: str, content_id: str, data: Dict[str, Any]) -> bool:
        """Log a social media post"""
        record = {
            "platform": platform,
            "content_id": content_id,
            "data": json.dumps(data),
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self._insert("social_posts", record)

    def _insert(self, table: str, record: Dict) -> bool:
        """Insert a record into a Supabase table"""
        if not self.enabled:
            return False

        try:
            if self.client:
                self.client.table(table).insert(record).execute()
                return True
            else:
                return self._http_insert(table, record)
        except Exception as e:
            logger.error(f"Supabase insert to {table} failed: {e}")
            self._fallback_log(table, record)
            return False

    def _http_insert(self, table: str, record: Dict) -> bool:
        """HTTP fallback for Supabase inserts"""
        import requests
        url = f"{self.url}/rest/v1/{table}"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        response = requests.post(url, headers=headers, json=record, timeout=10)
        return response.status_code in (200, 201)

    def _fallback_log(self, table: str, record: Dict):
        """Fallback: write to local JSONL if Supabase is unavailable"""
        fallback_dir = Path.home() / "human-ai" / "data" / "data" / "logs" / "supabase_fallback"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_file = fallback_dir / f"{table}_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(fallback_file, 'a') as f:
            f.write(json.dumps(record) + '\n')


# Singleton instance
_instance = None

def get_supabase_logger() -> SupabaseLogger:
    """Get or create the Supabase logger singleton"""
    global _instance
    if _instance is None:
        _instance = SupabaseLogger()
    return _instance
