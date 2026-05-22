#!/usr/bin/env python3
"""
Numerai Shared Utilities — pickle persistence, model management, GDrive upload
"""

import hashlib
import io
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "data" / "numerai" / "models"
LOG_FILE = PROJECT_ROOT / "data" / "logs" / "numerai_utils.log"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("numerai_utils")


def _setup_logging():
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(ch)


_setup_logging()


def _load_env():
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return {}
    loaded = {}
    with env_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
            loaded[key] = value
    return loaded


def pickle_path(model_name: str) -> Path:
    return MODELS_DIR / f"{model_name}.pkl"


def metadata_path(model_name: str) -> Path:
    return MODELS_DIR / f"{model_name}_metadata.json"


def hash_features(feature_cols: list[str]) -> str:
    return hashlib.sha256("|".join(sorted(feature_cols)).encode()).hexdigest()[:12]


def save_model(model, model_name: str, feature_cols: list[str], metrics: Optional[dict] = None, extra: Optional[dict] = None):
    import joblib
    path = pickle_path(model_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, path)
    meta = {
        "model_name": model_name,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "feature_hash": hash_features(feature_cols),
        "n_features": len(feature_cols),
        "metrics": metrics or {},
        "size_bytes": path.stat().st_size,
    }
    if extra:
        meta.update(extra)
    metadata_path(model_name).write_text(json.dumps(meta, indent=2))
    log.info("Model '%s' saved (%d features, %d bytes)", model_name, len(feature_cols), meta["size_bytes"])
    return path


def load_model(model_name: str):
    import joblib
    path = pickle_path(model_name)
    if not path.exists():
        log.warning("Model '%s' not found at %s", model_name, path)
        return None, {}
    meta_path = metadata_path(model_name)
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    model = joblib.load(path)
    log.info("Model '%s' loaded (saved: %s, features: %d)", model_name, meta.get("saved_at", "?"), meta.get("n_features", 0))
    return model, meta


def get_existing_model_ids() -> dict[str, str]:
    """
    Fetch all models for the Numerai account.
    Returns {model_name: model_id} for the main tournament.
    """
    pub_key = os.environ.get("NUMERAI_PUBLIC_ID", "")
    sec_key = os.environ.get("NUMERAI_SECRET_KEY", "")
    if not pub_key or not sec_key:
        log.warning("NUMERAI API keys not set — cannot fetch model IDs")
        return {}

    try:
        import numerapi
        napi = numerapi.NumerAPI(public_id=pub_key, secret_key=sec_key)
        models = napi.get_models()
        log.info("Found %d models on Numerai: %s", len(models), models)
        return models
    except Exception as exc:
        log.error("Failed to fetch model IDs: %s", exc)
        return {}


def get_crypto_model_ids() -> dict[str, str]:
    """Fetch models for the Numerai Crypto tournament."""
    pub_key = os.environ.get("NUMERAI_PUBLIC_ID", "")
    sec_key = os.environ.get("NUMERAI_SECRET_KEY", "")
    if not pub_key or not sec_key:
        return {}

    try:
        import numerapi
        capi = numerapi.CryptoAPI(public_id=pub_key, secret_key=sec_key)
        models = capi.get_models()
        log.info("Found %d crypto models: %s", len(models), models)
        return models
    except Exception as exc:
        log.error("Failed to fetch crypto model IDs: %s", exc)
        return {}


def upload_to_gdrive(local_path: Path, gdrive_dest: str) -> bool:
    """Upload a file to Google Drive via rclone. Returns True on success."""
    if not local_path.exists():
        log.warning("Cannot upload — %s not found", local_path)
        return False

    try:
        subprocess.run(
            ["rclone", "copy", str(local_path), gdrive_dest],
            capture_output=True, text=True, timeout=120,
        )
        log.info("Uploaded %s → %s", local_path, gdrive_dest)
        return True
    except FileNotFoundError:
        log.warning("rclone not found — skipping GDrive upload")
        return False
    except Exception as exc:
        log.error("GDrive upload failed: %s", exc)
        return False


def backup_model_pickle(model_name: str):
    """Upload model pickle + metadata to GDrive."""
    pkl = pickle_path(model_name)
    meta = metadata_path(model_name)
    ok = True
    if pkl.exists():
        ok &= upload_to_gdrive(pkl, f"gdrive:backups/numerai/models/{pkl.name}")
    if meta.exists():
        ok &= upload_to_gdrive(meta, f"gdrive:backups/numerai/models/{meta.name}")
    return ok


def _format_submission(df: pd.DataFrame, tournament: str) -> pd.DataFrame:
    fmt = df.copy()
    if tournament == "crypto":
        if "ucid" in fmt.columns:
            fmt = fmt.rename(columns={"ucid": "symbol"})
        elif fmt.index.name == "ucid" or (fmt.index.name is None and not isinstance(fmt.index, pd.RangeIndex)):
            fmt = fmt.reset_index()
            if "ucid" in fmt.columns:
                fmt = fmt.rename(columns={"ucid": "symbol"})
        elif "symbol" not in fmt.columns:
            fmt = fmt.reset_index()
        if "prediction" not in fmt.columns and "signal" in fmt.columns:
            fmt = fmt.rename(columns={"signal": "prediction"})
        cols = [c for c in fmt.columns if c in ("symbol", "prediction")]
        return fmt[cols]
    elif tournament == "signals":
        if "numerai_ticker" in fmt.columns:
            fmt = fmt[["numerai_ticker", "signal"]]
        else:
            keep = [c for c in ("bloomberg_ticker", "symbol", "friday_date", "signal", "prediction") if c in fmt.columns]
            fmt = fmt[keep]
            if "prediction" in fmt.columns and "signal" not in fmt.columns:
                fmt = fmt.rename(columns={"prediction": "signal"})
            keep2 = [c for c in ("bloomberg_ticker", "symbol", "friday_date", "signal") if c in fmt.columns]
            fmt = fmt[keep2]
    else:  # main tournament
        if "id" not in fmt.columns and fmt.index.name == "id":
            fmt = fmt.reset_index()
        keep = [c for c in ("id", "prediction", "probability") if c in fmt.columns]
        if keep:
            fmt = fmt[keep]
        if "prediction" in fmt.columns:
            fmt["prediction"] = fmt["prediction"].clip(1e-9, 1 - 1e-9)
        elif "probability" in fmt.columns:
            fmt = fmt.rename(columns={"probability": "prediction"})
            fmt["prediction"] = fmt["prediction"].clip(1e-9, 1 - 1e-9)
    return fmt


def submit_predictions_numerai(
    predictions: pd.DataFrame,
    model_id: str,
    tournament: str = "main",
    dry_run: bool = False,
) -> bool:
    """
    Submit predictions to Numerai (main / crypto / signals tournament).
    Returns True on success.
    """
    pub_key = os.environ.get("NUMERAI_PUBLIC_ID", "")
    sec_key = os.environ.get("NUMERAI_SECRET_KEY", "")

    if dry_run:
        log.info("DRY-RUN: submission skipped (shape: %s)", predictions.shape)
        return True

    if not pub_key or not sec_key:
        log.warning("NUMERAI API keys missing — skipping submission")
        return False

    if not model_id:
        log.warning("No model_id — skipping submission")
        return False

    fmt = _format_submission(predictions, tournament)
    log.info("Submission format (%s): columns=%s rows=%d", tournament, list(fmt.columns), len(fmt))

    import numerapi

    sub_dir = PROJECT_ROOT / "data" / "numerai" / "submissions"
    sub_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    sub_path = sub_dir / f"{tournament}_{ts}.csv"
    fmt.to_csv(sub_path, index=False)

    try:
        if tournament == "crypto":
            napi = numerapi.CryptoAPI(public_id=pub_key, secret_key=sec_key)
        elif tournament == "signals":
            napi = numerapi.SignalsAPI(public_id=pub_key, secret_key=sec_key)
        else:
            napi = numerapi.NumerAPI(public_id=pub_key, secret_key=sec_key)
        sub_id = napi.upload_predictions(str(sub_path), model_id=model_id)
        log.info("Submitted to %s tournament — submission_id=%s", tournament, sub_id)
        upload_to_gdrive(sub_path, "gdrive:backups/numerai/submissions/")
        return True
    except Exception as exc:
        log.error("Submission failed for %s: %s", tournament, exc)
        return False


def list_saved_models() -> list[dict]:
    """List all saved model pickles with metadata."""
    results = []
    for pkl in sorted(MODELS_DIR.glob("*.pkl")):
        name = pkl.stem
        meta_path = metadata_path(name)
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        results.append({
            "name": name,
            "size_mb": round(pkl.stat().st_size / 1e6, 2),
            "saved_at": meta.get("saved_at", "?"),
            "n_features": meta.get("n_features", "?"),
            "metrics": meta.get("metrics", {}),
        })
    return results


if __name__ == "__main__":
    _load_env()
    print("=== Saved Models ===")
    for m in list_saved_models():
        print(f"  {m['name']:30s} {m['saved_at'][:19]:s}  {m['n_features']:>4d} feats  {m['size_mb']:>6.2f}MB")
    print()
    print("=== Numerai Models (from API) ===")
    models = get_existing_model_ids()
    for name, mid in models.items():
        print(f"  {name:30s} → {mid}")
    print()
    print("=== Crypto Models (from API) ===")
    cmodels = get_crypto_model_ids()
    for name, mid in cmodels.items():
        print(f"  {name:30s} → {mid}")
