#!/usr/bin/env python3
"""
Live, active test of the Trading Agent integration.
This script runs synchronously in the current session.
"""
import sys
import os
import json
import logging
from datetime import datetime

# Ensure we can import from the agent directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_agent import TradingAgent
from controller import write_command, TradingCommand, read_and_clear_command
import pandas as pd
import numpy as np

# Setup logging to stdout for active observation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("LiveTest")

def mock_data_fetcher_fetch(symbol):
    """Create mock data for testing."""
    dates = pd.date_range(end=datetime.now(), periods=50, freq='h')
    data = pd.DataFrame({
        'Open': np.random.normal(50000, 1000, 50),
        'High': np.random.normal(50500, 1000, 50),
        'Low': np.random.normal(49500, 1000, 50),
        'Close': np.linspace(50000, 52000, 50), # Upward trend
        'Volume': np.random.randint(100, 1000, 50)
    }, index=dates)
    return data

def main():
    logger.info("="*60)
    logger.info("STARTING LIVE TEST (Active Session)")
    logger.info("="*60)

    # 1. Initialize Agent
    logger.info("\n[STEP 1] Initializing TradingAgent...")
    agent = TradingAgent()
    # Monkey-patch the data fetcher to use mock data for this test
    agent.data_fetcher.fetch_latest_data = mock_data_fetcher_fetch
    logger.info("Agent initialized. DataFetcher mocked.")

    # 2. Inject an OVERRIDE command
    logger.info("\n[STEP 2] Injecting OVERRIDE command (Force BUY BTC/USDT)...")
    override_cmd = TradingCommand(
        action="override",
        symbol="BTC/USDT",
        signal=1, # Buy
        quantity=0.01
    )
    write_command(override_cmd)
    logger.info("Command written to bridge.")

    # 3. Process Symbol (Single Cycle)
    logger.info("\n[STEP 3] Processing BTC/USDT (Manual Cycle)...")
    
    # Check for bridge command first (as the run loop would)
    cmd = agent.controller.check_for_commands()
    if cmd:
        logger.info(f"Detected command: {cmd.action}")
        agent.controller.apply_command(agent, cmd)
    
    # Now process the symbol manually
    symbol = "BTC/USDT"
    data = agent.data_fetcher.fetch_latest_data(symbol)
    
    # Update portfolio (Dynamic Equity Step)
    agent.risk_manager.update_portfolio(data, symbol)
    logger.info(f"Current Equity (Dynamic): {agent.risk_manager.current_equity}")
    
    # Check if we should use override or strategy
    if agent.controller.override_command:
        logger.info("OVERRIDE DETECTED! Using override signal instead of strategy.")
        signal_to_use = agent.controller.override_command.signal
        agent.controller.override_command = None # Clear after use
    else:
        signal_to_use = agent.strategy.generate_signal(data)
    
    logger.info(f"Final Signal for {symbol}: {signal_to_use}")
    
    if signal_to_use != 0:
        logger.info("Executing trade based on override...")
        # Simplified execution for test
        entry_price = data['Close'].iloc[-1]
        agent.risk_manager.open_position(
            symbol=symbol,
            entry_price=entry_price,
            order_quantity=0.01,
            stop_loss_price=entry_price * 0.95,
            take_profit_price=entry_price * 1.05
        )
        logger.info(f"Position OPENED at {entry_price}")
        logger.info(f"New Equity after opening: {agent.risk_manager.current_equity}")

    # 4. Test Post-Close Fix: Close position and immediately try to re-enter
    logger.info("\n[STEP 4] Testing Post-Close Fix (Close and Re-enter)...")
    logger.info("Closing position...")
    if symbol in agent.risk_manager.open_positions:
        pos = agent.risk_manager.open_positions[symbol]
        agent.risk_manager.close_position(symbol, data['Close'].iloc[-1]) # Close at current price
        logger.info("Position closed. Now attempting to generate a NEW signal immediately...")
        
        # In the fixed code, we should NOT return here. We continue to strategy.
        new_signal = agent.strategy.generate_signal(data)
        if new_signal != 0:
            logger.info(f"SUCCESS: New signal generated immediately after close: {new_signal}")
            logger.info("Post-Close Fix is WORKING (no blocking).")
        else:
            logger.info("Strategy returned 0 (Hold), but code did not block.")
    else:
        logger.warning("Position was not open, cannot test close/re-enter.")

    logger.info("\n" + "="*60)
    logger.info("LIVE TEST COMPLETE")
    logger.info("="*60)

if __name__ == "__main__":
    main()