#!/usr/bin/env python3
"""
Numerai Crypto Pipeline — Binance Strategy Port
=================================================
Downloads Numerai Crypto tournament data, engineers features mirroring
the Binance scalping strategy (EMA crossovers, RSI timing, ATR/volatility,
momentum, volume confirmation), trains a LightGBM model, and submits
predictions to the Numerai Crypto tournament.

Usage:
    python3 agents/numerai/crypto_pipeline.py --dry-run
    python3 agents/numerai/crypto_pipeline.py
    python3 agents/numerai/crypto_pipeline.py --model-id <model_id> --use-cached

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
    upload_to_gdrive,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CRYPTO_DATA_DIR = DATA_DIR / "numerai" / "crypto"
LOG_FILE = DATA_DIR / "logs" / "crypto_numerai.log"
MODEL_NAME = "crypto_binance_v1"
CRYPTO_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("crypto_numerai_pipeline")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
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


def _load_env() -> dict:
    env_path = PROJECT_ROOT / ".env"
    loaded = {}
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
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + missing)
        log.info("Packages installed.")


DATA_VERSION = "crypto/v2.0"


def _get_capi():
    import numerapi
    pub_key = os.environ.get("NUMERAI_PUBLIC_ID", "")
    sec_key = os.environ.get("NUMERAI_SECRET_KEY", "")
    if pub_key and sec_key:
        log.info("Using authenticated CryptoAPI")
        return numerapi.CryptoAPI(public_id=pub_key, secret_key=sec_key)
    log.info("Using anonymous CryptoAPI")
    return numerapi.CryptoAPI()


def download_data(dry_run: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    train_file = CRYPTO_DATA_DIR / "train.parquet"
    live_file = CRYPTO_DATA_DIR / "live.parquet"
    already_cached = train_file.exists() and live_file.exists()

    if already_cached:
        log.info("Loading cached data from %s", CRYPTO_DATA_DIR)
        train = pd.read_parquet(train_file)
        live = pd.read_parquet(live_file)
        feature_cols = [c for c in train.columns if c.startswith("feature_")]
        return _post_download(train, live, feature_cols)

    if dry_run:
        log.info("DRY-RUN: generating synthetic crypto data")
        return _make_synthetic_data()

    napi = _get_capi()
    log.info("Downloading %s/train.parquet ...", DATA_VERSION)
    dl_path = napi.download_dataset(
        f"{DATA_VERSION}/train.parquet",
        dest_path=str(train_file),
    )
    log.info("Downloaded to: %s", dl_path)
    log.info("Downloading %s/live.parquet ...", DATA_VERSION)
    dl_path = napi.download_dataset(
        f"{DATA_VERSION}/live.parquet",
        dest_path=str(live_file),
    )
    log.info("Downloaded to: %s", dl_path)

    train = pd.read_parquet(train_file)
    live = pd.read_parquet(live_file)
    feature_cols = [c for c in train.columns if c.startswith("feature_")]
    return _post_download(train, live, feature_cols)


def _post_download(train, live, feature_cols):
    target_cols = [c for c in train.columns if c.startswith("target_")]
    log.info("Train: %d rows, %d features, %d targets", len(train), len(feature_cols), len(target_cols))
    log.info("Targets: %s", target_cols)
    log.info("Eras (dates): %d", train["date"].nunique())
    train = train[train["date"].isin(train["date"].unique()[::8])]
    log.info("Downsampled to %d rows (%d dates)", len(train), train["date"].nunique())
    live_features = [c for c in live.columns if c.startswith("feature_")]
    log.info("Live: %d rows, %d features", len(live), len(live_features))
    return train, live, feature_cols


def _make_synthetic_data() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    rng = np.random.default_rng(42)
    n_coins = 300
    n_days = 200
    features = [
        "feature_bollinger_20d", "feature_bollinger_60d",
        "feature_close_avg_20d", "feature_close_avg_60d",
        "feature_close_ewa_20d", "feature_close_ewa_60d",
        "feature_market_cap_avg_20d", "feature_market_cap_avg_60d",
        "feature_market_cap_ewa_20d", "feature_market_cap_ewa_60d",
        "feature_momentum_20d", "feature_momentum_60d",
        "feature_relative_strength_index_20d", "feature_relative_strength_index_60d",
        "feature_sharpe_ratio_20d", "feature_sharpe_ratio_60d",
        "feature_volatility_20d", "feature_volatility_60d",
        "feature_volume_avg_20d", "feature_volume_avg_60d",
        "feature_volume_ewa_20d", "feature_volume_ewa_60d",
    ]
    rows = []
    ucid = 1
    for _ in range(n_coins):
        for day in range(n_days):
            row = {"ucid": ucid, "date": f"2024-{day//30+1:02d}-{(day%30)+1:02d}"}
            for f in features:
                row[f] = rng.uniform(0, 1)
            row["target_binned_return_20"] = rng.choice([0.0, 0.25, 0.5, 0.75, 1.0])
            row["target_binned_return_60"] = rng.choice([0.0, 0.25, 0.5, 0.75, 1.0])
            rows.append(row)
        ucid += 1
    train = pd.DataFrame(rows)

    live_rows = []
    for ucid in range(1, n_coins + 1):
        row = {"ucid": ucid, "date": "2026-05-15"}
        for f in features:
            row[f] = rng.uniform(0, 1)
        live_rows.append(row)
    live = pd.DataFrame(live_rows)

    log.info("Synthetic: %d train rows, %d live rows, %d features", len(train), len(live), len(features))
    return train, live, features


def engineer_binance_features(df: pd.DataFrame, feature_set: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """
    Engineer features that mirror the Binance scalping bot strategy:
    - EMA crossover signals (fast vs slow EWA)
    - RSI timing signals
    - Momentum + volatility combos
    - Volume confirmation
    """
    data = df.copy()
    derived = []

    close_ewa_20 = "feature_close_ewa_20d"
    close_ewa_60 = "feature_close_ewa_60d"
    rsi_20 = "feature_relative_strength_index_20d"
    rsi_60 = "feature_relative_strength_index_60d"
    momentum_20 = "feature_momentum_20d"
    momentum_60 = "feature_momentum_60d"
    volatility_20 = "feature_volatility_20d"
    volatility_60 = "feature_volatility_60d"
    volume_20 = "feature_volume_avg_20d"
    volume_60 = "feature_volume_avg_60d"
    bollinger_20 = "feature_bollinger_20d"
    bollinger_60 = "feature_bollinger_60d"

    cols_present = set(data.columns)

    # EMA crossover signal: fast EWA > slow EWA = bullish
    if close_ewa_20 in cols_present and close_ewa_60 in cols_present:
        data["bs_ema_cross"] = np.where(data[close_ewa_20] > data[close_ewa_60], 1, 0)
        data["bs_ema_cross_strength"] = (data[close_ewa_20] - data[close_ewa_60]).clip(-1, 1)
        derived += ["bs_ema_cross", "bs_ema_cross_strength"]

    # RSI timing: below 40 = oversold (buy zone), above 60 = overbought (sell zone)
    if rsi_20 in cols_present:
        data["bs_rsi_buy_zone"] = np.where(data[rsi_20] < 40, 1, 0)
        data["bs_rsi_sell_zone"] = np.where(data[rsi_20] > 60, 1, 0)
        data["bs_rsi_mid"] = (data[rsi_20] - 50) / 50
        derived += ["bs_rsi_buy_zone", "bs_rsi_sell_zone", "bs_rsi_mid"]

    # RSI divergence: RSI-20 vs RSI-60
    if rsi_20 in cols_present and rsi_60 in cols_present:
        data["bs_rsi_slope"] = data[rsi_20] - data[rsi_60]
        derived += ["bs_rsi_slope"]

    # Momentum confirmation: positive momentum + bullish crossover = strong signal
    if momentum_20 in cols_present:
        data["bs_mom_strength"] = data[momentum_20].clip(-1, 1)
        derived += ["bs_mom_strength"]

    # Momentum + volatility combo (from the Binance ATR + momentum logic)
    if momentum_20 in cols_present and volatility_20 in cols_present:
        data["bs_mom_vol_combo"] = data[momentum_20] * (1 - data[volatility_20])
        derived += ["bs_mom_vol_combo"]

    # Volume confirmation: above-average volume confirms signal
    if volume_20 in cols_present:
        data["bs_vol_ok"] = np.where(data[volume_20] > 0.5, 1, 0)
        derived += ["bs_vol_ok"]

    # Bollinger squeeze (low volatility setup)
    if bollinger_20 in cols_present and bollinger_60 in cols_present:
        data["bs_bollinger_ratio"] = data[bollinger_20] / (data[bollinger_60] + 1e-8)
        derived += ["bs_bollinger_ratio"]

    all_features = feature_set + derived
    log.info("Features: %d base + %d Binance-derived = %d", len(feature_set), len(derived), len(all_features))
    return data, all_features


def era_validate(train: pd.DataFrame, feature_cols: list[str]):
    import lightgbm as lgb
    from sklearn.model_selection import GroupKFold
    from scipy.stats import pearsonr

    dates = train["date"].values
    groups = pd.factorize(dates)[0]
    gkf = GroupKFold(n_splits=3)
    target = "target_binned_return_20"

    cv_scores = []
    for fold, (train_idx, val_idx) in enumerate(gkf.split(train, groups=groups)):
        log.info("CV fold %d/3 ...", fold + 1)
        X_tr = train.iloc[train_idx][feature_cols].fillna(0)
        y_tr = train.iloc[train_idx][target]
        X_val = train.iloc[val_idx][feature_cols].fillna(0)
        y_val = train.iloc[val_idx][target]

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


def train_model(train: pd.DataFrame, feature_cols: list[str]):
    import lightgbm as lgb
    target = "target_binned_return_20"

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
    model.fit(train[feature_cols].fillna(0), train[target])
    elapsed = time.time() - t0
    log.info("Model trained in %.1f seconds.", elapsed)
    return model


def generate_predictions(model, live: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    log.info("Generating predictions for %d coins ...", len(live))
    preds = model.predict(live[feature_cols].fillna(0))
    submission = pd.DataFrame({"ucid": live["ucid"].values, "prediction": np.clip(preds, 1e-9, 1 - 1e-9)})
    log.info(
        "Predictions — mean: %.4f  std: %.4f  min: %.4f  max: %.4f",
        submission["prediction"].mean(), submission["prediction"].std(),
        submission["prediction"].min(), submission["prediction"].max(),
    )
    # Map ucid to coin symbol via meta_model.csv
    try:
        mm_path = CRYPTO_DATA_DIR / "meta_model.csv"
        if not mm_path.exists():
            import numerapi
            capi = _get_capi()
            capi.download_dataset("crypto/v2.0/meta_model.csv", dest_path=str(mm_path))
        mm = pd.read_csv(mm_path)
        mm["id"] = mm["id"].astype(str)
        id_to_symbol = dict(zip(mm["id"], mm["symbol"]))
        submission["symbol"] = submission["ucid"].astype(str).map(id_to_symbol)
        submission = submission.dropna(subset=["symbol"])
        log.info("Mapped %d/%d ucids to symbols", len(submission), len(live))
    except Exception as e:
        log.warning("ucid→symbol mapping failed: %s — using ucid as-is", e)
        submission["symbol"] = submission["ucid"].astype(str)

    submission = submission.set_index("symbol")[["prediction"]]
    submission.index.name = "symbol"
    return submission


def submit_predictions(predictions: pd.DataFrame, model_id: str, dry_run: bool = False) -> bool:
    pub_key = os.environ.get("NUMERAI_PUBLIC_ID", "")
    sec_key = os.environ.get("NUMERAI_SECRET_KEY", "")

    if dry_run:
        log.info("DRY-RUN: Skipping submission (shape: %s).", predictions.shape)
        log.info("Preview:\n%s", predictions.head(3).to_string())
        return True

    if not pub_key or not sec_key:
        log.warning("API credentials missing — skipping submission.")
        return False

    if not model_id:
        log.warning("No --model-id — skipping submission.")
        return False

    import numerapi
    napi = numerapi.CryptoAPI(public_id=pub_key, secret_key=sec_key)

    sub_path = CRYPTO_DATA_DIR / "crypto_predictions.csv"
    predictions.to_csv(sub_path)
    log.info("Submitting %s to model %s ...", sub_path, model_id)

    try:
        sub_id = napi.upload_predictions(str(sub_path), model_id=model_id)
        log.info("Submission successful! submission_id=%s", sub_id)
        return True
    except Exception as exc:
        log.error("Submission failed: %s", exc)
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Numerai Crypto Pipeline — Binance Strategy Port",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run without submitting.")
    parser.add_argument("--model-id", type=str, default="", help="Numerai Crypto model ID for submission.")
    parser.add_argument("--use-cached", action="store_true", default=False,
                        help="Load existing pickle model instead of retraining.")
    parser.add_argument("--save-only", action="store_true", default=False,
                        help="Train and save model pickle without submitting.")
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
    log.info("Numerai Crypto Pipeline | dry_run=%s | use_cached=%s | save_only=%s",
             args.dry_run, args.use_cached, args.save_only)
    log.info("Model name : %s | model_id=%s", MODEL_NAME, model_id or "(no model ID)")
    log.info("Project root: %s", PROJECT_ROOT)
    log.info("Data dir: %s", CRYPTO_DATA_DIR)
    log.info("Log file: %s", LOG_FILE)
    log.info("Model name: %s", MODEL_NAME)
    log.info("=" * 60)

    _load_env()
    _ensure_packages()

    train_df, live_df, feature_set = download_data(dry_run=args.dry_run)

    train_aug, all_features = engineer_binance_features(train_df, feature_set)
    live_aug, _ = engineer_binance_features(live_df, feature_set)

    for col in all_features:
        if col not in live_aug.columns:
            live_aug[col] = 0.0

    # Try loading cached model
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

    if model is None:
        if os.environ.get("NUMERAI_CV", "0") == "1":
            era_validate(train_aug, all_features)
        model = train_model(train_aug, all_features)
        save_model(model, MODEL_NAME, all_features)
        backup_model_pickle(MODEL_NAME)

    if args.save_only:
        log.info("Model saved — skipping submission (--save-only)")
        log.info("=" * 60)
        return 0

    predictions = generate_predictions(model, live_aug, all_features)
    success = submit_predictions_numerai(
        predictions, model_id=model_id, tournament="crypto", dry_run=args.dry_run
    )

    if success:
        log.info("Pipeline completed successfully.")
    else:
        log.warning("Pipeline completed but submission was skipped or failed.")

    log.info("=" * 60)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
