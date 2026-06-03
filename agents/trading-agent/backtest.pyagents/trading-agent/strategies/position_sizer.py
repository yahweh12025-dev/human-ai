#!/usr/bin/env python3
"""
Dynamic position sizing algorithm based on Regime Detection Layer outputs
Adjusts position sizes according to market regime, confidence, and risk parameters
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class PositionSizingMethod(Enum):
    """Different position sizing methods available"""
    FIXED_FRACTIONAL = "fixed_fractional"
    KELLY_CRITERION = "kelly_criterion"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    REGIME_BASED = "regime_based"

class MarketRegime(Enum):
    """Market regime classifications (matching RegimeDetector)"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

class DynamicPositionSizer:
    """
    Dynamic position sizing algorithm that adjusts trade sizes based on
    market regime detection outputs from the Regime Detection Layer
    """
    
    def __init__(self,
                 base_risk_percent: float = 2.0,
                 max_risk_percent: float = 5.0,
                 min_risk_percent: float = 0.5,
                 regime_multipliers: Optional[Dict[str, float]] = None,
                 confidence_scaling: bool = True,
                 volatility_lookback: int = 20):
        """
        Initialize the dynamic position sizer
        
        Args:
            base_risk_percent: Base percentage of capital to risk per trade (default 2%)
            max_risk_percent: Maximum percentage of capital to risk per trade (default 5%)
            min_risk_percent: Minimum percentage of capital to risk per trade (default 0.5%)
            regime_multipliers: Multipliers for different market regimes
            confidence_scaling: Whether to scale position size by regime confidence
            volatility_lookback: Period for calculating volatility adjustments
        """
        self.base_risk_percent = base_risk_percent
        self.max_risk_percent = max_risk_percent
        self.min_risk_percent = min_risk_percent
        self.confidence_scaling = confidence_scaling
        self.volatility_lookback = volatility_lookback
        
        # Default regime multipliers (adjust risk based on market conditions)
        self.regime_multipliers = regime_multipliers or {
            MarketRegime.TRENDING_UP.value: 1.5,      # Increase size in strong uptrends
            MarketRegime.TRENDING_DOWN.value: 1.2,    # Moderate increase in downtrends (for shorts)
            MarketRegime.RANGING.value: 0.8,          # Decrease size in ranging markets
            MarketRegime.VOLATILE.value: 0.5,         # Significantly decrease size in volatile markets
            MarketRegime.UNKNOWN.value: 0.6           # Conservative size when uncertain
        }
        
        logger.info(f"DynamicPositionSizer initialized with base risk: {base_risk_percent}%")
    
    def calculate_position_size(self, 
                              capital: float,
                              entry_price: float,
                              stop_loss_price: float,
                              regime_data: Optional[Dict[str, Any]] = None,
                              method: PositionSizingMethod = PositionSizingMethod.REGIME_BASED) -> Dict[str, Any]:
        """
        Calculate dynamic position size based on market regime and risk parameters
        
        Args:
            capital: Total available capital
            entry_price: Intended entry price
            stop_loss_price: Stop loss price
            regime_data: Output from RegimeDetectionLayer.detect_regime()
            method: Position sizing method to use
            
        Returns:
            Dictionary containing position size calculation details
        """
        # Validate inputs
        if capital <= 0:
            raise ValueError("Capital must be positive")
        
        if entry_price <= 0:
            raise ValueError("Entry price must be positive")
        
        if stop_loss_price <= 0:
            raise ValueError("Stop loss price must be positive")
        
        # Calculate risk per share/unit
        risk_per_unit = abs(entry_price - stop_loss_price)
        if risk_per_unit <= 0:
            raise ValueError("Entry price and stop loss price must be different")
        
        # Determine risk percentage based on method
        if method == PositionSizingMethod.REGIME_BASED:
            risk_percent = self._calculate_regime_based_risk(regime_data)
        elif method == PositionSizingMethod.VOLATILITY_ADJUSTED:
            risk_percent = self._calculate_volatility_adjusted_risk(regime_data)
        elif method == PositionSizingMethod.FIXED_FRACTIONAL:
            risk_percent = self.base_risk_percent
        elif method == PositionSizingMethod.KELLY_CRITERION:
            risk_percent = self._calculate_kelly_risk(regime_data)
        else:
            risk_percent = self.base_risk_percent  # Default to fixed fractional
        
        # Apply bounds
        risk_percent = max(self.min_risk_percent, min(self.max_risk_percent, risk_percent))
        
        # Calculate position size
        risk_amount = capital * (risk_percent / 100)
        position_size = risk_amount / risk_per_unit
        
        # Calculate actual values
        actual_risk_amount = position_size * risk_per_unit
        actual_risk_percent = (actual_risk_amount / capital) * 100
        
        result = {
            'position_size': position_size,
            'risk_amount': risk_amount,
            'risk_percent': risk_percent,
            'actual_risk_amount': actual_risk_amount,
            'actual_risk_percent': actual_risk_percent,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'capital': capital,
            'max_loss': actual_risk_amount,
            'method': method.value,
            'regime_data_used': regime_data is not None
        }
        
        # Add regime information if available
        if regime_data:
            result['regime'] = regime_data.get('regime', {}).value if hasattr(regime_data.get('regime'), 'value') else regime_data.get('regime', 'unknown')
            result['regime_confidence'] = regime_data.get('confidence', 0.0)
            result['regime_reason'] = regime_data.get('reason', '')
            
            # Add indicators if available
            if 'indicators' in regime_data:
                result['indicators'] = regime_data['indicators']
        
        logger.debug(f"Position size calculated: {position_size:.4f} units "
                    f"({risk_percent:.2f}% risk = ${risk_amount:.2f})")
        
        return result
    
    def _calculate_regime_based_risk(self, regime_data: Optional[Dict[str, Any]]) -> float:
        """
        Calculate risk percentage based on market regime and confidence
        
        Args:
            regime_data: Output from RegimeDetectionLayer
            
        Returns:
            Risk percentage to apply
        """
        if not regime_data:
            return self.base_risk_percent
        
        # Get regime and confidence
        regime_obj = regime_data.get('regime')
        confidence = regime_data.get('confidence', 0.0)
        
        # Extract regime value
        if hasattr(regime_obj, 'value'):
            regime = regime_obj.value
        elif isinstance(regime_obj, str):
            regime = regime_obj
        else:
            regime = str(regime_obj) if regime_obj else MarketRegime.UNKNOWN.value
        
        # Get base multiplier for this regime
        base_multiplier = self.regime_multipliers.get(regime, 1.0)
        
        # Apply confidence scaling if enabled
        if self.confidence_scaling and regime != MarketRegime.UNKNOWN.value:
            # Scale multiplier based on confidence (0.5 to 1.5 range)
            # Low confidence reduces effectiveness of regime signal
            confidence_factor = 0.5 + (confidence * 0.5)  # Maps [0,1] to [0.5, 1.0]
            adjusted_multiplier = 1.0 + ((base_multiplier - 1.0) * confidence_factor)
        else:
            # Use base multiplier regardless of confidence
            adjusted_multiplier = base_multiplier
        
        # Calculate final risk percentage
        risk_percent = self.base_risk_percent * adjusted_multiplier
        
        logger.debug(f"Regime-based risk calculation: {regime} (confidence: {confidence:.2f}) "
                    f"-> multiplier: {adjusted_multiplier:.2f} -> risk: {risk_percent:.2f}%")
        
        return risk_percent
    
    def _calculate_volatility_adjusted_risk(self, regime_data: Optional[Dict[str, Any]]) -> float:
        """
        Calculate risk percentage based on volatility indicators
        
        Args:
            regime_data: Output from RegimeDetectionLayer
            
        Returns:
            Risk percentage to apply
        """
        if not regime_data or 'indicators' not in regime_data:
            return self.base_risk_percent
        
        indicators = regime_data['indicators']
        atr = indicators.get('atr', 0)
        price = indicators.get('price_change_5d', 0)  # This is actually price change, not price
        
        # We need actual price for ATR% calculation, approximate from available data
        # In a real implementation, we'd pass the current price separately
        # For now, use a simplified approach based on ATR relative to typical price moves
        
        if atr > 0:
            # Normalize ATR - in practice we'd compare to historical ATR or price
            # Using a simplified heuristic: assume typical ATR% is around 1-3% for crypto
            atr_percent_estimate = min(atr * 100, 5.0)  # Cap at 5% for safety
            
            # Invert volatility relationship: higher volatility = lower position size
            if atr_percent_estimate > 3.0:  # High volatility
                volatility_factor = 0.5
            elif atr_percent_estimate > 1.5:  # Medium volatility
                volatility_factor = 0.75
            else:  # Low volatility
                volatility_factor = 1.2
            
            risk_percent = self.base_risk_percent * volatility_factor
        else:
            risk_percent = self.base_risk_percent
        
        logger.debug(f"Volatility-adjusted risk: ATR={atr:.4f} -> risk: {risk_percent:.2f}%")
        return risk_percent
    
    def _calculate_kelly_risk(self, regime_data: Optional[Dict[str, Any]]) -> float:
        """
        Calculate risk percentage using Kelly Criterion (simplified version)
        
        Args:
            regime_data: Output from RegimeDetectionLayer
            
        Returns:
            Risk percentage to apply (capped for safety)
        """
        # Kelly Criterion: f* = (bp - q) / b
        # where f* = fraction of capital to bet
        # b = net odds received on the bet (e.g., 2 for 2:1 odds)
        # p = probability of winning
        # q = probability of losing (1 - p)
        
        # Simplified approach using regime data to estimate win probability
        base_win_rate = 0.5  # 50% base win rate
        
        if regime_data:
            regime_obj = regime_data.get('regime')
            confidence = regime_data.get('confidence', 0.0)
            
            # Adjust win rate based on regime
            if hasattr(regime_obj, 'value'):
                regime = regime_obj.value
            elif isinstance(regime_obj, str):
                regime = regime_obj
            else:
                regime = str(regime_obj) if regime_obj else MarketRegime.UNKNOWN.value
            
            # Regime-based win rate adjustments
            regime_win_rate_adjustments = {
                MarketRegime.TRENDING_UP.value: 0.1,      # +10% win rate in uptrends
                MarketRegime.TRENDING_DOWN.value: 0.05,   # +5% win rate in downtrends
                MarketRegime.RANGING.value: -0.05,        # -5% win rate in ranging
                MarketRegime.VOLATILE.value: -0.15,       # -15% win rate in volatile
                MarketRegime.UNKNOWN.value: -0.1          # -10% win rate when uncertain
            }
            
            win_rate_adjustment = regime_win_rate_adjustments.get(regime, 0.0)
            adjusted_win_rate = base_win_rate + win_rate_adjustment
            
            # Apply confidence scaling
            if self.confidence_scaling:
                # Move win rate towards 50% based on low confidence
                confidence_adjustment = (0.5 - adjusted_win_rate) * (1.0 - confidence)
                adjusted_win_rate += confidence_adjustment
            
            # Keep win rate in reasonable bounds
            adjusted_win_rate = max(0.1, min(0.9, adjusted_win_rate))
        else:
            adjusted_win_rate = base_win_rate
        
        # Calculate Kelly fraction
        # Assuming average win/loss ratio of 1.5:1 (typical for good trading strategies)
        win_loss_ratio = 1.5
        p = adjusted_win_rate
        q = 1 - p
        b = win_loss_ratio
        
        kelly_fraction = (b * p - q) / b
        
        # Apply safety factors (never use full Kelly)
        # Use fractional Kelly (e.g., half-Kelly) to reduce volatility
        fractional_kelly = kelly_fraction * 0.5
        
        # Convert to percentage and apply bounds
        risk_percent = max(self.min_risk_percent, 
                          min(self.max_risk_percent, 
                              fractional_kelly * 100))
        
        logger.debug(f"Kelly risk calculation: win_rate={adjusted_win_rate:.2f} "
                    f"-> Kelly={kelly_fraction:.3f} -> Fractional={fractional_kelly:.3f} "
                    f"-> risk: {risk_percent:.2f}%")
        
        return risk_percent

# Convenience function for easy usage
def calculate_dynamic_position_size(capital: float,
                                  entry_price: float,
                                  stop_loss_price: float,
                                  regime_data: Optional[Dict[str, Any]] = None,
                                  base_risk_percent: float = 2.0) -> float:
    """
    Convenience function to calculate position size using dynamic sizing
    
    Args:
        capital: Total available capital
        entry_price: Intended entry price
        stop_loss_price: Stop loss price
        regime_data: Output from RegimeDetectionLayer (optional)
        base_risk_percent: Base risk percentage (default 2%)
        
    Returns:
        Position size in units
    """
    sizer = DynamicPositionSizer(base_risk_percent=base_risk_percent)
    result = sizer.calculate_position_size(
        capital=capital,
        entry_price=entry_price,
        stop_loss_price=stop_loss_price,
        regime_data=regime_data
    )
    return result['position_size']

# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create position sizer
    sizer = DynamicPositionSizer(
        base_risk_percent=2.0,
        max_risk_percent=5.0,
        min_risk_percent=0.5
    )
    
    # Example inputs
    capital = 10000.0  # $10,000 account
    entry_price = 65000.0  # BTC entry at $65,000
    stop_loss_price = 63000.0  # Stop loss at $63,000 ($2,000 risk)
    
    # Test different regime scenarios
    test_scenarios = [
        {
            'name': 'Strong Uptrend',
            'regime_data': {
                'regime': MarketRegime.TRENDING_UP,
                'confidence': 0.85,
                'reason': 'Strong uptrend detected (ADX: 35.2, 5-day change: +8.2%)',
                'indicators': {
                    'adx': 35.2,
                    'rsi': 68.5,
                    'bb_width': 0.032,
                    'atr': 1250.0,
                    'price_change_5d': 0.082
                }
            }
        },
        {
            'name': 'Ranging Market',
            'regime_data': {
                'regime': MarketRegime.RANGING,
                'confidence': 0.72,
                'reason': 'Ranging market detected (ADX: 18.5 < 25.0, BB Width: 0.042 < 0.05)',
                'indicators': {
                    'adx': 18.5,
                    'rsi': 52.3,
                    'bb_width': 0.042,
                    'atr': 850.0,
                    'price_change_5d': 0.005
                }
            }
        },
        {
            'name': 'Volatile Market',
            'regime_data': {
                'regime': MarketRegime.VOLATILE,
                'confidence': 0.68,
                'reason': 'High volatility detected (ATR: 0.085)',
                'indicators': {
                    'adx': 22.1,
                    'rsi': 48.7,
                    'bb_width': 0.068,
                    'atr': 2100.0,  # High ATR
                    'price_change_5d': -0.023
                }
            }
        },
        {
            'name': 'No Regime Data',
            'regime_data': None
        }
    ]
    
    print("Dynamic Position Sizing Examples:")
    print("=" * 50)
    print(f"Capital: ${capital:,.2f}")
    print(f"Entry Price: ${entry_price:,.2f}")
    print(f"Stop Loss: ${stop_loss_price:,.2f}")
    print(f"Risk per Unit: ${abs(entry_price - stop_loss_price):,.2f}")
    print()
    
    for scenario in test_scenarios:
        result = sizer.calculate_position_size(
            capital=capital,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            regime_data=scenario['regime_data']
        )
        
        print(f"{scenario['name']}:")
        print(f"  Position Size: {result['position_size']:.6f} BTC")
        print(f"  Risk Amount: ${result['risk_amount']:,.2f}")
        print(f"  Risk Percent: {result['risk_percent']:.2f}%")
        if result['regime_data_used']:
            print(f"  Regime: {result['regime']} (confidence: {result['regime_confidence']:.2f})")
        print()