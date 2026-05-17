import sys
import os

# Add freqtrade to sys.path
sys.path.append('/home/yahwehatwork/human-ai/agents/freqtrade')

from freqtrade.main import main

def run_backtest():
    # Construct the sys.argv manually to mimic the command line
    sys.argv = [
        'freqtrade', 
        'backtesting',
        '--strategy', 'AI_Driven_BTC_Strategy',
        '--config', '/home/yahwehatwork/human-ai/apps/alpha_integration/freqtrade_configs/btc_backtest_config.json',
        '--strategy-path', '/home/yahwehatwork/human-ai/apps/alpha_integration/freqtrade_strategies/',
        '--userdir', '/home/yahwehatwork/human-ai/agents/freqtrade/user_data',
        '--timerange', '20240101-20240501',
        '--pairs', 'BTC/USDT',
        '--export', 'trades',
        '--export-directory', '/home/yahwehatwork/human-ai/validation/freqtrade_backtests/'
    ]
    
    try:
        main()
    except SystemExit as e:
        print(f"Process exited with code {e.code}")

if __name__ == "__main__":
    run_backtest()
