---
name: External APIs
description: Alpaca, CCXT, DeepSeek, OpenRouter, Telethon, Camoufox
type: reference
---

**Trading & Market Data:**
- **Alpaca API**: Professional-grade market data, backtesting, paper/live trading execution
- **CCXT**: Cryptocurrency exchange connectivity (Binance, Kraken, OKX, Bybit, Bitget, HTX, KuCoin)
- **TA-Lib**: Technical analysis indicators

**AI & Research:**
- **DeepSeek**: Web research via stealth browser agent (uses Camoufox)
- **OpenRouter**: LLM routing and model selection for agent reasoning
- **FreqAI**: Built-in ML capabilities for price prediction and classification

**Communication:**
- **Telethon**: Telegram integration for swarm commands and notifications

**Automation:**
- **Camoufox**: Anti-detection browser automation for stealth operations
- **Playwright**: Additional browser automation capabilities

**Configuration:** API keys and secrets stored in `.env` (never committed)

Example `.env` entries:
```
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
DEEPSEEK_API_KEY=your_key
OPENROUTER_API_KEY=your_key
TELEGRAM_API_ID=12345
TELEGRAM_API_HASH=your_hash
```

All integrations are abstracted through the `core/integrations/` modules.
