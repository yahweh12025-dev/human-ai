import sys
import os
import json

# Add freqtrade to sys.path
sys.path.append('/home/yahwehatwork/human-ai/agents/freqtrade')

from freqtrade.main import main

def run_direct_backtest():
    # We use the exact same arguments that worked in the CLI before it failed,
    # but we will provide them to the main function via sys.argv.
    
    # Using the most minimal set of arguments that we know bypass the broken parser
    # Note: We omit the problematic --export flags for the first pass to ensure it runs.
    
    sys.argv = [
        'freqtrade',
        'backtesting',
        '--strategy', 'AI_Driven_BTC_Strategy',
        '--config', '/home/yahwehatwork/human-ai/apps/alpha_integration/freqtrade_configs/btc_backtest_config.json',
        '--strategy-path', '/home/yahwehatwork/human-ai/apps/alpha_integration/freqtrade_strategies/',
        '--userdir', '/home/yahwehatwork/human-ai/agents/freqtrade/user_data',
        '--timerange', '20240101-20240501',
        '--pairs', 'BTC/USDT'
    ]
    
    print("🚀 Initiating Direct Python Backtest...")
    try:
        main()
    except SystemExit as e:
        if e.code == 0:
            print("\n✅ Backtest completed successfully!")
        else:
            print(f"\n❌ Backtest failed with exit code {e.code}")

if __name__ == "__main__":
    run_direct_backtest()
