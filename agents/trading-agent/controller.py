"""
Trading Controller for OpenClaw/Hermes Integration.
Provides a synchronous interface for external agents to control the TradingAgent.
"""

import json
import os
import time
import fcntl
from dataclasses import dataclass, asdict
from typing import Optional

COMMAND_FILE = "/tmp/trading-bridge/command.json"

@dataclass
class TradingCommand:
    """Structure for commands from OpenClaw/Hermes."""
    action: str  # "override", "pause", "resume", "close_position"
    symbol: Optional[str] = None
    signal: Optional[int] = None  # 1 for buy, -1 for sell
    quantity: Optional[float] = None
    price: Optional[float] = None
    timestamp: Optional[str] = None

def ensure_bridge_dir():
    """Ensure the command directory exists."""
    os.makedirs(os.path.dirname(COMMAND_FILE), exist_ok=True)

def write_command(command: TradingCommand):
    """Write a command to the bridge file (synchronous, locked)."""
    ensure_bridge_dir()
    with open(COMMAND_FILE, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(asdict(command), f)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

def read_and_clear_command() -> Optional[TradingCommand]:
    """Read and clear the command file. Returns None if no command."""
    if not os.path.exists(COMMAND_FILE):
        return None
    with open(COMMAND_FILE, 'r') as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return None
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    
    # Clear the file after reading
    open(COMMAND_FILE, 'w').close()
    return TradingCommand(**data)

class TradingController:
    """Manages synchronous command processing for the TradingAgent."""
    def __init__(self):
        self.override_command = None
        self.last_command_time = 0

    def check_for_commands(self) -> Optional[TradingCommand]:
        """Poll for new commands from the bridge."""
        cmd = read_and_clear_command()
        if cmd:
            self.last_command_time = time.time()
        return cmd

    def apply_command(self, agent, cmd: TradingCommand):
        """Apply a command to the trading agent, modifying its behavior."""
        if cmd.action == "pause":
            agent.paused = True
            agent.logger.info("Trading paused by bridge command.")
        elif cmd.action == "resume":
            agent.paused = False
            agent.logger.info("Trading resumed by bridge command.")
        elif cmd.action == "override":
            # Store an override that will be processed in the next symbol cycle
            self.override_command = cmd
            agent.logger.info(f"Override set for {cmd.symbol} with signal {cmd.signal}")
        elif cmd.action == "close_position":
            # Directly close a position without strategy logic
            if cmd.symbol and cmd.symbol in agent.risk_manager.open_positions:
                pos = agent.risk_manager.open_positions[cmd.symbol]
                close_signal = -1 if pos['side'] == 'long' else 1
                order = agent.executor.create_order(cmd.symbol, close_signal, {'Close': pos['entry_price']})
                if order:
                    order['quantity'] = pos['quantity']
                    agent.executor.execute_order(order)
                    agent.risk_manager.close_position(cmd.symbol, order['filled_price'])
                    agent.logger.info(f"Position for {cmd.symbol} closed by bridge command.")
        else:
            agent.logger.warning(f"Unknown bridge command action: {cmd.action}")