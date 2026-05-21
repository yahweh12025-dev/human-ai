#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

NUMERAI_DIR="$PROJECT_DIR/agents/numerai"
usage() {
    echo "Usage: $0 <pipeline> [options]"
    echo ""
    echo "Pipelines:"
    echo "  all        Run all 3 pipelines (main + crypto + signals) sequentially"
    echo "  main       Run human_ai_alpha (main tournament)"
    echo "  crypto     Run crypto_model_alpha (crypto tournament)"
    echo "  signals    Run signal_model_alpha (Signals tournament)"
    echo "  manage     List saved models and backed-up pickles"
    echo ""
    echo "Options (passed to pipeline):"
    echo "  --dry-run          Run without submitting predictions"
    echo "  --use-cached       Load existing pickle instead of retraining"
    echo "  --save-only        Train/save model without submitting"
    echo "  --help             Show this message"
    echo ""
    echo "Examples:"
    echo "  $0 crypto --use-cached --dry-run"
    echo "  $0 main --save-only"
    echo "  $0 all --use-cached"
    exit 1
}

if [ $# -lt 1 ]; then
    usage
fi

PIPELINE="$1"
shift 2>/dev/null || true

run_pipeline() {
    local script="$1"
    shift
    echo "=== Running: $script $* ==="
    source .venv/bin/activate
    python3 "$script" "$@"
    local rc=$?
    if [ $rc -ne 0 ]; then
        echo "WARNING: $script exited with code $rc"
    fi
    return $rc
}

case "$PIPELINE" in
    all)
        run_pipeline "$NUMERAI_DIR/numerai_pipeline.py" "$@"
        run_pipeline "$NUMERAI_DIR/crypto_pipeline.py" "$@"
        run_pipeline "$NUMERAI_DIR/signal_pipeline.py" "$@"
        echo "=== All pipelines complete ==="
        ;;
    main)
        run_pipeline "$NUMERAI_DIR/numerai_pipeline.py" "$@"
        ;;
    crypto)
        run_pipeline "$NUMERAI_DIR/crypto_pipeline.py" "$@"
        ;;
    signals)
        run_pipeline "$NUMERAI_DIR/signal_pipeline.py" "$@"
        ;;
    manage)
        source .venv/bin/activate
        python3 "$NUMERAI_DIR/utils.py"
        ;;
    *)
        usage
        ;;
esac
