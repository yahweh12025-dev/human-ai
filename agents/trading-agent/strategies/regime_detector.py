"""
Regime Detection Layer (Trending/Ranging)
Detects market regime conditions to adapt trading strategies accordingly
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime classifications"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

class RegimeDetector:
    """
    Detects market regime conditions using multiple technical indicators
    Helps determine whether market is trending or ranging
    """
    
    def __init__(self, 
                 adx_threshold: float = 25.0,
                 rsi_overbought: float = 70.0,
                 rsi_oversold: float = 30.0,
                 bb_width_threshold: float = 0.05,
                 lookback_period: int = 20):
        """
        Initialize Regime Detector
        
        Args:
            adx_threshold: ADX value above which market is considered trending
            rsi_overbought: RSI level for overbought condition
            rsi_oversold: RSI level for oversold condition
            bb_width_threshold: Bollinger Band width threshold for ranging detection
            lookback_period: Period for calculating indicators
        """
        self.adx_threshold = adx_threshold
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.bb_width_threshold = bb_width_threshold
        self.lookback_period = lookback_period
        logger.info(f"RegimeDetector initialized with ADX threshold={adx_threshold}")
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()
        return atr
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index"""
        # Calculate +DM and -DM
        up_move = df['high'] - df['high'].shift()
        down_move = df['low'].shift() - df['low']
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Calculate True Range
        tr = self._calculate_atr(df, period)
        
        # Calculate smoothed +DM, -DM, and TR
        plus_di = 100 * (pd.Series(plus_dm).rolling(window=period).mean() / tr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(window=period).mean() / tr)
        
        # Calculate DX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # Calculate ADX
        adx = dx.rolling(window=period).mean()
        return adx
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, 
                                 period: int = 20, 
                                 std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        bandwidth = (upper_band - lower_band) / sma
        
        return upper_band, lower_band, bandwidth
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def detect_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect current market regime
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary containing regime detection results
        """
        # Ensure we have enough data
        if len(df) < self.lookback_period:
            return {
                'regime': MarketRegime.UNKNOWN,
                'confidence': 0.0,
                'indicators': {},
                'reason': 'Insufficient data for regime detection'
            }
        
        # Calculate indicators
        adx = self._calculate_adx(df)
        rsi = self._calculate_rsi(df)
        _, _, bb_width = self._calculate_bollinger_bands(df)
        atr = self._calculate_atr(df)
        
        # Get latest values
        latest_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0
        latest_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        latest_bb_width = bb_width.iloc[-1] if not pd.isna(bb_width.iloc[-1]) else 0
        latest_atr = atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0
        
        # Calculate price momentum
        price_change = df['close'].pct_change(periods=5).iloc[-1] if len(df) >= 5 else 0
        
        # Determine regime
        regime = MarketRegime.UNKNOWN
        confidence = 0.0
        reason = ""
        
        # Trending market conditions (ADX above threshold)
        if latest_adx > self.adx_threshold:
            # Determine direction of trend
            if price_change > 0.02:  # Strong upward movement
                regime = MarketRegime.TRENDING_UP
                confidence = min(latest_adx / 50, 0.9)  # Cap confidence at 0.9
                reason = f"Strong uptrend detected (ADX: {latest_adx:.1f}, 5-day change: {price_change:.2%})"
            elif price_change < -0.02:  # Strong downward movement
                regime = MarketRegime.TRENDING_DOWN
                confidence = min(latest_adx / 50, 0.9)
                reason = f"Strong downtrend detected (ADX: {latest_adx:.1f}, 5-day change: {price_change:.2%})"
            else:
                # Weak directional movement but still trending
                regime = MarketRegime.TRENDING_UP if price_change > 0 else MarketRegime.TRENDING_DOWN
                confidence = min(latest_adx / 50, 0.7)
                reason = f"Weak {'' if price_change > 0 else 'down'}trend detected (ADX: {latest_adx:.1f})"
        
        # Ranging market conditions (low ADX, low Bollinger Band width)
        elif latest_adx < self.adx_threshold and latest_bb_width < self.bb_width_threshold:
            regime = MarketRegime.RANGING
            confidence = min((1 - latest_adx / self.adx_threshold) * (1 - latest_bb_width / self.bb_width_threshold), 0.85)
            reason = f"Ranging market detected (ADX: {latest_adx:.1f} < {self.adx_threshold}, BB Width: {latest_bb_width:.3f} < {self.bb_width_threshold})"
        
        # High volatility conditions
        elif latest_atr > (df['close'].rolling(window=20).mean().iloc[-1] * 0.05):  # ATR > 5% of price
            regime = MarketRegime.VOLATILE
            confidence = min(latest_atr / (df['close'].mean() * 0.1), 0.8)  # Normalize ATR
            reason = f"High volatility detected (ATR: {latest_atr:.4f})"
        
        # Default to ranging if uncertain
        else:
            regime = MarketRegime.RANGING
            confidence = 0.3
            reason = "Unclear regime, defaulting to ranging"
        
        return {
            'regime': regime,
            'confidence': float(confidence),
            'indicators': {
                'adx': float(latest_adx),
                'rsi': float(latest_rsi),
                'bb_width': float(latest_bb_width),
                'atr': float(latest_atr),
                'price_change_5d': float(price_change)
            },
            'reason': reason
        }
    
    def get_regime_adjustments(self, regime: MarketRegime, confidence: float) -> Dict[str, Any]:
        """
        Get trading strategy adjustments based on detected regime
        
        Args:
            regime: Detected market regime
            confidence: Confidence in regime detection
            
        Returns:
            Dictionary of suggested strategy adjustments
        """
        adjustments = {
            'position_size_multiplier': 1.0,
            'stop_loss_multiplier': 1.0,
            'take_profit_multiplier': 1.0,
            'max_positions': 1,
            'signal_filters': [],
            'preferred_indicators': []
        }
        
        if regime == MarketRegime.TRENDING_UP:
            adjustments.update({
                'position_size_multiplier': 1.2 + (confidence * 0.3),  # Increase size in strong trends
                'stop_loss_multiplier': 1.1,  # Slightly tighter stops
                'take_profit_multiplier': 1.5 + (confidence * 0.5),  # Much larger targets
                'max_positions': 2,
                'signal_filters': ['volume_confirmation', 'momentum_alignment'],
                'preferred_indicators': ['moving_averages', 'macd', 'adx']
            })
        
        elif regime == MarketRegime.TRENDING_DOWN:
            adjustments.update({
                'position_size_multiplier': 1.0 + (confidence * 0.2),  # Moderate increase
                'stop_loss_multiplier': 1.0,  # Normal stops
                'take_profit_multiplier': 1.3 + (confidence * 0.3),  # Good targets
                'max_positions': 1,
                'signal_filters': ['volume_confirmation', 'momentum_alignment'],
                'preferred_indicators': ['moving_averages', 'macd', 'adx']
            })
        
        elif regime == MarketRegime.RANGING:
            adjustments.update({
                'position_size_multiplier': 0.8,  # Decrease size in ranging markets
                'stop_loss_multiplier': 0.9,  # Tighter stops
                'take_profit_multiplier': 0.8,  # Smaller targets
                'max_positions': 1,
                'signal_filters': ['oscillator_extremes', 'support_resistance'],
                'preferred_indicators': ['rsi', 'bollinger_bands', 'stochastic']
            })
        
        elif regime == MarketRegime.VOLATILE:
            adjustments.update({
                'position_size_multiplier': 0.6,  # Significantly decrease size
                'stop_loss_multiplier': 1.3,  # Much wider stops
                'take_profit_multiplier': 1.2,  # Moderate targets
                'max_positions': 1,
                'signal_filters': ['volatility_filter', 'news_avoidance'],
                'preferred_indicators': ['atr', 'vix', 'volume_profile']
            })
        
        # Adjust based on confidence
        confidence_factor = 0.5 + (confidence * 0.5)  # Scale from 0.5 to 1.0
        adjustments['position_size_multiplier'] *= confidence_factor
        
        return adjustments

# Example usage
if __name__ == "__main__":
    # Sample data for testing
    import yfinance as yf
    
    # Download sample data
    data = yf.download("BTC-USD", period="3mo", interval="1d")
    
    # Initialize regime detector
    detector = RegimeDetector(adx_threshold=25.0)
    
    # Detect regime
    regime_result = detector.detect_regime(data)
    
    print(f"Market Regime: {regime_result['regime'].value}")
    print(f"Confidence: {regime_result['confidence']:.2f}")
    print(f"Reason: {regime_result['reason']}")
    print("\nIndicators:")
    for key, value in regime_result['indicators'].items():
        print(f"  {key}: {value:.3f}")
    
    # Get strategy adjustments
    adjustments = detector.get_regime_adjustments(
        regime_result['regime'], 
        regime_result['confidence']
    )
    
    print("\nSuggested Strategy Adjustments:")
    for key, value in adjustments.items():
        print(f"  {key}: {value}")