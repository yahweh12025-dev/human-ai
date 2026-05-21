#!/usr/bin/env python3
"""
Numerai ML Pipeline — Human-AI Swarm Integration
=================================================
Downloads Numerai tournament data, engineers features (RSI, ATR, EMA slopes,
volume, Bollinger width), trains a LightGBM model, generates predictions, and
optionally submits to the Numerai tournament if NUMERAI_API_KEY is set.

Usage:
    python3 agents/numerai/numerai_pipeline.py --dry-run
    python3 agents/numerai/numerai_pipeline.py
    python3 agents/numerai/numerai_pipeline.py --model-id <your_model_id>

From the human-ai project root.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent   # .../human-ai/
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"
NUMERAI_DATA_DIR = DATA_DIR / "numerai"
LOG_FILE = LOG_DIR / "numerai.log"
MODEL_NAME = "human_ai_alpha"

sys.path.insert(0, str(PROJECT_ROOT))
from agents.numerai.utils import (
    backup_model_pickle,
    hash_features,
    load_model,
    save_model,
    submit_predictions_numerai,
)

LOG_DIR.mkdir(parents=True, exist_ok=True)
NUMERAI_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging: file + console
# ---------------------------------------------------------------------------
def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("numerai_pipeline")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


log = _setup_logging()

# ---------------------------------------------------------------------------
# .env loader (project uses a plain .env file, no dotenv required)
# ---------------------------------------------------------------------------
def _load_env() -> dict:
    """Load .env from project root into os.environ (simple key=value parser)."""
    env_path = PROJECT_ROOT / ".env"
    loaded: dict = {}
    if not env_path.exists():
        return loaded
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


# ---------------------------------------------------------------------------
# Dependency installer (auto-installs missing packages into active venv)
# ---------------------------------------------------------------------------
def _ensure_packages() -> None:
    required = {"numerapi": "numerapi", "lightgbm": "lightgbm", "pyarrow": "pyarrow"}
    missing = []
    for import_name, pkg_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg_name)
    if missing:
        log.info("Installing missing packages: %s", missing)
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q"] + missing
        )
        log.info("Packages installed.")


# ---------------------------------------------------------------------------
# Numerai data download
# ---------------------------------------------------------------------------
DATA_VERSION = "v5.2"
FEATURE_SET = "small"   # "small"=42 features, "medium"=780, "all"=2748


def _get_napi():
    """Return an authenticated or anonymous NumerAPI client."""
    import numerapi  # noqa: E402 — installed above
    pub_key = os.environ.get("NUMERAI_PUBLIC_ID", "")
    sec_key = os.environ.get("NUMERAI_SECRET_KEY", "")
    if pub_key and sec_key:
        log.info("Using authenticated NumerAPI (NUMERAI_PUBLIC_ID set)")
        return numerapi.NumerAPI(public_id=pub_key, secret_key=sec_key)
    log.info("Using anonymous NumerAPI (no credentials — download only)")
    return numerapi.NumerAPI()


def download_data(dry_run: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Download Numerai training data and live features.
    Returns (train_df, live_features_df, feature_names).

    In dry-run mode with no cached data, generates synthetic data so the
    rest of the pipeline can be exercised without network access.
    """
    features_file = NUMERAI_DATA_DIR / f"{DATA_VERSION}" / "features.json"
    train_file = NUMERAI_DATA_DIR / f"{DATA_VERSION}" / "train.parquet"
    live_file = NUMERAI_DATA_DIR / f"{DATA_VERSION}" / "live.parquet"

    already_cached = features_file.exists() and train_file.exists() and live_file.exists()

    if dry_run and not already_cached:
        log.info("DRY-RUN: No cached data found — generating synthetic dataset.")
        return _make_synthetic_data()

    napi = _get_napi()

    # Change CWD so NumerAPI saves files relative to our data dir
    original_cwd = os.getcwd()
    os.chdir(NUMERAI_DATA_DIR)
    try:
        log.info("Downloading %s/features.json ...", DATA_VERSION)
        napi.download_dataset(f"{DATA_VERSION}/features.json")

        feature_metadata = json.loads(features_file.read_text())
        feature_set = feature_metadata["feature_sets"][FEATURE_SET]
        log.info("Feature set '%s': %d features", FEATURE_SET, len(feature_set))

        log.info("Downloading %s/train.parquet ...", DATA_VERSION)
        napi.download_dataset(f"{DATA_VERSION}/train.parquet")

        log.info("Downloading %s/live.parquet ...", DATA_VERSION)
        napi.download_dataset(f"{DATA_VERSION}/live.parquet")

    finally:
        os.chdir(original_cwd)

    # Load training data (aggressive downsampling for memory-constrained env)
    log.info("Loading training data (every 8th era) ...")
    train = pd.read_parquet(
        train_file,
        columns=["era", "target"] + feature_set,
    )
    train = train[train["era"].isin(train["era"].unique()[::8])]
    log.info("Training rows: %d | eras: %d", len(train), train["era"].nunique())

    # Load live features
    log.info("Loading live features ...")
    live_features = pd.read_parquet(live_file, columns=feature_set)
    log.info("Live rows: %d", len(live_features))

    return train, live_features, feature_set


def _make_synthetic_data() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Generate small synthetic data that mirrors Numerai's schema."""
    rng = np.random.default_rng(42)
    n_features = 42
    feature_names = [f"feature_{i:04d}" for i in range(n_features)]

    # 200 stocks x 20 eras = 4 000 training rows
    n_stocks = 200
    n_eras = 20
    rows = []
    for era_i in range(1, n_eras + 1):
        era_label = str(era_i).zfill(4)
        feat_vals = rng.integers(0, 5, size=(n_stocks, n_features))
        targets = rng.choice([0.0, 0.25, 0.5, 0.75, 1.0], size=n_stocks)
        for s in range(n_stocks):
            row = {"era": era_label, "target": targets[s]}
            for fi, fn in enumerate(feature_names):
                row[fn] = feat_vals[s, fi]
            rows.append(row)
    train = pd.DataFrame(rows)

    # 50 live rows
    live_feat = rng.integers(0, 5, size=(50, n_features)).astype(float)
    live_ids = [f"n{i:016x}" for i in range(50)]
    live_features = pd.DataFrame(live_feat, index=live_ids, columns=feature_names)

    log.info(
        "Synthetic data: %d train rows, %d live rows, %d features",
        len(train), len(live_features), n_features,
    )
    return train, live_features, feature_names


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
def _rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _ema_slope(series: pd.Series, span: int = 10) -> pd.Series:
    ema = series.ewm(span=span, adjust=False).mean()
    return ema.diff()


def _bollinger_width(series: pd.Series, window: int = 20) -> pd.Series:
    ma = series.rolling(window).mean()
    std = series.rolling(window).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    mid = ma.replace(0, np.nan)
    return (upper - lower) / mid


def engineer_features(train: pd.DataFrame, feature_set: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """
    Add trading-style derived features on top of the raw Numerai features.
    Because Numerai features are already binned integers (0-4) representing
    cross-sectional ranks, the derived signals still carry relative ordering
    information useful to tree-based models.

    Returns (augmented_df, all_feature_columns).
    """
    log.info("Engineering derived features (RSI, ATR, EMA slopes, Bollinger) ...")

    df = train.copy()

    # Choose a handful of base features to derive signals from.
    # We pick the first few to keep this deterministic across dataset versions.
    pilot = feature_set[:8] if len(feature_set) >= 8 else feature_set

    derived_cols: list[str] = []

    for col in pilot:
        series = df[col].astype(float)

        rsi_col = f"eng_rsi_{col}"
        df[rsi_col] = _rsi(series, window=14).fillna(2.0)   # fill with neutral value
        derived_cols.append(rsi_col)

        ema_col = f"eng_ema_slope_{col}"
        df[ema_col] = _ema_slope(series, span=10).fillna(0.0)
        derived_cols.append(ema_col)

        bw_col = f"eng_boll_width_{col}"
        df[bw_col] = _bollinger_width(series, window=10).fillna(0.0)
        derived_cols.append(bw_col)

    # Simulated volume feature: row-wise mean of feature values (proxy for
    # cross-sectional "intensity" — higher absolute deviation from neutral=2)
    df["eng_vol_proxy"] = df[pilot].sub(2).abs().mean(axis=1)
    derived_cols.append("eng_vol_proxy")

    # ATR proxy: rolling std across pilot features per row (cross-sectional)
    df["eng_atr_proxy"] = df[pilot].std(axis=1).fillna(0.0)
    derived_cols.append("eng_atr_proxy")

    all_features = feature_set + derived_cols
    log.info(
        "Features: %d base + %d derived = %d total",
        len(feature_set), len(derived_cols), len(all_features),
    )
    return df, all_features


def apply_feature_engineering(
    live_features: pd.DataFrame,
    feature_set: list[str],
) -> tuple[pd.DataFrame, list[str]]:
    """Apply the same derived-feature logic to live data (no target column)."""
    # Wrap in a fake train-like df then strip
    dummy = live_features.copy()
    dummy["era"] = "live"
    dummy["target"] = 0.5
    augmented, all_features = engineer_features(dummy, feature_set)
    return augmented, all_features


# ---------------------------------------------------------------------------
# Era-wise cross-validation
# ---------------------------------------------------------------------------
def era_validate(train: pd.DataFrame, feature_cols: list[str]):
    """GroupKFold on eras to simulate live generalization."""
    import lightgbm as lgb
    from sklearn.model_selection import GroupKFold
    from scipy.stats import pearsonr

    eras = train["era"].values
    groups = pd.factorize(eras)[0]
    gkf = GroupKFold(n_splits=5)

    cv_scores = []
    for fold, (train_idx, val_idx) in enumerate(gkf.split(train, groups=groups)):
        log.info("CV fold %d/5 ...", fold + 1)
        X_tr = train.iloc[train_idx][feature_cols].fillna(0)
        y_tr = train.iloc[train_idx]["target"]
        X_val = train.iloc[val_idx][feature_cols].fillna(0)
        y_val = train.iloc[val_idx]["target"]

        m = lgb.LGBMRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=5, num_leaves=31,
            colsample_bytree=0.1, subsample=0.8, extra_trees=True,
            boosting_type="gbdt", max_bin=63, n_jobs=-1, verbose=-1,
        )
        m.fit(X_tr, y_tr)
        preds = m.predict(X_val)
        corr = pearsonr(y_val, preds)[0]
        cv_scores.append(corr)
        log.info("  Fold %d CORR: %.4f", fold + 1, corr)

    log.info("CV CORR: mean=%.4f  std=%.4f", np.mean(cv_scores), np.std(cv_scores))
    return cv_scores


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------
def train_model(train: pd.DataFrame, feature_cols: list[str]):
    """Train a LightGBM regressor on the augmented training data."""
    import lightgbm as lgb  # noqa: E402

    log.info("Training LightGBM on %d rows x %d features ...", len(train), len(feature_cols))
    t0 = time.time()

    model = lgb.LGBMRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=5,
        num_leaves=31,
        colsample_bytree=0.1,
        subsample=0.8,
        extra_trees=True,
        boosting_type="gbdt",
        max_bin=63,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(
        train[feature_cols].fillna(0),
        train["target"],
    )
    elapsed = time.time() - t0
    log.info("Model trained in %.1f seconds.", elapsed)
    return model


# ---------------------------------------------------------------------------
# Prediction generation
# ---------------------------------------------------------------------------
def generate_predictions(
    model,
    live_features: pd.DataFrame,
    feature_cols: list[str],
) -> pd.DataFrame:
    """Run model inference on live features and return a formatted submission."""
    log.info("Generating live predictions for %d stocks ...", len(live_features))
    preds = model.predict(live_features[feature_cols].fillna(0))
    submission = pd.Series(preds, index=live_features.index, name="prediction")
    # Numerai expects predictions in [0, 1]; clip just in case
    submission = submission.clip(0, 1)
    log.info(
        "Predictions stats — mean: %.4f  std: %.4f  min: %.4f  max: %.4f",
        submission.mean(), submission.std(), submission.min(), submission.max(),
    )
    return submission.to_frame("prediction")


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------
def submit_predictions(
    predictions: pd.DataFrame,
    model_id: str,
    dry_run: bool = False,
) -> bool:
    """
    Submit live predictions to Numerai.
    Returns True on success (or dry-run skip), False on error.
    """
    pub_key = os.environ.get("NUMERAI_PUBLIC_ID", "")
    sec_key = os.environ.get("NUMERAI_SECRET_KEY", "")

    if dry_run:
        log.info("DRY-RUN: Skipping submission (predictions shape: %s).", predictions.shape)
        preview = predictions.head(3).to_string()
        log.info("Prediction preview:\n%s", preview)
        return True

    if not pub_key or not sec_key:
        log.warning(
            "NUMERAI_PUBLIC_ID / NUMERAI_SECRET_KEY not set in .env — skipping submission."
        )
        return False

    if not model_id:
        log.warning("No --model-id provided — skipping submission.")
        return False

    import numerapi  # noqa: E402
    napi = numerapi.NumerAPI(public_id=pub_key, secret_key=sec_key)

    # Save predictions to a temp CSV for submission
    sub_path = NUMERAI_DATA_DIR / "live_predictions.csv"
    predictions.to_csv(sub_path)
    log.info("Submitting %s to model %s ...", sub_path, model_id)

    try:
        sub_id = napi.upload_predictions(str(sub_path), model_id=model_id)
        log.info("Submission successful! submission_id=%s", sub_id)
        return True
    except Exception as exc:
        log.error("Submission failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Numerai ML Pipeline — Human-AI Swarm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help=(
            "Run the full pipeline without submitting predictions. "
            "Uses cached data if available, otherwise generates synthetic data."
        ),
    )
    parser.add_argument(
        "--model-id",
        type=str,
        default="",
        help="Numerai model ID for submission (default: from models_config.json).",
    )
    parser.add_argument(
        "--feature-set",
        choices=["small", "medium", "all"],
        default=FEATURE_SET,
        help="Numerai feature set to use (default: small).",
    )
    parser.add_argument(
        "--data-version",
        type=str,
        default=DATA_VERSION,
        help="Numerai dataset version (default: v5.2).",
    )
    parser.add_argument(
        "--use-cached", action="store_true", default=False,
        help="Load existing pickle model instead of retraining.",
    )
    parser.add_argument(
        "--save-only", action="store_true", default=False,
        help="Train and save model pickle without submitting.",
    )
    return parser.parse_args()


def get_model_id(args_model_id: str, config_name: str = MODEL_NAME) -> str:
    if args_model_id:
        return args_model_id
    config_path = Path(__file__).resolve().parent / "models_config.json"
    try:
        with open(config_path) as f:
            config = json.load(f)
        return config.get(config_name, {}).get("model_id", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


def main() -> int:
    args = parse_args()

    model_id = get_model_id(args.model_id)
    log.info("=" * 60)
    log.info("Numerai Pipeline starting | dry_run=%s | feature_set=%s | use_cached=%s | save_only=%s",
             args.dry_run, args.feature_set, args.use_cached, args.save_only)
    log.info("Model name : %s | model_id=%s", MODEL_NAME, model_id or "(no model ID)")
    log.info("Project root : %s", PROJECT_ROOT)
    log.info("Data dir     : %s", NUMERAI_DATA_DIR)
    log.info("Log file     : %s", LOG_FILE)
    log.info("=" * 60)

    # Load .env
    env_vars = _load_env()
    log.debug("Loaded %d vars from .env", len(env_vars))

    # Ensure dependencies
    _ensure_packages()

    # 1. Download data
    global DATA_VERSION, FEATURE_SET
    DATA_VERSION = args.data_version
    FEATURE_SET = args.feature_set

    train_df, live_df, feature_set = download_data(dry_run=args.dry_run)

    # 2. Feature engineering on training data
    train_aug, all_features = engineer_features(train_df, feature_set)

    # 3. Apply same engineering to live data
    live_aug, _ = apply_feature_engineering(live_df, feature_set)

    # Make sure live_aug has all columns present in train_aug
    for col in all_features:
        if col not in live_aug.columns:
            live_aug[col] = 0.0

    # 4. Try loading cached model
    model = None
    if args.use_cached:
        model, meta = load_model(MODEL_NAME)
        if model is not None:
            feat_hash = hash_features(all_features)
            cached_hash = meta.get("feature_hash", "")
            if feat_hash != cached_hash:
                log.warning("Feature hash mismatch (%s vs %s) — retraining", cached_hash, feat_hash)
                model = None
            else:
                log.info("Using cached model from %s", meta.get("saved_at", "?"))

    # 5. Train if no cached model
    if model is None:
        if os.environ.get("NUMERAI_CV", "0") == "1":
            cv_scores = era_validate(train_aug, all_features)
        else:
            log.info("Skipping era-wise CV. Set NUMERAI_CV=1 to enable.")
        model = train_model(train_aug, all_features)
        save_model(model, MODEL_NAME, all_features)
        backup_model_pickle(MODEL_NAME)

    # 6. Save-only mode
    if args.save_only:
        log.info("Model saved — skipping submission (--save-only)")
        log.info("=" * 60)
        return 0

    # 7. Generate predictions
    predictions = generate_predictions(model, live_aug, all_features)

    # 8. Submit (or skip in dry-run / missing key)
    success = submit_predictions_numerai(
        predictions,
        model_id=model_id,
        tournament="main",
        dry_run=args.dry_run,
    )

    if success:
        log.info("Pipeline completed successfully.")
    else:
        log.warning("Pipeline completed but submission was skipped or failed.")

    log.info("=" * 60)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
