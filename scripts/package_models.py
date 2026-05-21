#!/usr/bin/env python3
"""
Generate cloudpickle predict files for Numerai Model Uploads.
Produces one .pkl per model with the proper predict() function signature.

Usage:
    python3 scripts/package_models.py

Output:
    data/numerai/cloudpickle/human_ai_alpha_predict.pkl
    data/numerai/cloudpickle/crypto_binance_v1_predict.pkl
    data/numerai/cloudpickle/signal_model_alpha_predict.pkl
"""
import json
import sys
from pathlib import Path

import cloudpickle
import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "data" / "numerai" / "models"
OUTPUT_DIR = PROJECT_ROOT / "data" / "numerai" / "cloudpickle"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

np.seterr(invalid='ignore')


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


def package_main_model():
    model_path = MODELS_DIR / "human_ai_alpha.pkl"
    meta_path = MODELS_DIR / "human_ai_alpha_metadata.json"

    model = joblib.load(model_path)
    with open(meta_path) as f:
        meta = json.load(f)

    all_feature_names = meta["feature_names"]
    base_features = [c for c in all_feature_names if not c.startswith("eng_")]
    derived_features = [c for c in all_feature_names if c.startswith("eng_")]

    pilot_feature_map = {}
    for col in all_feature_names:
        for prefix in ["eng_rsi_", "eng_ema_slope_", "eng_boll_width_"]:
            if col.startswith(prefix):
                base_name = col[len(prefix):]
                pilot_feature_map[base_name] = True

    pilot_features = list(pilot_feature_map.keys())

    def predict(live_features: pd.DataFrame, live_benchmark_models: pd.DataFrame) -> pd.DataFrame:
        df = live_features.copy()
        for col in pilot_features:
            if col not in df.columns:
                df[col] = 2.0
            series = df[col].astype(float)
            df[f"eng_rsi_{col}"] = _rsi(series, 14).fillna(2.0)
            df[f"eng_ema_slope_{col}"] = _ema_slope(series, 10).fillna(0.0)
            df[f"eng_boll_width_{col}"] = _bollinger_width(series, 10).fillna(0.0)
        df["eng_vol_proxy"] = df[pilot_features].sub(2).abs().mean(axis=1)
        df["eng_atr_proxy"] = df[pilot_features].std(axis=1).fillna(0.0)
        for col in all_feature_names:
            if col not in df.columns:
                df[col] = 0.0
        X = df[all_feature_names].fillna(0)
        preds = model.predict(X)
        return pd.Series(preds, index=live_features.index).to_frame("prediction")

    return predict, "human_ai_alpha"


def package_crypto_model():
    model_path = MODELS_DIR / "crypto_binance_v1.pkl"
    meta_path = MODELS_DIR / "crypto_binance_v1_metadata.json"

    model = joblib.load(model_path)
    with open(meta_path) as f:
        meta = json.load(f)

    all_feature_names = meta["feature_names"]
    base_features = [c for c in all_feature_names if not c.startswith("bs_")]
    derived_features = [c for c in all_feature_names if c.startswith("bs_")]

    def predict(live_features: pd.DataFrame, live_benchmark_models: pd.DataFrame) -> pd.DataFrame:
        data = live_features.copy()
        cols_present = set(data.columns)

        close_ewa_20 = "feature_close_ewa_20d"
        close_ewa_60 = "feature_close_ewa_60d"
        rsi_20 = "feature_relative_strength_index_20d"
        rsi_60 = "feature_relative_strength_index_60d"
        momentum_20 = "feature_momentum_20d"
        momentum_60 = "feature_momentum_60d"
        vol20 = "feature_volatility_20d"
        vol60 = "feature_volatility_60d"
        vol_avg_20 = "feature_volume_avg_20d"
        bollinger_20 = "feature_bollinger_20d"
        bollinger_60 = "feature_bollinger_60d"

        if close_ewa_20 in cols_present and close_ewa_60 in cols_present:
            data["bs_ema_cross"] = np.where(data[close_ewa_20] > data[close_ewa_60], 1, 0)
            data["bs_ema_cross_strength"] = (data[close_ewa_20] - data[close_ewa_60]).clip(-1, 1)

        if rsi_20 in cols_present:
            data["bs_rsi_buy_zone"] = np.where(data[rsi_20] < 40, 1, 0)
            data["bs_rsi_sell_zone"] = np.where(data[rsi_20] > 60, 1, 0)
            data["bs_rsi_mid"] = (data[rsi_20] - 50) / 50

        if rsi_20 in cols_present and rsi_60 in cols_present:
            data["bs_rsi_slope"] = data[rsi_20] - data[rsi_60]

        if momentum_20 in cols_present:
            data["bs_mom_strength"] = data[momentum_20].clip(-1, 1)

        if momentum_20 in cols_present and vol20 in cols_present:
            data["bs_mom_vol_combo"] = data[momentum_20] * (1 - data[vol20])

        if vol_avg_20 in cols_present:
            data["bs_vol_ok"] = np.where(data[vol_avg_20] > 0.5, 1, 0)

        if bollinger_20 in cols_present and bollinger_60 in cols_present:
            data["bs_bollinger_ratio"] = data[bollinger_20] / (data[bollinger_60] + 1e-8)

        for col in all_feature_names:
            if col not in data.columns:
                data[col] = 0.0

        X = data[all_feature_names].fillna(0)
        preds = model.predict(X)
        return pd.Series(preds, index=live_features.index).to_frame("prediction")

    return predict, "crypto_binance_v1"


def package_signals_model():
    model_path = MODELS_DIR / "signal_model_alpha.pkl"
    meta_path = MODELS_DIR / "signal_model_alpha_metadata.json"

    import lightgbm as lgb
    model = joblib.load(model_path)
    with open(meta_path) as f:
        meta = json.load(f)

    all_feature_names = meta["feature_names"]

    def predict(live_features: pd.DataFrame, live_benchmark_models: pd.DataFrame) -> pd.DataFrame:
        data = live_features.copy()
        if "data_type" in data.columns:
            df_pivot = data.pivot_table(
                index=["friday_date", "bloomberg_ticker"],
                columns="data_type", values="value", aggfunc="first",
            ).reset_index()
            df_pivot.columns.name = None
        else:
            df_pivot = data

        numeric_cols = df_pivot.select_dtypes(include=[np.number]).columns.tolist()
        for col in numeric_cols:
            if col in ("era", "data_type"):
                continue
            df_pivot[f"{col}_zscore"] = df_pivot.groupby("friday_date")[col].transform(
                lambda x: (x - x.mean()) / (x.std() + 1e-8)
            )

        for col in all_feature_names:
            if col not in df_pivot.columns:
                df_pivot[col] = 0.0

        X = df_pivot[all_feature_names].fillna(0)
        preds = model.predict(X)
        return pd.Series(preds, index=df_pivot.index).to_frame("prediction")

    return predict, "signal_model_alpha"


def main():
    packages = [
        package_main_model,
        package_crypto_model,
        package_signals_model,
    ]

    for pkg_fn in packages:
        predict_fn, name = pkg_fn()
        out_path = OUTPUT_DIR / f"{name}_predict.pkl"
        with open(out_path, "wb") as f:
            cloudpickle.dump(predict_fn, f)
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"Created {out_path.name} ({size_mb:.1f} MB)")

    print("\nDone. Upload these files at https://numer.ai/submissions")


if __name__ == "__main__":
    main()
