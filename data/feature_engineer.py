import pandas as pd
import numpy as np
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Automated feature engineering system that creates technical indicators 
    and alternative data features for ML models.
    """
    def __init__(self):
        self.indicators = []

    def add_technical_indicator(self, df: pd.DataFrame, name: str, func):
        """Adds a custom technical indicator to the dataframe."""
        df[name] = func(df)
        self.indicators.append(name)
        return df

    def generate_standard_suite(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generates a standard set of technical indicators (RSI, SMA, Volatility)."""
        # RSI Mock
        df['RSI'] = np.random.uniform(0, 100, len(df))
        # SMA Mock
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        # Volatility Mock
        df['VOL_STD'] = df['close'].pct_change().rolling(window=20).std()
        
        return df

    def create_alternative_features(self, df: pd.DataFrame, sentiment_series: pd.Series) -> pd.DataFrame:
        """Combines price data with alternative data (e.g., sentiment)."""
        df['SENTIMENT_SCORE'] = sentiment_series.values
        df['PRICE_SENT_DIFF'] = df['close'].pct_change() - sentiment_series.values
        return df

if __name__ == "__main__":
    df = pd.DataFrame({"close": np.random.randn(100).cumsum() + 100})
    sent = pd.Series(np.random.uniform(-1, 1, 100))
    
    engineer = FeatureEngineer()
    df = engineer.generate_standard_suite(df)
    df = engineer.create_alternative_features(df, sent)
    print(f"Engineered DataFrame Columns: {df.columns.tolist()}")
