#!/usr/bin/env python3
"""
Autonomous Development Loop for Trading Agent
Provides continuous testing and improvement cycles for the trading agent.
"""
import time
import sys
import os
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path('/home/yahwehatwork/human-ai')
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
log_file = project_root / "scripts" / "outcome_log.md"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def log_action(action, status="SUCCESS", details=""):
    """Log action to outcome_log.md with timestamp"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"- **{timestamp}** - {action}: {status}"
    if details:
        entry += f" - {details}"
    with open(log_file, "a") as f:
        f.write(entry + "\n")
    logger.info(f"{action}: {status} - {details}")

def _test_cycle():
    """Execute one test cycle of the trading agent"""
    try:
        log_action("Starting test cycle", "RUNNING")
        
        # Import and initialize trading agent
        # The module is located at agents/trading-agent/trading_agent.py
        # Since project_root is in sys.path, we should import via agents.trading-agent.trading_agent
        # BUT Python doesn't like hyphens in module names. 
        # Let's try importing by adding the agent directory to sys.path.
        
        agent_dir = project_root / "agents" / "trading-agent"
        if str(agent_dir) not in sys.path:
            sys.path.insert(0, str(agent_dir))
            
        from trading_agent import TradingAgent
        
        # Initialize agent with config
        # Config path is relative to the current directory or absolute
        config_path = agent_dir / "config.yaml"
        agent = TradingAgent(str(config_path))
        log_action("Trading agent initialized", "SUCCESS")
        
        # Test data fetching
        data = agent.data_fetcher.fetch_historical_data("BTC/USDT", limit=50)
        if data is not None and len(data) > 0:
            log_action("Data fetching test", "SUCCESS", f"Fetched {len(data)} records")
        else:
            log_action("Data fetching test", "FAILED", "No data returned")
            return False
        
        # Test strategy signal generation
        signal = agent.strategy.generate_signal(data)
        log_action("Strategy signal generation", "SUCCESS", f"Signal: {signal}")
        
        # Test risk management
        account_info = {'balance': 10000, 'equity': 10000}
        position_size = agent.risk_manager.calculate_position_size(
            'BTC/USDT', 0.02, account_info
        )
        log_action("Risk management test", "SUCCESS", f"Position size: {position_size}")
        
        log_action("Test cycle completed", "SUCCESS")
        return True
        
    except Exception as e:
        log_action("Test cycle", "FAILED", str(e))
        import traceback
        logger.error(traceback.format_exc())
        return False

def run_development_loop():
    """Run continuous development and testing loop"""
    cycle_count = 0
    
    # Initialize outcome log
    log_file = project_root / "scripts" / "outcome_log.md"
    with open(log_file, "w") as f:
        f.write("# Trading Agent Development Outcome Log\n\n")
        f.write("## Development Cycle Log\n\n")
    
    log_action("Development loop started", "SUCCESS")
    
    try:
        while True:
            cycle_count += 1
            log_action(f"Starting development cycle #{cycle_count}", "RUNNING")
            
            success = _test_cycle()
            
            if success:
                log_action(f"Development cycle #{cycle_count}", "SUCCESS", "All tests passed")
            else:
                log_action(f"Development cycle #{cycle_count}", "FAILED", "Tests failed")
                
            # Wait before next cycle
            time.sleep(30)
            
    except KeyboardInterrupt:
        log_action("Development loop stopped by user", "SUCCESS")
    except Exception as e:
        log_action("Development loop error", "FAILED", str(e))
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    run_development_loop()