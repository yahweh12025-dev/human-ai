import sys
import os
import json
import logging
from datetime import datetime
from custom_backtester import CustomBacktester

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_comprehensive_backtest():
    # Paths
    strategy_path = "/home/yahwehatwork/human-ai/apps/alpha_integration/freqtrade_strategies/ai_driven_btc_strategy_v5.py"
    strategy_class = "AI_Driven_BTC_Strategy_V5"
    data_dir = "/home/yahwehatwork/human-ai/agents/freqtrade/user_data/data/binance"
    output_dir = "/home/yahwehatwork/human-ai/validation/freqtrade_backtests/"
    timerange = "20240101-20240501"

    # Test Matrix
    # Note: Since we only have BTC_USDT-1h.feather, 
    # we will vary Timeframe and Leverage. 
    # If more coins were available, we'd add them to symbols.
    symbols = ["BTC_USDT"] 
    timeframes = ["1h"]
    leverages = [1, 3, 5]

    results_summary = []

    for symbol in symbols:
        for tf in timeframes:
            for lev in leverages:
                try:
                    tester = CustomBacktester(
                        strategy_module_path=strategy_path,
                        strategy_class_name=strategy_class,
                        data_path=data_dir,
                        timerange=timerange,
                        output_dir=output_dir,
                        symbol=symbol,
                        timeframe=tf,
                        leverage=lev
                    )
                    res = tester.run()
                    results_summary.append(res)
                except Exception as e:
                    logger.error(f"Failed backtest for {symbol}-{tf} @ {lev}x: {e}")

    # Save summary
    summary_file = os.path.join(output_dir, f"backtest_summary_V5_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(summary_file, 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    logger.info(f"🚀 All tests completed. Summary saved to {summary_file}")
    for r in results_summary:
        print(f"[{r['symbol']} | {r['timeframe']} | {r['leverage']}x] Return: {r['total_return']:.2%}")

if __name__ == "__main__":
    # Add current directory to sys.path to allow importing scripts.custom_backtester
    sys.path.append('/home/yahwehatwork/human-ai')
    run_comprehensive_backtest()
