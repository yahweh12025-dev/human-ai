# Trading Agent

A modular trading agent designed for multiple markets (stocks, forex, crypto, commodities), trading styles (day, swing, position), and strategies (technical, ML, sentiment, arbitrage). Built as part of the Human-AI Agent Swarm.

## Directory Structure

- `data/` - Data fetching, storage, and preprocessing modules
- `strategies/` - Trading signal generation modules
- `execution/` - Order execution and broker interfaces
- `risk/` - Risk management and position sizing logic
- `utils/` - Shared utilities, logging, configuration
- `logs/` - Execution logs and audit trails

## Development Roadmap

1. **Core Loop & Configuration** - Main agent loop, config loading, logging setup
2. **Data Module** - Connect to market data APIs (Binance, Yahoo Finance, Alpaca, etc.)
3. **Strategy Module** - Implement technical indicators (SMA, EMA, RSI, MACD) and signal generation
4. **Execution Module** - Paper trading simulator, later integrate with broker APIs
5. **Risk Module** - Position sizing, stop-loss/take-profit, portfolio limits
6. **Integration & Testing** - End-to-end backtesting, live paper trading, performance metrics
7. **Deployment** - Docker container, scheduled runs, Telegram notifications

## Getting Started

See individual module READMEs for detailed instructions.

## Contributing

Follow the project's contribution guidelines in the root README.
