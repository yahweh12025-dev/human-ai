import sys
import os
import json
import logging
from datetime import datetime
import pandas as pd

# Add current directory to sys.path to allow importing scripts.custom_backtester
sys.path.append('/home/yahwehatwork/human-ai')
from scripts.custom_backtester import CustomBacktester

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_robust_backtest():
    """
    Runs a series of backtests across different time periods, symbols, 
    and leverages to ensure the strategy is robust and not overfit.
    """
    strategy_path = "/home/yahwehatwork/human-ai/apps/alpha_integration/freqtrade_strategies/ai_driven_btc_strategy_v7.py"
    strategy_class = "AI_Driven_BTC_Strategy_V7"
    data_dir = "/home/yahwehatwork/human-ai/agents/freqtrade/user_data/data/binance"
    output_dir = "/home/yahwehatwork/human-ai/validation/freqtrade_backtests/"

    # 1. Define Test Matrix
    test_scenarios = [
        {"name": "Q1_2024_Trend", "timerange": "20240101-20240331", "symbol": "BTC_USDT", "tf": "1h", "lev": 1},
        {"name": "Q2_2024_Sideways", "timerange": "20240401-20240501", "symbol": "BTC_USDT", "tf": "1h", "lev": 1},
    ]

    leverage_scenarios = [1, 3, 5]
    timeframe_scenarios = ["1h"]

    results_summary = []

    logger.info("🚀 Starting Robust Backtesting Campaign (V7 - Regime Switcher)...")

    for scenario in test_scenarios:
        for tf in timeframe_scenarios:
            for lev in leverage_scenarios:
                try:
                    tester = CustomBacktester(
                        strategy_module_path=strategy_path,
                        strategy_class_name=strategy_class,
                        data_path=data_dir,
                        timerange=scenario["timerange"],
                        output_dir=output_dir,
                        symbol=scenario["symbol"],
                        timeframe=tf,
                        leverage=lev
                    )
                    res = tester.run()
                    res['scenario_name'] = scenario['name']
                    res['timeframe_tested'] = tf
                    res['leverage_tested'] = lev
                    results_summary.append(res)
                except Exception as e:
                    logger.error(f"❌ Failed Scenario: {scenario['name']} | TF: {tf} | Lev: {lev}x | Error: {e}")

    if not results_summary:
        logger.error("⚠️ No successful backtests performed.")
        return

    summary_file = os.path.join(output_dir, f"robust_summary_V7_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(summary_file, 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    logger.info(f"🏁 Robust Campaign Complete. Summary: {summary_file}")
    print("\n" + "="*80)
    print(f"{'SCENARIO':<20} | {'TF':<4} | {'LEV':<4} | {'RETURN':<10} | {'TRADES':<6}")
    print("-" * 80)
    for r in results_summary:
        print(f"{r['scenario_name']:<20} | {r['timeframe_tested']:<4} | {r['leverage_tested']:<4} | {r['total_return']:>9.2%} | {r['trade_count']:>6}")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_robust_backtest()
