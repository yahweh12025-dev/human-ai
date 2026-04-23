# Trading Agent Skill

## Description
A specialized AI agent for financial market analysis, trading strategy development, and investment decision-making. The Trading Agent excels at technical analysis, fundamental analysis, risk management, and developing actionable trading strategies across various financial instruments.

## Capabilities
- Market analysis (technical, fundamental, sentiment, macroeconomic)
- Trading strategy development and backtesting
- Risk management and position sizing
- Multi-timeframe analysis
- Real-time market data access
- Portfolio optimization
- Trading signal generation

## Usage
The Trading Agent can be invoked for tasks such as:
- Analyzing stock charts and identifying patterns
- Developing trading strategies for specific instruments
- Conducting risk assessment for investment proposals
- Creating watchlists and screening criteria
- Backtesting trading ideas
- Providing actionable trading recommendations

## Files
- `agentmain.py` - Main trading agent implementation
- `assets/` - Configuration and prompt assets
- `mykey.py` - API key configuration (update with real keys for production)
- `references/` - Reference materials and documentation

## Dependencies
- GenericAgent infrastructure (inherited)
- LLM API access (configured via mykey.py)
- Internet connectivity for market data access

## Notes
For production use, update mykey.py with actual API keys from preferred LLM providers.
The agent is designed to work with various LLM backends through the GenericAgent framework.