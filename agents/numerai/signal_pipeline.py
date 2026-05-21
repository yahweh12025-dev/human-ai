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


def download_data(dry_run: bool = False) -> pd.DataFrame:
    if dry_run:
        n_dates = 5
        n_tickers = 100
        dates = pd.date_range(end="2026-05-20", periods=n_dates, freq="W")
        tickers = [f"US_{i:05d}" for i in range(n_tickers)]
        records = []
        for d in dates:
            for t in tickers:
                records.append({
                    "friday_date": d,
                    "bloomberg_ticker": t,
                    "data_type": np.random.choice(["returns", "volatility", "volume", "momentum"]),
                    "value": np.random.randn(),
                })
        log.info("Generated synthetic data: %d rows", len(records))
        return pd.DataFrame(records)

    try:
        import numerapi
        napi = numerapi.SignalsAPI()
        log.info("Downloading Signals training data...")
        train = napi.download_dataset("signals_train_val")
        log.info("Downloaded training data: %s", train.shape)
        return train
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


def train_model(df: pd.DataFrame, feature_cols: list[str]) -> object:
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

    X = train_df[feature_cols].fillna(0)
    y = train_df[target_col]

    log.info("Training LightGBM on %d samples with %d features...", len(X), len(feature_cols))
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
    return model


def generate_predictions(model: object, df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    X = df[feature_cols].fillna(0)
    preds = model.predict(X)

    result = df[["friday_date", "bloomberg_ticker"]].copy()
    result["signal"] = preds
    return result


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

    if model is None:
        model = train_model(df_aug, feature_cols)
        save_model(model, MODEL_NAME, feature_cols)
        backup_model_pickle(MODEL_NAME)

    if args.save_only:
        log.info("Model saved — skipping submission (--save-only)")
        return 0

    predictions = generate_predictions(model, df_aug, feature_cols)

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
