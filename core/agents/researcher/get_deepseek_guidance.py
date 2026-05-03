import asyncio
import os
import sys

# Add the project root to path
sys.path.append('/home/yahwehatwork/human-ai')
from core.agents.researcher.deepseek_browser_agent_enhanced import DeepSeekBrowserAgentEnhanced

async def run_deepseek_loop():
    # Initialize the DeepSeek agent
    # We set alert_on_captcha=True because this is a headless browser agent
    agent = DeepSeekBrowserAgentEnhanced(alert_on_captcha=True)
    
    try:
        # 1. Initialize browser and check login
        if not await agent.login():
            print("❌ DeepSeek Login failed. Manual intervention may be required for CAPTCHA.")
            return None
        
        # 2. Detailed prompt to maximize token/response efficiency
        detailed_prompt = (
            "SYSTEM CONTEXT: You are a Quantitative Trading Expert and Freqtrade specialist. "
            "I am using Freqtrade 2026.3 with the 'ConsensusScalperV1' strategy on Binance Swap. \n\n"
            "CURRENT BLOCKER: 'Configuration error: Ticker pricing not available for Binance'. "
            "I have already attempted 'pricing_mode': 'candles' in config.json, which failed. \n\n"
            "STRATEGY GOAL: Validate 1,500+ trades across 7 symbols (BTC, ETH, SOL, DOGE, ADA, XRP, DOT) "
            "to ensure institutional edge and avoid overfitting. \n\n"
            "MISSION: Provide a surgical, technical fix to bypass this ticker pricing error. "
            "If a config change is insufficient, suggest a specific code-level monkey-patch "
            "or a custom_ccxt_params configuration that forces the backtester to use candles. \n\n"
            "CONSTRAINTS: Be extremely concise and actionable. Provide only the code/config changes. "
            "Do not repeat my context. \n\n"
            "QUESTION: What is the absolute next technical step I must take to resolve the pricing error "
            "and start the backtest? Provide the exact code block."
        )
        
        print(f"🚀 Prompting DeepSeek Agent for the technical fix...")
        response = await agent.prompt(detailed_prompt)
        print(f"📥 DeepSeek's Guidance:\n{response}")
        return response

    except Exception as e:
        print(f"❌ Error during DeepSeek execution: {e}")
        return None
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(run_deepseek_loop())
