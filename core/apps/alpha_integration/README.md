# Alpha Integration Bridge

This script bridges the Trading Agents, AI-Hedge-Fund, and Freqtrade repos to create an AI-driven trading system with guardrails.

## Setup

1. Clone the three repositories into this directory:
   - git clone https://github.com/tauricresearch/tradingagents.git
   - git clone https://github.com/virattt/ai-hedge-fund.git
   - git clone https://github.com/freqtrade/freqtrade.git

2. Install dependencies for each repo (follow their respective READMEs).

3. Configure Freqtrade with your exchange and API keys.

4. Adjust the paths in this script if necessary.

## Usage

Run the bridge script periodically (e.g., every hour) to:
   - Generate a trading signal from the AI repos.
   - Send the signal to Freqtrade via the /forcebuy endpoint (for high conviction signals).

## Components

- signal_factory.py: Simulates or runs the AI repos to produce a signal.json.
- bridge.py: Main script that runs the signal factory and sends to Freqtrade.
- freqtrade_strategy.py: A Freqtrade strategy that uses the signal and includes guardrails (hard stop loss, trailing profit).

## Note

The AI repos are complex and may require significant setup. This bridge includes a mock signal mode for testing.
Replace the mock signal with actual runs of the AI repos when they are properly configured.


