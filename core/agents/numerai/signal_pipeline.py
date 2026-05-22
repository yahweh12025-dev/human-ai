#!/usr/bin/env python3
"""
Numerai Signals Pipeline — US Equities Strategy
=================================================
Downloads Numerai Signals tournament data (US equities from Erasure),
engineers features from market data, trains a LightGBM model, and submits
predictions to the Numerai Signals tournament.

Usage:
    python3 agents/numerai/signal_pipeline.py --dry-run
    python3 agents/numerai/signal_pipeline.py --use-cached
    python3 agents/numerai/signal_pipeline.py --save-only

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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from agents.numerai.utils import (
    backup_model_pickle,
    hash_features,
    load_model,
    save_model,
    submit_predictions_numerai,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SIGNALS_DATA_DIR = DATA_DIR / "numerai" / "signals"
LOG_FILE = DATA_DIR / "logs" / "signal_numerai.log"
MODEL_NAME = "signal_model_alpha"
SIGNALS_DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("signal_pipeline")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Numerai Signals Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run without submitting.")
    parser.add_argument("--model-id", type=str, default="", help="Numerai Signals model ID for submission.")
    parser.add_argument("--use-cached", action="store_true", default=False,
                        help="Load existing pickle model instead of retraining.")
    parser.add_argument("--save-only", action="store_true", default=False,
                        help="Train and save model pickle without submitting.")
    parser.add_argument("--ticker-file", type=str, default="",
                        help="Path to CSV with ticker universe (optional, auto-downloaded if not provided).")
    return parser.parse_args()


def get_model_id(args_model_id: str) -> str:
    if args_model_id:
        return args_model_id
    config_path = Path(__file__).resolve().parent / "models_config.json"
    try:
        with open(config_path) as f:
            config = json.load(f)
        return config.get("signal_model_alpha", {}).get("model_id", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


DATA_VERSION = "signals/v2.1"
SIGNALS_DATA_DIR.mkdir(parents=True, exist_ok=True)

def download_data(dry_run: bool = False) -> pd.DataFrame:
    if dry_run:
        n_tickers = 100
        tickers = [f"US_{i:05d}" for i in range(n_tickers)]
        records = []
        for t in tickers:
            records.append({
                "numerai_ticker": t,
                "data_type": np.random.choice(["train", "validation"]),
                "feature_country": np.random.choice(["US", "JP", "KR", "HK", "DE"]),
                "feature_adv_20d_factor": np.random.randn(),
                "feature_beta_factor": np.random.randn(),
                "feature_market_cap_factor": np.random.randn(),
                "feature_momentum_12w_factor": np.random.randn(),
                "target": 0.5 + 0.1 * np.random.randn(),
            })
        log.info("Generated synthetic data: %d rows", len(records))
        return pd.DataFrame(records)

    try:
        import numerapi
        pub_key = os.environ.get("NUMERAI_PUBLIC_ID", "")
        sec_key = os.environ.get("NUMERAI_SECRET_KEY", "")
        napi = numerapi.SignalsAPI(public_id=pub_key, secret_key=sec_key) if pub_key and sec_key else numerapi.SignalsAPI()
        log.info("Downloading Signals training data (%s/train.parquet)...", DATA_VERSION)
        train_path = SIGNALS_DATA_DIR / "train.parquet"
        napi.download_dataset(f"{DATA_VERSION}/train.parquet", dest_path=str(train_path))
        train = pd.read_parquet(train_path)
        log.info("Downloaded training data: %s", train.shape)
        val_path = SIGNALS_DATA_DIR / "validation.parquet"
        napi.download_dataset(f"{DATA_VERSION}/validation.parquet", dest_path=str(val_path))
        val = pd.read_parquet(val_path)
        log.info("Downloaded validation data: %s", val.shape)
        return pd.concat([train, val], ignore_index=True)
    except Exception as e:
        log.warning("Failed to download Signals data from Numerai: %s", e)
        log.warning("Falling back to synthetic data for testing...")
        return download_data(dry_run=True)


def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    feature_cols = [c for c in df.columns if "feature" in c.lower() or "signal" in c.lower()]
    if feature_cols:
        log.info("Found %d pre-engineered features from Numerai", len(feature_cols))
        return df, feature_cols

    log.info("Engineering features from raw Signals data...")
    if "data_type" not in df.columns:
        log.warning("No data_type column — returning raw dataframe")
        return df, []

    df_pivot = df.pivot_table(
        index=["friday_date", "bloomberg_ticker"],
        columns="data_type",
        values="value",
        aggfunc="first",
    ).reset_index()
    df_pivot.columns.name = None

    numeric_cols = df_pivot.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [c for c in numeric_cols if c not in ("era", "data_type")]

    for col in numeric_cols:
        df_pivot[f"{col}_zscore"] = df_pivot.groupby("friday_date")[col].transform(
            lambda x: (x - x.mean()) / (x.std() + 1e-8)
        )
        feature_cols.append(f"{col}_zscore")

    log.info("Engineered %d features from pivot table", len(feature_cols))
    return df_pivot, feature_cols


def _encode_categoricals(df: pd.DataFrame, feature_cols: list[str], mapping: dict | None = None) -> tuple[pd.DataFrame, list[str], dict]:
    """Convert object dtype features to integer codes. Returns cleaned cols and mapping dict."""
    cleaned = df.copy()
    cat_encoders = mapping or {}
    for col in feature_cols:
        if cleaned[col].dtype.kind == "O":
            if mapping is None:
                cleaned[col], uniques = pd.factorize(cleaned[col].fillna("__NA__"))
                cat_encoders[col] = list(uniques)
            else:
                uniques = cat_encoders.get(col, [])
                cleaned[col] = cleaned[col].fillna("__NA__").map({v: i for i, v in enumerate(uniques)})
                cleaned[col] = cleaned[col].fillna(-1).astype(int)
    numeric_cols = [c for c in feature_cols if cleaned[c].dtype.kind in ("i", "f", "b")]
    return cleaned, numeric_cols, cat_encoders


def train_model(df: pd.DataFrame, feature_cols: list[str]) -> tuple[object, dict]:
    try:
        import lightgbm as lgb
    except ImportError:
        log.error("lightgbm not installed. Run: pip install lightgbm")
        sys.exit(1)

    target_col = "target" if "target" in df.columns else None
    if target_col is None:
        log.warning("No target column found — training on synthetic targets")
        df["target"] = 0.5 + 0.1 * df[feature_cols].mean(axis=1) + 0.1 * np.random.randn(len(df))
        target_col = "target"

    train_mask = df["data_type"] == "train" if "data_type" in df.columns else slice(None)
    train_df = df[train_mask].copy() if isinstance(train_mask, pd.Series) else df.copy()

    train_df, numeric_cols, cat_mapping = _encode_categoricals(train_df, feature_cols)

    X = train_df[numeric_cols].fillna(0)
    y = train_df[target_col]

    log.info("Training LightGBM on %d samples with %d features...", len(X), len(numeric_cols))
    params = {
        "objective": "regression",
        "metric": "rmse",
        "boosting_type": "gbdt",
        "num_leaves": 64,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "verbosity": -1,
        "n_jobs": -1,
    }
    model = lgb.train(params, lgb.Dataset(X, y), num_boost_round=500)
    log.info("Training complete")
    return model, cat_mapping


def generate_predictions(model: object, df: pd.DataFrame, feature_cols: list[str], cat_mapping: dict | None = None) -> pd.DataFrame:
    df, numeric_cols, _ = _encode_categoricals(df, feature_cols, mapping=cat_mapping)
    X = df[numeric_cols].fillna(0)
    preds = model.predict(X)

    ticker_col = "numerai_ticker" if "numerai_ticker" in df.columns else "bloomberg_ticker"
    result = pd.DataFrame({"numerai_ticker": df[ticker_col].values, "signal": np.clip(preds, 1e-9, 1 - 1e-9)})
    return result


def get_live_data() -> pd.DataFrame | None:
    """Download the Signals live universe data with features for prediction."""
    try:
        import numerapi
        pub_key = os.environ.get("NUMERAI_PUBLIC_ID", "")
        sec_key = os.environ.get("NUMERAI_SECRET_KEY", "")
        napi = numerapi.SignalsAPI(public_id=pub_key, secret_key=sec_key) if pub_key and sec_key else numerapi.SignalsAPI()
        live_path = SIGNALS_DATA_DIR / "live.parquet"
        napi.download_dataset(f"{DATA_VERSION}/live.parquet", dest_path=str(live_path))
        live = pd.read_parquet(live_path)
        log.info("Downloaded live data: %s", live.shape)
        return live
    except Exception as e:
        log.warning("Failed to download live data: %s", e)
        return None


def main() -> int:
    args = parse_args()

    model_id = get_model_id(args.model_id)
    if not model_id and not args.dry_run:
        log.warning(
            "No Signals model ID configured. "
            "Create a model at https://signals.numer.ai/ and add model_id to models_config.json"
        )

    log.info("=" * 60)
    log.info("Numerai Signals Pipeline | dry_run=%s | use_cached=%s | save_only=%s",
             args.dry_run, args.use_cached, args.save_only)
    log.info("Model name : %s | model_id=%s", MODEL_NAME, model_id or "(not set)")
    log.info("Data dir   : %s", SIGNALS_DATA_DIR)
    log.info("=" * 60)

    df = download_data(dry_run=args.dry_run)

    df_aug, feature_cols = engineer_features(df)

    cat_mapping = None
    model = None
    if args.use_cached:
        model, meta = load_model(MODEL_NAME)
        if model is not None:
            feat_hash = hash_features(feature_cols)
            cached_hash = meta.get("feature_hash", "")
            if feat_hash != cached_hash:
                log.warning("Feature hash mismatch — retraining")
                model = None
            else:
                log.info("Using cached model from %s", meta.get("saved_at", "?"))
                cat_mapping = meta.get("cat_mapping")

    if model is None:
        model, cat_mapping = train_model(df_aug, feature_cols)
        save_model(model, MODEL_NAME, feature_cols, extra={"cat_mapping": cat_mapping})
        backup_model_pickle(MODEL_NAME)

    if args.save_only:
        log.info("Model saved — skipping submission (--save-only)")
        return 0

    live_data = get_live_data()
    if live_data is not None:
        log.info("Predicting on Signals live data: %s", live_data.shape)
        predictions = generate_predictions(model, live_data, feature_cols, cat_mapping=cat_mapping)
    else:
        predictions = generate_predictions(model, df_aug, feature_cols, cat_mapping=cat_mapping)

    success = submit_predictions_numerai(
        predictions,
        model_id=model_id,
        tournament="signals",
        dry_run=args.dry_run,
    )

    log.info("=" * 60)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
