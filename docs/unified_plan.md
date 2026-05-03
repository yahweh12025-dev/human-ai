# 🗺️ Unified Plan: The "GUI-First" Evolution

## 🎯 High-Level Objective
Transition the `human-ai` swarm from an API-dependent architecture to a **GUI-First Architecture**. This maximizes stealth, eliminates API costs/restrictions, and mimics human interaction for ultimate reliability.

## 🛠️ Technical Directives

### 1. The API Purge (Immediate)
- **Action**: `opencode` to scrub the codebase for `requests`, `httpx`, `ccccxt`, `urllib`.
- **Goal**: Ensure zero direct external network calls from the agent layer.
- **Exception**: Only Hermes, openclaw, and opencode maintain API access for core orchestration.

### 2. AntFarm 2.0 (Factory Optimization)
- **Static Analysis**: Introduce a "Zero-Trust" layer. No code reaches the LLM Reviewer unless it passes `pytest` and `ruff`.
- **Visual Loop**: The Navigator must now operate on a "Screenshot $\rightarrow$ OCR $\rightarrow$ Action" cycle.

### 3. GUI-First Trading & Intel
- **Data Extraction**: Transition the Trading Engine's price feeds from APIs to **DOM Parsing** (via Playwright) and **OCR** (via OpenCV) from the la-layered source map.
- **Intelligence Sources**:
    - **Tier 1 (Core)**: Binance, TradingView, CoinGecko, Binance Academy.
    - **Tier 2 (Order Flow)**: CoinGlass, Hyblock, Coinalyze, CryptoQuant.
    - **Tier 3 (Sentiment)**: CoinDesk, Coinbase, Bybit, Tree News, The Block.
    - **Tier 4 (Predictions)**: Coin Edition, BitcoinEthereumNews, CoinDCX, Changelly, Digrin.
    - **Tier 5 (Macro)**: DefiLlama, Glassnode.
- **Optimization**: Implement a Walk-Forward Optimization module for SMA/RSI tuning.

### 4. The E2E Proof (The Dummy Task)
- **Scenario**: Extract BTC funding rate from a web UI $\rightarrow$ Process via opencode $\rightarrow$ Store in Mission Control.
- **Constraints**: Browser-only $\rightarrow$ Docker isolated $\rightarrow$ AntFarm verified.

## 📅 Execution Timeline
- **Step 1**: Code Scrub & Docker Hardening.
- **Step 2**: Static Analysis & Visual Loop integration.
- **Step 3**: Trading Engine GUI transition.
- **Step 4**: Final E2E Validation.
