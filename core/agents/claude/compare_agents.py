import asyncio
from core.agents.claude.claude_agent import ClaudeAgent
from core.agents.claude.claude_agent_improved import ClaudeAgentImproved

async def test_agent(agent_class, name, prompt):
    print(f"\n--- Testing {name} ---")
    try:
        async with agent_class() as agent:
            if await agent.start():
                print(f"✅ {name} started.")
                print(f"📤 Sending prompt...")
                response = await agent.send_prompt(prompt)
                print(f"📥 {name} Response:\n{response[:500]}...") # Show first 500 chars
                return response
            else:
                print(f"❌ {name} failed to start.")
                return None
    except Exception as e:
        print(f"❌ {name} error: {e}")
        return None

async def main():
    prompt = (
        "I am using Freqtrade 2026.3 with the ConsensusScalperV1 strategy on Binance Swap. "
        "I am getting the error: 'Configuration error: Ticker pricing not available for Binance'. "
        "I have already tried setting 'pricing_mode': 'candles' in config.json. "
        "How do I fix this at a code level or configuration level to ensure backtesting works?"
    )

    res_original = await test_agent(ClaudeAgent, "Original Claude Agent", prompt)
    
    # Small delay between agents to clear window focus
    await asyncio.sleep(5)
    
    res_improved = await test_agent(ClaudeAgentImproved, "Improved Claude Agent", prompt)

    print("\n" + "="*50)
    print("COMPARISON RESULTS")
    print("="*50)
    print(f"Original Agent Extraction: {'SUCCESS' if res_original and len(res_original) > 50 else 'FAILED'}")
    print(f"Improved Agent Extraction: {'SUCCESS' if res_improved and len(res_improved) > 50 else 'FAILED'}")
    
    if res_original and res_improved:
        diff = abs(len(res_original) - len(res_improved))
        print(f"Length Difference: {diff} characters")
    
    if not res_original and res_improved:
        print("RESULT: Improved Agent is significantly more robust.")
    elif res_original and not res_improved:
        print("RESULT: Original Agent performed better (unexpected).")
    elif res_original and res_improved:
        print("RESULT: Both agents successfully extracted the response.")
    else:
        print("RESULT: Both agents failed. Check if Claude Desktop is open.")

if __name__ == "__main__":
    asyncio.run(main())
