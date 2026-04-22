
import sys
sys.path.insert(0, '.')
try:
    from trading_agent import TradingAgent
    print('SUCCESS: TradingAgent imported')
    agent = TradingAgent()
    print('SUCCESS: Agent created')
    print(f'Data fetcher: {agent.data_fetcher}')
    print(f'Strategy: {agent.strategy}')
    print(f'Executor: {agent.executor}')
    print(f'Risk manager: {agent.risk_manager}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
