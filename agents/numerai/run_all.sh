#!/usr/bin/env bash
set -euo pipefail

echo "=== Numerai Compute: Starting all pipelines ==="
date -u

cd "$(dirname "$0")"

# Human-AI Alpha (main tournament)
echo "--- Running numerai_pipeline.py (human_ai_alpha) ---"
python3 numerai_pipeline.py --use-cached 2>&1 || echo "WARNING: main pipeline failed (continuing)"

# Crypto tournament
echo "--- Running crypto_pipeline.py (crypto_model_alpha) ---"
python3 crypto_pipeline.py --use-cached 2>&1 || echo "WARNING: crypto pipeline failed (continuing)"

# Signals tournament (if model_id is configured)
MODEL_ID=$(python3 -c "
import json
with open('models_config.json') as f:
    c = json.load(f)
print(c.get('signal_model_alpha', {}).get('model_id', ''))
" 2>/dev/null || echo "")
if [ -n "$MODEL_ID" ]; then
    echo "--- Running signal_pipeline.py (signal_model_alpha) ---"
    python3 signal_pipeline.py --use-cached 2>&1 || echo "WARNING: signals pipeline failed (continuing)"
else
    echo "--- Skipping signal_pipeline.py (no model_id configured) ---"
fi

echo "=== Numerai Compute: All pipelines complete ==="
date -u
