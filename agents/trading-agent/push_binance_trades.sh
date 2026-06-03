#!/usr/bin/env bash
set -euo pipefail
cd /home/yahweh1_2025/human-ai/agents/trading-agent
exec python3 push_binance_trades.py --lookback-days 7