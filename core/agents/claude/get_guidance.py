import asyncio
import os
import sys

# Ensure the path is correct for the improved agent
sys.path.append('/home/yahwehatwork/human-ai')
from core.agents.claude.claude_agent_improved import ClaudeAgentImproved

async def run_claude_loop():
    # Initialize the improved agent
    async with ClaudeAgentImproved() as agent:
        # DETAILED CONTEXT PROMPT to maximize efficiency and avoid token waste
        # We provide everything upfront so it doesn't need to ask clarifying questions
        detailed_prompt = (
            "SYSTEM CONTEXT: You are acting as a Quantitative Trading Expert. I am using Freqtrade 2026.3 "
            "with the 'ConsensusScalperV1' strategy on Binance Swap. \n\n"
            "CURRENT BLOCKER: 'Configuration error: Ticker pricing not available for Binance'. "
            "Attempts like setting 'pricing_mode': 'candles' in config.json have failed. \n\n"
            "STRATEGY GOAL: Validate 1,500+ trades across 7 symbols (BTC, ETH, SOL, DOGE, ADA, XRP, DOT) "
            "to ensure institutional edge and avoid overfitting. \n\n"
            "MISSION: Provide the exact next step to bypass this ticker pricing error and begin backtesting. "
            "CONSTRAINTS: I am on a free tier; maximize token efficiency. Be concise, provide only "
            "actionable code/config changes. Do not repeat my context. \n\n"
            "QUESTION: What is the absolute next technical step I must take to resolve the pricing error "
            "and start the backtest? Provide the code/config change immediately."
        )
        
        print(f"🚀 Prompting Claude Improved Agent for guidance...")
        response = await agent.send_prompt(detailed_prompt)
        print(f"📥 Claude's Guidance:\n{response}")
        return response

if __name__ == "__main__":
    asyncio.run(run_claude_loop())
