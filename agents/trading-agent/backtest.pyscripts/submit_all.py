#!/usr/bin/env python3
"""
Daily submission script for all Numerai tournaments.
Runs pipelines with --use-cached and submits via API.
Designed for systemd timer execution.
"""
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIPELINES = [
    {
        "name": "Main",
        "script": str(PROJECT_ROOT / "core/agents/numerai/numerai_pipeline.py"),
        "model_config_key": "human_ai_alpha",
        "tournament": "main",
    },
    {
        "name": "Crypto",
        "script": str(PROJECT_ROOT / "core/agents/numerai/crypto_pipeline.py"),
        "model_config_key": "crypto_model_alpha",
        "tournament": "crypto",
    },
    {
        "name": "Signals",
        "script": str(PROJECT_ROOT / "core/agents/numerai/signal_pipeline.py"),
        "model_config_key": "signal_model_alpha",
        "tournament": "signals",
    },
]

LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "daily_submit.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("daily_submit")


def get_model_id(config_key: str) -> str:
    config_path = PROJECT_ROOT / "agents/numerai" / "models_config.json"
    try:
        with open(config_path) as f:
            config = json.load(f)
        return config.get(config_key, {}).get("model_id", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


def run_pipeline(name: str, script: str, model_id: str) -> bool:
    if not model_id:
        log.warning("%s: no model_id configured - skipping", name)
        return False

    log.info("=" * 50)
    log.info("%s: starting", name)

    venv_python = str(PROJECT_ROOT / ".venv" / "bin" / "python3")
    cmd = [venv_python, script, "--use-cached", "--model-id", model_id]
    log.info("Running: %s", " ".join(cmd[-6:]))

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, cwd=str(PROJECT_ROOT)
        )
        if result.returncode == 0:
            log.info("%s: SUCCESS", name)
            return True
        else:
            log.error("%s: FAILED (code=%d)", name, result.returncode)
            log.error("STDERR: %s", result.stderr[-500:] if result.stderr else "none")
            return False
    except subprocess.TimeoutExpired:
        log.error("%s: TIMEOUT (10 min)", name)
        return False
    except Exception as e:
        log.error("%s: ERROR: %s", name, e)
        return False


def main():
    log.info("=" * 60)
    log.info("Daily Numerai Submission Run")
    log.info("Time: %s", time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))

    results = []
    for pipeline in PIPELINES:
        model_id = get_model_id(pipeline["model_config_key"])
        success = run_pipeline(
            pipeline["name"], pipeline["script"], model_id
        )
        results.append((pipeline["name"], success))
        time.sleep(5)

    log.info("=" * 60)
    log.info("RESULTS:")
    all_ok = True
    for name, ok in results:
        status = "OK" if ok else "FAILED"
        log.info("  %s: %s", name, status)
        if not ok:
            all_ok = False

    log.info("=" * 60)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
