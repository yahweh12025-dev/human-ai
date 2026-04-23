#!/usr/bin/env python3
"""
Trading Research Agent - Uses Patchright browsers to gather market intelligence
for the trading agent. Demonstrates the multi-agent browser approach.
"""

import asyncio
import os
from datetime import datetime
from core.agents.browser_base.google_agent import GoogleAgent
from core.agents.browser_base.deepseek_browser_agent import DeepSeekBrowserAgent


class TradingResearchAgent:
    """
    Research agent that gathers market intelligence using stealth browsers.
    Uses separate persistent profiles for different services as recommended.
    """
    
    def __init__(self):
        self.google_agent = GoogleAgent(headless=True)  # Set False for manual seeding
        self.deepseek_agent = DeepSeekBrowserAgent()
        self.research_dir = os.path.join(os.getenv('WORK_DIR', '/home/ubuntu/human-ai'), 'research')
        os.makedirs(self.research_dir, exist_ok=True)
    
    async def initialize(self):
        """Initialize all browser agents"""
        print("🚀 Initializing Trading Research Agent...")
        
        # Start browsers
        await self.google_agent.start_browser()
        await self.deepseek_agent.start_browser()
        
        # Check sessions (will prompt for manual seeding if needed)
        google_ok = await self.google_agent.ensure_session()
        deepseek_ok = await self.deepseek_agent.ensure_session()
        
        if not google_ok:
            print("⚠️ Google session needs manual seeding. Run with headless=False once.")
        
        if not deepseek_ok:
            print("⚠️ DeepSeek session needs manual seeding. Run with headless=False once.")
        
        return google_ok and deepseek_ok
    
    async def gather_market_sentiment(self) -> dict:
        """
        Gather market sentiment from multiple sources using different AI agents.
        Returns a dictionary with sentiment analysis from each source.
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'sources': {}
        }
        
        # 1. Get Google Trends / News sentiment via Gemini
        try:
            if await self.google_agent.ensure_session():
                gemini_prompt = """
                Analyze current market sentiment for cryptocurrency futures (BTC, ETH, TRX, XRP).
                Look at recent news, social media trends, and trader sentiment.
                Provide a concise summary with:
                - Overall sentiment (bullish/bearish/neutral)
                - Key drivers
                - Risk factors
                - Time horizon for outlook
                Keep it under 200 words.
                """
                
                gemini_response = await self.google_agent.prompt_gemini(gemini_prompt)
                results['sources']['gemini'] = {
                    'response': gemini_response,
                    'timestamp': datetime.now().isoformat()
                }
                print("✅ Gemini market sentiment gathered")
            else:
                results['sources']['gemini'] = {
                    'error': 'Session invalid - manual seeding required',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            results['sources']['gemini'] = {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        # 2. Get DeepSeek analysis for technical outlook
        try:
            if await self.deepseek_agent.ensure_session():
                deepseek_prompt = """
                Provide a technical analysis outlook for major cryptocurrency futures:
                BTC/USDT, ETH/USDT, TRX/USDT, XRP/USDT (4H and 1D timeframes).
                
                For each symbol, give:
                - Current trend direction
                - Key support/resistance levels
                - Recommended trading range (if any)
                - Risk/reward setup ideas
                
                Format as bullet points for easy parsing.
                Keep analysis actionable and concise.
                """
                
                deepseek_response = await self.deepseek_agent.prompt(deepseek_prompt)
                results['sources']['deepseek'] = {
                    'response': deepseek_response,
                    'timestamp': datetime.now().isoformat()
                }
                print("✅ DeepSeek technical analysis gathered")
            else:
                results['sources']['deepseek'] = {
                    'error': 'Session invalid - manual seeding required',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            results['sources']['deepseek'] = {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        # 3. Save results to file
        results_file = os.path.join(
            self.research_dir, 
            f"market_sentiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        import json
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"💾 Research saved to: {results_file}")
        return results
    
    async def close(self):
        """Close all browser agents"""
        await self.google_agent.close()
        await self.deepseek_agent.close()
        print("🌐 Trading Research Agent closed")


# Example usage
async def main():
    """Example of how to use the Trading Research Agent"""
    researcher = TradingResearchAgent()
    
    try:
        # Initialize browsers (will prompt for manual seeding if needed)
        ready = await researcher.initialize()
        
        if not ready:
            print("""
            ⚠️  Some sessions need manual seeding.
            
            To seed sessions:
            1. Set BROWSER_HEADLESS=false in your .env or export it
            2. Run this script once - it will open browsers
            3. Manually log into:
               - https://myaccount.google.com/ (for Gemini access)
               - https://chat.deepseek.com
            4. Solve any CAPTCHAs if presented
            5. Close the browsers - sessions will be saved
            6. Set BROWSER_HEADLESS=true and resume normal operation
            
            This one-time seeding prevents:
            - Repeated 2FA challenges from datacenter IPs
            - Account flags from automated login attempts
            - Session trust issues
            """)
            return
        
        # Gather market intelligence
        print("\n📊 Gathering market intelligence...")
        results = await researcher.gather_market_sentiment()
        
        # Display results
        print("\n" + "="*60)
        print("TRADING RESEARCH AGENT - MARKET INTELLIGENCE")
        print("="*60)
        
        for source, data in results['sources'].items():
            print(f"\n🔹 {source.upper()}:")
            if 'error' in data:
                print(f"   ❌ Error: {data['error']}")
            else:
                print(f"   {data['response'][:200]}...")
        
        print("\n" + "="*60)
        
    finally:
        await researcher.close()


if __name__ == "__main__":
    asyncio.run(main())