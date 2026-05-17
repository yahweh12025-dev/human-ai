#!/usr/bin/env python3
"""
FreqTrade Binance Testnet Trading Agent
Handles live testnet trading workflow with OpenClaw integration
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests
import ccxt

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

class FreqTradeTestnetAgent:
    """
    Autonomous FreqTrade agent for Binance Futures testnet trading.
    Integrates with OpenClaw gateway for swarm coordination.
    """

    def __init__(self, config_path: str = None):
        """Initialize the FreqTrade testnet agent"""
        self.config_path = config_path or "projects/freqtrade/freqtrade/user_data/config_testnet.json"
        self.config = self._load_config()
        self.exchange = self._initialize_exchange()
        self.api_base = f"http://{self.config['api_server']['listen_ip_address']}:{self.config['api_server']['listen_port']}"
        self.running = False
        self.trade_log = []

    def _load_config(self) -> Dict:
        """Load FreqTrade configuration"""
        config_full_path = Path.home() / "human-ai" / self.config_path
        with open(config_full_path, 'r') as f:
            return json.load(f)

    def _initialize_exchange(self) -> ccxt.binance:
        """Initialize CCXT exchange for Binance Demo Futures"""
        exchange = ccxt.binance({
            'apiKey': os.getenv('BINANCE_TESTNET_API_KEY'),
            'secret': os.getenv('BINANCE_TESTNET_SECRET_KEY'),
            'options': {'defaultType': 'future'},
        })
        # Override to Binance Demo Futures endpoints
        exchange.urls['api']['fapiPublic'] = 'https://demo-fapi.binance.com/fapi/v1'
        exchange.urls['api']['fapiPrivate'] = 'https://demo-fapi.binance.com/fapi/v1'
        exchange.urls['api']['fapiPublicV2'] = 'https://demo-fapi.binance.com/fapi/v2'
        exchange.urls['api']['fapiPrivateV2'] = 'https://demo-fapi.binance.com/fapi/v2'
        exchange.has['fetchCurrencies'] = False
        return exchange

    def verify_connection(self) -> Dict:
        """Verify Binance testnet connection and fetch account status"""
        try:
            balance = self.exchange.fetch_balance()
            ticker = self.exchange.fetch_ticker('BTC/USDT')

            return {
                'status': 'connected',
                'timestamp': datetime.now().isoformat(),
                'balance_usdt': balance.get('USDT', {}).get('free', 0),
                'btc_price': ticker['last'],
                'exchange': 'Binance Futures Testnet'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_open_positions(self) -> List[Dict]:
        """Get currently open positions"""
        try:
            positions = self.exchange.fetch_positions()
            open_positions = [
                {
                    'symbol': p['symbol'],
                    'side': p['side'],
                    'contracts': p['contracts'],
                    'unrealized_pnl': p['unrealizedPnl'],
                    'entry_price': p['entryPrice'],
                    'leverage': p['leverage']
                }
                for p in positions if p['contracts'] > 0
            ]
            return open_positions
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []

    def get_market_data(self, symbol: str = 'BTC/USDT', timeframe: str = '5m', limit: int = 100) -> Dict:
        """Fetch OHLCV market data"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'candles': len(ohlcv),
                'latest_close': ohlcv[-1][4],
                'latest_volume': ohlcv[-1][5],
                'data': ohlcv
            }
        except Exception as e:
            return {'error': str(e)}

    def execute_test_trade(self, symbol: str = 'BTC/USDT', side: str = 'buy',
                          amount: float = 0.001) -> Dict:
        """
        Execute a test trade on Binance testnet

        Args:
            symbol: Trading pair (default: BTC/USDT)
            side: 'buy' or 'sell'
            amount: Contract amount (default: 0.001 BTC)
        """
        try:
            # Get current market price
            ticker = self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']

            # Calculate position value
            position_value = current_price * amount

            # Place market order
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount
            )

            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'order_id': order['id'],
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'price': current_price,
                'position_value_usd': position_value,
                'status': order['status'],
                'filled': order.get('filled', 0)
            }

            self.trade_log.append(trade_record)
            self._log_trade(trade_record)

            return {
                'success': True,
                'trade': trade_record,
                'message': f"Test trade executed: {side.upper()} {amount} {symbol} @ ${current_price}"
            }

        except Exception as e:
            error_record = {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'symbol': symbol,
                'side': side,
                'amount': amount
            }
            self._log_trade(error_record)

            return {
                'success': False,
                'error': str(e),
                'details': error_record
            }

    def close_position(self, symbol: str = 'BTC/USDT') -> Dict:
        """Close an open position"""
        try:
            positions = self.get_open_positions()
            target_position = next((p for p in positions if p['symbol'] == symbol), None)

            if not target_position:
                return {'success': False, 'message': f'No open position for {symbol}'}

            # Close position (opposite side of entry)
            close_side = 'sell' if target_position['side'] == 'long' else 'buy'
            amount = abs(target_position['contracts'])

            return self.execute_test_trade(symbol, close_side, amount)

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _log_trade(self, trade_data: Dict):
        """Log trade to file for swarm access"""
        log_dir = Path.home() / "human-ai" / "data" / "data" / "logs" / "trading"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"freqtrade_testnet_{datetime.now().strftime('%Y%m%d')}.jsonl"

        with open(log_file, 'a') as f:
            f.write(json.dumps(trade_data) + '\n')

    def get_performance_summary(self) -> Dict:
        """Generate performance summary from trade log"""
        if not self.trade_log:
            return {'message': 'No trades executed yet'}

        successful_trades = [t for t in self.trade_log if 'error' not in t]
        failed_trades = [t for t in self.trade_log if 'error' in t]

        return {
            'total_trades': len(self.trade_log),
            'successful': len(successful_trades),
            'failed': len(failed_trades),
            'success_rate': len(successful_trades) / len(self.trade_log) * 100,
            'latest_trade': self.trade_log[-1] if self.trade_log else None
        }

    def save_state(self):
        """Save agent state to unified tasks"""
        state = {
            'agent': 'FreqTradeTestnetAgent',
            'timestamp': datetime.now().isoformat(),
            'status': 'running' if self.running else 'stopped',
            'connection': self.verify_connection(),
            'performance': self.get_performance_summary(),
            'open_positions': self.get_open_positions()
        }

        state_file = Path.home() / "human-ai" / "state" / "freqtrade_testnet_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)

        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

        return state

    def openclaw_notify(self, message: str, data: Dict = None):
        """Send notification to OpenClaw gateway"""
        try:
            notification = {
                'source': 'FreqTradeTestnetAgent',
                'timestamp': datetime.now().isoformat(),
                'message': message,
                'data': data or {}
            }

            # Log to OpenClaw queue
            queue_file = Path.home() / "human-ai" / "swarm" / "openclaw_notifications.jsonl"
            queue_file.parent.mkdir(parents=True, exist_ok=True)

            with open(queue_file, 'a') as f:
                f.write(json.dumps(notification) + '\n')

            return True
        except Exception as e:
            print(f"OpenClaw notify error: {e}")
            return False


def main():
    """Main execution function for manual testing"""
    print("🤖 FreqTrade Binance Testnet Agent - Initializing...")

    agent = FreqTradeTestnetAgent()

    # Test 1: Verify connection
    print("\n📡 Testing Binance testnet connection...")
    connection = agent.verify_connection()
    print(json.dumps(connection, indent=2))

    if connection['status'] != 'connected':
        print("❌ Connection failed. Check API credentials.")
        return

    print(f"\n✅ Connected to {connection['exchange']}")
    print(f"   USDT Balance: ${connection['balance_usdt']:.2f}")
    print(f"   BTC Price: ${connection['btc_price']:.2f}")

    # Test 2: Get market data
    print("\n📊 Fetching market data...")
    market_data = agent.get_market_data('BTC/USDT', '5m', 50)
    if 'error' not in market_data:
        print(f"   Latest BTC close: ${market_data['latest_close']:.2f}")
        print(f"   Candles retrieved: {market_data['candles']}")

    # Test 3: Check open positions
    print("\n📈 Checking open positions...")
    positions = agent.get_open_positions()
    if positions:
        print(f"   Open positions: {len(positions)}")
        for pos in positions:
            print(f"   - {pos['symbol']} {pos['side']}: {pos['contracts']} contracts")
    else:
        print("   No open positions")

    # Test 4: Save state
    print("\n💾 Saving agent state...")
    state = agent.save_state()
    print(f"   State saved: {state['status']}")

    # Test 5: OpenClaw notification
    print("\n📨 Testing OpenClaw notification...")
    agent.openclaw_notify("FreqTrade testnet agent initialized and verified", {
        'balance': connection['balance_usdt'],
        'btc_price': connection['btc_price']
    })
    print("   Notification sent to OpenClaw queue")

    print("\n✅ All systems operational. Agent ready for trading.")
    print("\n⚠️  Note: Execute test trades manually via agent methods")
    print("   Example: agent.execute_test_trade('BTC/USDT', 'buy', 0.001)")

    return agent


if __name__ == "__main__":
    agent = main()
