import os
import sys
import json
import numpy as np
from typing import Dict, List, Any, Callable
from scipy.optimize import differential_evolution
import logging

# Add the scripts directory to sys.path to import CustomBacktester
sys.path.append('/home/yahwehatwork/human-ai/scripts')
from custom_backtester import CustomBacktester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BayesianOptimizer:
    def __init__(
        self,
        strategy_module_path: str,
        strategy_class_name: str,
        data_path: str,
        timerange: str,
        output_dir: str,
        symbol: str = "BTC_USDT",
        timeframe: str = "1h",
        leverage: int = 1,
        param_bounds: Dict[str, List[float]] = None
    ):
        self.strategy_module_path = strategy_module_path
        self.strategy_class_name = strategy_class_name
        self.data_path = data_path
        self.timerange = timerange
        self.output_dir = output_dir
        self.symbol = symbol
        self.timeframe = timeframe
        self.leverage = leverage
        self.param_bounds = param_bounds if param_bounds else {}
        
        os.makedirs(self.output_dir, exist_ok=True)

    def _objective(self, param_values: np.ndarray, param_names: List[str]) -> float:
        # Map array values back to dictionary
        params = {name: float(val) for name, val in zip(param_names, param_values)}
        
        try:
            tester = CustomBacktester(
                strategy_module_path=self.strategy_module_path,
                strategy_class_name=self.strategy_class_name,
                data_path=self.data_path,
                timerange=self.timerange,
                output_dir=os.path.join(self.output_dir, "temp_runs"),
                symbol=self.symbol,
                timeframe=self.timeframe,
                leverage=self.leverage,
                params=params
            )
            results = tester.run()
            # We want to MAXIMIZE total_return, so we MINIMIZE negative total_return
            return -results['total_return']
        except Exception as e:
            logger.error(f"Error during optimization step with params {params}: {e}")
            return 0.0  # Return 0 (neutral) on error to avoid getting stuck in bad regions

    def optimize(self, popsize: int = 15, maxiter: int = 20):
        if not self.param_bounds:
            raise ValueError("No parameter bounds provided for optimization.")

        param_names = list(self.param_bounds.keys())
        bounds = [self.param_bounds[name] for name in param_names]

        logger.info(f"🚀 Starting optimization for {self.strategy_class_name}...")
        logger.info(f"Parameters: {self.param_bounds}")

        # Differential Evolution is a great choice for hyperparameter optimization
        # as it doesn't require gradients and handles non-convex landscapes well.
        result = differential_evolution(
            self._objective,
            bounds=bounds,
            args=(param_names,),
            popsize=popsize,
            maxiter=maxiter,
            polish=True,
            disp=True
        )

        best_params = {name: float(val) for name, val in zip(param_names, result.x)}
        best_return = -result.fun

        logger.info(f"✨ Optimization complete!")
        logger.info(f"Best Params: {best_params}")
        logger.info(f"Best Return: {best_return:.2%}")

        # Final run with best params to get full results and save them
        logger.info("Running final backtest with best parameters...")
        tester = CustomBacktester(
            strategy_module_path=self.strategy_module_path,
            strategy_class_name=self.strategy_class_name,
            data_path=self.data_path,
            timerange=self.timerange,
            output_dir=self.output_dir,
            symbol=self.symbol,
            timeframe=self.timeframe,
            leverage=self.leverage,
            params=best_params
        )
        final_results = tester.run()

        # Save optimization report
        report = {
            "optimization_timestamp": datetime.now().isoformat(),
            "strategy": self.strategy_class_name,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "leverage": self.leverage,
            "timerange": self.timerange,
            "best_params": best_params,
            "best_return": best_return,
            "final_results": final_results
        }
        
        report_path = os.path.join(self.output_dir, f"optimization_report_{self.strategy_class_name}_{self.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Optimization report saved to {report_path}")

        return best_params, best_return, final_results

if __name__ == "__main__":
    # Example usage
    from datetime import datetime
    
    # This needs to match your actual strategy file and class
    STRATEGY_PATH = "/home/yahwehatwork/human-ai/apps/alpha_integration/freqtrade_strategies/ai_driven_btc_strategy_v4.py"
    STRATEGY_CLASS = "AI_Driven_BTC_Strategy_V4"
    
    # Define the search space (bounds for hyperparameters)
    # The keys MUST match the names used in the strategy's self.config.get('key', default)
    BOUNDS = {
        'rsi_period': [10.0, 30.0],
        'rsi_upper_threshold': [60.0, 80.0],
        'rsi_lower_threshold': [20.0, 40.0],
        'adx_threshold': [20.0, 30.0],
        'ema_fast_period': [8.0, 18.0],
        'ema_slow_period': [20.0, 40.0]
    }

    optimizer = BayesianOptimizer(
        strategy_module_path=STRATEGY_PATH,
        strategy_class_name=STRATEGY_CLASS,
        data_path="/home/yahwehatwork/human-ai/agents/freqtrade/user_data/data/binance",
        timerange="20240101-20240501",
        output_dir="/home/yahwehatwork/human-ai/validation/optimization_results/",
        symbol="BTC_USDT",
        timeframe="1h",
        leverage=1,
        param_bounds=BOUNDS
    )

    optimizer.optimize(popsize=10, maxiter=10)
