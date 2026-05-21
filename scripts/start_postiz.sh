#!/usr/bin/env bash
# start_postiz.sh — Start Postiz self-hosted social media scheduler
# Usage:  bash scripts/start_postiz.sh
#         bash scripts/start_postiz.sh stop

set -euo pipefail
COMPOSE_FILE="$(cd "$(dirname "$0")/.." && pwd)/infrastructure/docker/postiz/docker-compose.yml"

case "${1:-start}" in
  start)
    echo "[POSTIZ] Starting containers..."
    docker compose -f "$COMPOSE_FILE" up -d
    echo ""
    echo "[POSTIZ] Waiting for service to be ready..."
    for i in $(seq 1 30); do
      if curl -sf http://localhost:5000/api/health &>/dev/null; then
        echo "[POSTIZ] ✅ Online at http://localhost:5000"
        echo ""
        echo "  Next steps:"
        echo "  1. Visit http://localhost:5000 → create admin account"
        echo "  2. Settings → Social Channels → Connect YouTube / TikTok"
        echo "  3. Settings → API Keys → copy key"
        echo "  4. Add to .env:  POSTIZ_API_KEY=<key>"
        echo "  5. Test:  python3 agents/social/postiz_connector.py"
        exit 0
      fi
      sleep 2
    done
    echo "[POSTIZ] ⚠️  Service didn't respond after 60s — check: docker compose -f $COMPOSE_FILE logs postiz"
    ;;
  stop)
    echo "[POSTIZ] Stopping containers..."
    docker compose -f "$COMPOSE_FILE" down
    ;;
  status)
    docker compose -f "$COMPOSE_FILE" ps
    ;;
  logs)
    docker compose -f "$COMPOSE_FILE" logs --tail=50 -f postiz
    ;;
  *)
    echo "Usage: $0 [start|stop|status|logs]"
    exit 1
    ;;
esac
