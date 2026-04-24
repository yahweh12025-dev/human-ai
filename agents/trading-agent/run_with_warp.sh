#!/bin/bash
# Wrapper script to run trading agent with WARP proxy

# Set proxy environment variables for SOCKS5 proxy
export HTTP_PROXY="socks5://127.0.0.1:40000"
export HTTPS_PROXY="socks5://127.0.0.1:40000"
export http_proxy="socks5://127.0.0.1:40000"
export https_proxy="socks5://127.0.0.1:40000"
export ALL_PROXY="socks5://127.0.0.1:40000"

# Ensure WARP is connected
warp-cli --accept-tos connect 2>/dev/null || true
warp-cli --accept-tos mode proxy 2>/dev/null || true

# Run the trading agent
cd "$(dirname "$0")"
.venv/bin/python trading_agent.py "$@"
