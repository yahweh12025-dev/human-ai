import numpy as np
import pandas as pd
from typing import List, Dict, Any, Callable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdversarialMarketGenerator:
    """
    Generates synthetic 'black swan' and adversarial market conditions
    to stress-test trading strategies.
    """
    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(seed)

    def generate_flash_crash(self, base_price: float, duration: int = 10, crash_depth: float = 0.15) -> pd.Series:
        """Simulates a sudden, sharp price drop followed by a partial recovery."""
        prices = [base_price]
        # Crash phase
        for i in range(duration):
            prices.append(prices[-1] * (1 - (crash_depth / duration) + np.random.normal(0, 0.001)))
        # Recovery phase
        for i in range(duration * 2):
            prices.append(prices[-1] * (1 + (crash_depth / 2 / (duration * 2)) + np.random.normal(0, 0.002)))
        return pd.Series(prices)

    def generate_extreme_volatility(self, base_price: float, duration: int = 100, vol_multiplier: float = 5.0) -> pd.Series:
        """Simulates a high-volatility regime (e.g., news-driven chaos)."""
        returns = np.random.normal(0, 0.01 * vol_multiplier, duration)
        price_path = base_price * np.exp(np.cumsum(returns))
        return pd.Series(price_path)

    def generate_mean_reversion_trap(self, base_price: float, duration: int = 100) -> pd.Series:
        """Simulates a market that looks mean-reverting but then breaks out strongly (trap)."""
        prices = [base_price]
        for i in range(duration // 2):
            prices.append(base_price + np.random.normal(0, 1.0))
        # Strong breakout
        for i in range(duration // 2):
            prices.append(prices[-1] * (1 + 0.01 + np.random.normal(0, 0.005)))
        return pd.Series(prices)

class StrategyStressTester:
    """
    Executes a strategy against adversarial scenarios and reports robustness metrics.
    """
    def __init__(self, strategy_fn: Callable[[pd.Series], List[str]]):
        """
        strategy_fn: A function that takes a price series and returns a list of signals ('BUY', 'SELL', 'HOLD')
        """
        self.strategy_fn = strategy_fn

    def run_scenario(self, name: str, data: pd.Series) -> Dict[str, Any]:
        signals = self.strategy_fn(data)
        # Simple PnL calculation
        returns = data.pct_change().fillna(0)
        positions = pd.Series(signals).map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).shift(1).fillna(0)
        strategy_returns = positions * returns
        
        cumulative_return = strategy_returns.sum()
        max_drawdown = (data / data.cummax() - 1).min()
        
        return {
            "scenario": name,
            "cumulative_return": cumulative_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252) if strategy_returns.std() != 0 else 0
        }

    def run_full_suite(self, base_price: float = 100.0) -> List[Dict[str, Any]]:
        generator = AdversarialMarketGenerator()
        scenarios = [
            ("Flash Crash", generator.generate_flash_crash(base_price)),
            ("Extreme Volatility", generator.generate_extreme_volatility(base_price)),
            ("Mean Reversion Trap", generator.generate_mean_reversion_trap(base_price)),
        ]
        
        results = []
        for name, data in scenarios:
            results.append(self.run_scenario(name, data))
        return results

if __name__ == "__main__":
    # Mock strategy: BUY if price drops 1%, SELL if price rises 1% (Simple mean reversion)
    def mock_strategy(data: pd.Series):
        signals = []
        for i in range(1, len(data)):
            change = (data.iloc[i] - data.iloc[i-1]) / data.iloc[i-1]
            if change < -0.01: signals.append('BUY')
            elif change > 0.01: signals.append('SELL')
            else: signals.append('HOLD')
        # Pad first element
        return ['HOLD'] + signals

    tester = StrategyStressTester(mock_strategy)
    results = tester.run_full_suite()
    for res in results:
        print(f"Scenario: {res['scenario']} | Return: {res['cumulative_return']:.4f} | MaxDD: {res['max_drawdown']:.4f}")
