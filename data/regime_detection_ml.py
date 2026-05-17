import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from typing import Dict, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RegimeDetectionML:
    """
    Automated market regime detection system using unsupervised learning (GMM) 
    on multiple timeframes.
    """
    def __init__(self, n_regimes: int = 3):
        self.n_regimes = n_regimes
        self.model = GaussianMixture(n_components=n_regimes, random_state=42)

    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Extracts volatility and momentum features for regime detection."""
        returns = df['close'].pct_change().dropna()
        vol = returns.rolling(window=20).std().dropna()
        mom = returns.rolling(window=20).mean().dropna()
        
        features = np.column_stack([vol, mom])
        return features

    def fit_and_predict(self, df: pd.DataFrame) -> pd.Series:
        """Clusters the market into regimes."""
        X = self.prepare_features(df)
        regimes = self.model.fit_predict(X)
        
        # Map results back to the original dataframe index
        res = pd.Series(index=df.index, data=np.nan)
        res.iloc[20:] = regimes # First 20 are NaN due to rolling window
        return res

if __name__ == "__main__":
    df = pd.DataFrame({"close": np.cumsum(np.random.randn(500)) + 100})
    detector = RegimeDetectionML()
    regimes = detector.fit_and_predict(df)
    print(f"Detected Regimes for last 5 bars:\n{regimes.tail()}")
