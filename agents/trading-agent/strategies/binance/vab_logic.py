"""
Volume Analysis Bot (VAB) Core Logic
Implements volume-based trading strategies for cryptocurrency markets
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class VABCore:
    """
    Volume Analysis Bot Core Logic
    Analyzes volume patterns to generate trading signals
    """
    
    def __init__(self, volume_threshold: float = 2.0, lookback_period: int = 20):
        """
        Initialize VAB Core
        
        Args:
            volume_threshold: Multiplier for average volume to signal significant activity
            lookback_period: Number of periods to calculate average volume
        """
        self.volume_threshold = volume_threshold
        self.lookback_period = lookback_period
        logger.info(f"VAB Core initialized with threshold={volume_threshold}, lookback={lookback_period}")
    
    def calculate_volume_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volume-based trading signals
        
        Args:
            df: DataFrame with OHLCV data (must have 'volume' column)
            
        Returns:
            DataFrame with added volume signal columns
        """
        if 'volume' not in df.columns:
            raise ValueError("DataFrame must contain 'volume' column")
        
        # Calculate average volume over lookback period
        df['avg_volume'] = df['volume'].rolling(window=self.lookback_period).mean()
        
        # Calculate volume ratio (current volume / average volume)
        df['volume_ratio'] = df['volume'] / df['avg_volume']
        
        # Generate signals based on volume thresholds
        df['volume_spike'] = df['volume_ratio'] > self.volume_threshold
        df['volume_dry_up'] = df['volume_ratio'] < (1.0 / self.volume_threshold)
        
        # Price change confirmation
        df['price_change'] = df['close'].pct_change()
        df['bullish_volume'] = (df['volume_spike']) & (df['price_change'] > 0)
        df['bearish_volume'] = (df['volume_spike']) & (df['price_change'] < 0)
        
        return df
    
    def get_trading_signals(self, df: pd.DataFrame) -> List[Dict]:
        """
        Generate actionable trading signals from volume analysis
        
        Args:
            df: DataFrame with volume signals calculated
            
        Returns:
            List of signal dictionaries
        """
        signals = []
        
        # Get the most recent row with complete data
        latest = df.iloc[-1]
        
        if pd.isna(latest['avg_volume']):
            return signals  # Not enough data yet
        
        # Volume spike with bullish price action
        if latest['bullish_volume']:
            signals.append({
                'signal': 'BUY',
                'reason': f"Volume spike ({latest['volume_ratio']:.2f}x avg) with price increase",
                'strength': min(latest['volume_ratio'] / self.volume_threshold, 3.0),
                'volume_ratio': latest['volume_ratio'],
                'price_change': latest['price_change']
            })
        
        # Volume spike with bearish price action
        elif latest['bearish_volume']:
            signals.append({
                'signal': 'SELL',
                'reason': f"Volume spike ({latest['volume_ratio']:.2f}x avg) with price decrease",
                'strength': min(latest['volume_ratio'] / self.volume_threshold, 3.0),
                'volume_ratio': latest['volume_ratio'],
                'price_change': latest['price_change']
            })
        
        # Volume dry up (potential reversal)
        elif latest['volume_dry_up']:
            signals.append({
                'signal': 'WATCH',
                'reason': f"Volume dry up ({latest['volume_ratio']:.2f}x avg) - potential reversal",
                'strength': (1.0 - latest['volume_ratio']) * 2,
                'volume_ratio': latest['volume_ratio']
            })
        
        return signals
    
    def calculate_volume_profile(self, df: pd.DataFrame, price_bins: int = 50) -> Dict:
        """
        Calculate volume profile (volume at price levels)
        
        Args:
            df: DataFrame with OHLCV data
            price_bins: Number of price levels to bin volume into
            
        Returns:
            Dictionary with price levels and corresponding volume
        """
        if 'close' not in df.columns or 'volume' not in df.columns:
            raise ValueError("DataFrame must contain 'close' and 'volume' columns")
        
        # Create price bins
        price_min = df['low'].min()
        price_max = df['high'].max()
        bin_edges = np.linspace(price_min, price_max, price_bins + 1)
        
        # Approximate volume distribution (simplified)
        # In a real implementation, we'd use tick data or higher frequency data
        volume_profile = {}
        
        for i in range(len(bin_edges) - 1):
            bin_center = (bin_edges[i] + bin_edges[i+1]) / 2
            # Simplified: assign volume based on how much time price spent in bin
            # More accurate would require intraday data
            mask = (df['close'] >= bin_edges[i]) & (df['close'] < bin_edges[i+1])
            volume_in_bin = df.loc[mask, 'volume'].sum()
            volume_profile[round(bin_center, 4)] = volume_in_bin
        
        return volume_profile
    
    def detect_volume_divergence(self, df: pd.DataFrame, lookback: int = 10) -> List[Dict]:
        """
        Detect volume-price divergences
        
        Args:
            df: DataFrame with volume and price data
            lookback: Number of periods to look back for divergence
            
        Returns:
            List of divergence signals
        """
        signals = []
        
        if len(df) < lookback:
            return signals
        
        recent = df.tail(lookback)
        
        # Calculate price trend (linear regression on close prices)
        x = np.arange(len(recent))
        y_close = recent['close'].values
        y_volume = recent['volume'].values
        
        # Avoid division by zero
        if np.std(x) == 0:
            return signals
            
        price_slope = np.corrcoef(x, y_close)[0, 1] * (np.std(y_close) / np.std(x))
        volume_slope = np.corrcoef(x, y_volume)[0, 1] * (np.std(y_volume) / np.std(x))
        
        # Bullish divergence: price falling, volume rising
        if price_slope < -0.1 and volume_slope > 0.1:
            signals.append({
                'type': 'BULLISH_DIVERGENCE',
                'reason': 'Price declining while volume increasing',
                'price_slope': price_slope,
                'volume_slope': volume_slope
            })
        
        # Bearish divergence: price rising, volume falling
        elif price_slope > 0.1 and volume_slope < -0.1:
            signals.append({
                'type': 'BEARISH_DIVERGENCE',
                'reason': 'Price rising while volume decreasing',
                'price_slope': price_slope,
                'volume_slope': volume_slope
            })
        
        return signals

# Example usage
if __name__ == "__main__":
    # Sample data for testing
    import yfinance as yf
    
    # Download sample data
    data = yf.download("BTC-USD", period="1mo", interval="1h")
    
    # Initialize VAB
    vab = VABCore(volume_threshold=2.0, lookback_period=20)
    
    # Calculate signals
    df_with_signals = vab.calculate_volume_signals(data)
    signals = vab.get_trading_signals(df_with_signals)
    
    print(f"Generated {len(signals)} signals:")
    for signal in signals:
        print(f"  {signal}")