#!/usr/bin/env python3
"""
OpenClaw <-> FreqTrade Bridge
Enables OpenClaw gateway to trigger and monitor FreqTrade operations
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import signal
import psutil


class OpenClawFreqTradeBridge:
    """
    Bridge between OpenClaw gateway and FreqTrade trading agent.
    Handles command routing, process management, and status reporting.
    """

    def __init__(self):
        self.project_root = Path.home() / "human-ai"
        self.freqtrade_config = self.project_root / "projects/freqtrade/freqtrade/user_data/config_testnet.json"
        self.strategy_path = self.project_root / "agents/trading-agent/freqtrade_strategy_testnet.py"
        self.log_dir = self.project_root / "data" / "data" / "logs" / "trading"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.process: Optional[subprocess.Popen] = None
        self.process_pid: Optional[int] = None

    def start_trading_bot(self, dry_run: bool = True) -> Dict:
        """
        Start FreqTrade trading bot

        Args:
            dry_run: If True, runs in paper trading mode
        """
        try:
            # Build command
            cmd = [
                "freqtrade", "trade",
                "--config", str(self.freqtrade_config),
                "--strategy", "SwarmIntelligenceStrategy",
                "--strategy-path", str(self.strategy_path.parent)
            ]

            if dry_run:
                cmd.append("--dry-run")

            # Start process
            log_file = self.log_dir / f"freqtrade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

            with open(log_file, 'w') as f:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.project_root)
                )

            self.process_pid = self.process.pid

            return {
                'status': 'started',
                'pid': self.process_pid,
                'log_file': str(log_file),
                'dry_run': dry_run,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def stop_trading_bot(self) -> Dict:
        """Stop running FreqTrade bot gracefully"""
        try:
            if self.process and self.process.poll() is None:
                # Graceful shutdown
                self.process.send_signal(signal.SIGTERM)
                self.process.wait(timeout=30)

                return {
                    'status': 'stopped',
                    'pid': self.process_pid,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'not_running',
                    'message': 'No active FreqTrade process found'
                }

        except subprocess.TimeoutExpired:
            # Force kill if graceful fails
            self.process.kill()
            return {
                'status': 'force_killed',
                'pid': self.process_pid,
                'message': 'Graceful shutdown failed, force killed'
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def get_bot_status(self) -> Dict:
        """Check if FreqTrade bot is running"""
        try:
            if self.process_pid:
                # Check if process exists
                if psutil.pid_exists(self.process_pid):
                    proc = psutil.Process(self.process_pid)
                    return {
                        'status': 'running',
                        'pid': self.process_pid,
                        'cpu_percent': proc.cpu_percent(),
                        'memory_mb': proc.memory_info().rss / 1024 / 1024,
                        'uptime_seconds': (datetime.now() - datetime.fromtimestamp(proc.create_time())).seconds
                    }

            return {
                'status': 'stopped',
                'message': 'Bot is not running'
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def run_backtest(self, strategy: str = "SwarmIntelligenceStrategy",
                    timerange: str = "20260401-20260510") -> Dict:
        """
        Run FreqTrade backtest

        Args:
            strategy: Strategy class name
            timerange: Date range in format YYYYMMDD-YYYYMMDD
        """
        try:
            cmd = [
                "freqtrade", "backtesting",
                "--config", str(self.freqtrade_config),
                "--strategy", strategy,
                "--strategy-path", str(self.strategy_path.parent),
                "--timerange", timerange,
                "--export", "trades"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=300  # 5 minute timeout
            )

            # Save backtest output
            output_file = self.log_dir / f"backtest_{strategy}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            with open(output_file, 'w') as f:
                f.write(result.stdout)
                f.write(result.stderr)

            return {
                'status': 'completed' if result.returncode == 0 else 'failed',
                'return_code': result.returncode,
                'output_file': str(output_file),
                'stdout': result.stdout[-1000:],  # Last 1000 chars
                'timestamp': datetime.now().isoformat()
            }

        except subprocess.TimeoutExpired:
            return {
                'status': 'timeout',
                'message': 'Backtest exceeded 5 minute timeout'
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def download_market_data(self, pairs: List[str] = None,
                            timerange: str = "20260401-20260510") -> Dict:
        """
        Download historical market data for backtesting

        Args:
            pairs: List of trading pairs (default: ['BTC/USDT'])
            timerange: Date range
        """
        pairs = pairs or ['BTC/USDT']

        try:
            cmd = [
                "freqtrade", "download-data",
                "--config", str(self.freqtrade_config),
                "--pairs", *pairs,
                "--timerange", timerange,
                "--timeframes", "5m", "15m", "1h"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=600  # 10 minute timeout
            )

            return {
                'status': 'completed' if result.returncode == 0 else 'failed',
                'pairs': pairs,
                'timerange': timerange,
                'return_code': result.returncode,
                'output': result.stdout[-500:],
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Retrieve recent trade history"""
        try:
            # Read from trade log
            trade_logs = sorted(self.log_dir.glob("freqtrade_testnet_*.jsonl"))
            if not trade_logs:
                return []

            trades = []
            with open(trade_logs[-1], 'r') as f:
                for line in f:
                    trades.append(json.loads(line))

            return trades[-limit:]

        except Exception as e:
            return [{'error': str(e)}]

    def openclaw_command_handler(self, command: str, params: Dict = None) -> Dict:
        """
        Handle commands from OpenClaw gateway

        Commands:
            - start_bot: Start trading bot
            - stop_bot: Stop trading bot
            - status: Get bot status
            - backtest: Run backtest
            - download_data: Download market data
            - trade_history: Get recent trades
        """
        params = params or {}

        handlers = {
            'start_bot': lambda: self.start_trading_bot(params.get('dry_run', True)),
            'stop_bot': lambda: self.stop_trading_bot(),
            'status': lambda: self.get_bot_status(),
            'backtest': lambda: self.run_backtest(
                params.get('strategy', 'SwarmIntelligenceStrategy'),
                params.get('timerange', '20260401-20260510')
            ),
            'download_data': lambda: self.download_market_data(
                params.get('pairs', ['BTC/USDT']),
                params.get('timerange', '20260401-20260510')
            ),
            'trade_history': lambda: {'trades': self.get_trade_history(params.get('limit', 50))}
        }

        if command not in handlers:
            return {
                'status': 'error',
                'error': f'Unknown command: {command}',
                'available_commands': list(handlers.keys())
            }

        return handlers[command]()

    def log_to_swarm(self, event_type: str, data: Dict):
        """Log events to swarm queue for other agents"""
        event = {
            'source': 'OpenClawFreqTradeBridge',
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }

        queue_file = self.project_root / "swarm" / "trading_events.jsonl"
        queue_file.parent.mkdir(parents=True, exist_ok=True)

        with open(queue_file, 'a') as f:
            f.write(json.dumps(event) + '\n')


def main():
    """CLI interface for manual testing"""
    bridge = OpenClawFreqTradeBridge()

    if len(sys.argv) < 2:
        print("Usage: python openclaw_freqtrade_bridge.py <command> [params]")
        print("\nCommands:")
        print("  start_bot      - Start FreqTrade bot")
        print("  stop_bot       - Stop FreqTrade bot")
        print("  status         - Get bot status")
        print("  backtest       - Run backtest")
        print("  download_data  - Download market data")
        print("  trade_history  - Get recent trades")
        return

    command = sys.argv[1]
    result = bridge.openclaw_command_handler(command)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
