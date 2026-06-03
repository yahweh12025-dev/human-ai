
import os
import sys
import logging
import alpaca_trade_api as tradeapi
from dotenv import load_dotenv

# Ensure the venv can be imported
sys.path.insert(0, '/home/yahwehatwork/human-ai/agents/trading-agent')

# Load env vars
load_dotenv('/home/yahwehatwork/human-ai/human-ai.env')

# Setup logging - prints to console for visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- START IMPORTS ---
from strategies.grid import GridStrategy
from risk.manager import RiskManager
logger = logging.getLogger(__name__)

# --- SIMPLE EVENT LOOP ---
while True:
    try:
        logger.info("Starting basic loop iteration...")
        
        # 1. Get market data (placeholder)
        logger.info("Fetching mock price data...")
        current_price = 77800.0  # dummy BTC price
        
        # 2. Initialize grid (minimal)
        logger.info("Initializing lambda-style grid...")
        grid_levels = [current_price * (1 - 0.02), current_price, current_price * (1 + 0.02)]
        logger.info(f"Grid levels: {sorted(grid_levels)}")
        
        # 3. Generate signal (automatically triggered on init)
        #     Since there's no real data feed, we simulate a signal
        import random
        signal = random.choice([1, -1])  # +/-1 with 50% chance
        logger.info(f"Generated signal: {signal}")
        
        # 3. Dummy order execution
        target_price = current_price * random.uniform(0.99, 1.01)
        order = {
            'symbol': 'BTC/USDT',
            'side': 'buy' if signal == 1 else 'sell',
            'price': target_price,
            'quantity': 1,
            'status': 'test_or_fill'
        }
        logger.info(f"Dummy order placed: {order}")
        
        logger.info("--- Iteration complete - sleeping 1 min ---")
        import time; time.sleep(5)  # add delay so we can see it
        
    except KeyboardInterrupt:
        logger.info("Shutting down due to KeyboardInterrupt")
        break
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        import traceback; traceback.print_exc()
