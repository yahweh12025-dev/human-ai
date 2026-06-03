import asyncio
import os
import sys
from pathlib import Path

# Force system paths for the specific trading agent structure
sys.path.append('/home/yahwehatwork/human-ai')
sys.path.append('/home/yahwehatwork/human-ai/agents/trading-agent')

from core.agents.browser_base.patchright_base_agent import PatchrightBaseAgent
import trading_strategy as ts

# Define the profile directory
PROFILE_DIR = '/home/yahwehatwork/human-ai/data/browser_profiles/master_profile'
OUTPUT_DIR = Path('/home/yahwehatwork/human-ai/research/trading_strategy_review')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class TradingStrategyBrowserAgent(PatchrightBaseAgent):
    def __init__(self, identity, **kwargs):
        # Initialize BaseAgent with master_profile override
        super().__init__(
            identity=identity, 
            profile_override=PROFILE_DIR, 
            **kwargs
        )
        self.strategy = ts.TradingStrategy()

    async def prompt_agent(self, url, input_selector, send_selector, response_selector, prompt_text):
        print(f"🚀 Prompting {self.identity} at {url}...")
        try:
            await self.start_browser()
            await self.navigate_and_wait(url)
            
            # Hard-coded wait to ensure session loading
            await asyncio.sleep(5)
            
            # Ensure we are logged in
            if not await self.check_session():
                print(f"⚠️ {self.identity} session invalid.")
                return "Error: Session invalid"

            # Reset capture buffer
            if hasattr(self, '_latest_llm_response'):
                self._latest_llm_response = None
            else:
                self.captured_response = None
            
            await self.safe_fill(input_selector, prompt_text)
            await self.safe_click(send_selector)
            
            # Polling for network response instead of DOM scraping
            timeout = 60
            elapsed = 0
            while elapsed < timeout:
                await asyncio.sleep(1)
                elapsed += 1
                
                # Check both possible capture variables
                res = getattr(self, '_latest_llm_response', None) or getattr(self, 'captured_response', None)
                if res:
                    print(f"✅ Got response from {self.identity} via network interception")
                    return res
            
            # Hybrid Fallback: If network interception fails, try BS4 DOM extraction
            print("⚠️ Network interception timed out. Falling back to DOM extraction...")
            try:
                element = await self.page.locator(response_selector).last()
                text = await element.inner_text()
                return text
            except:
                return "Error: Failed to capture response via network or DOM"
                
        except Exception as e:
            print(f"❌ {self.identity} retrieval failed: {e}")
            return f"Error: {str(e)}"
        finally:
            await self.close()

async def main():
    # Define the prompts since the TradingStrategy class doesn't have them
    strategy_code = Path('/home/yahwehatwork/human-ai/agents/trading-agent/trading_strategy.py').read_text()
    
    prompts = {
        'deepseek': f"Please review this trading strategy for consistency and daily yield. Suggest specific improvements to the logic or risk management:\n\n{strategy_code}",
        'claude': f"Analyze this trading strategy. Focus on the Volatility-Indexed Exit and the symmetry-based risk scaling. How can it be more robust?\n\n{strategy_code}",
        'perplexity': f"Critique this trading strategy for potential failure points in high-volatility markets. Suggest an optimized take-profit multiplier:\n\n{strategy_code}"
    }

    configs = {
        'deepseek': {
            'url': 'https://chat.deepseek.com',
            'input': 'textarea[placeholder*="Message"], [role="textbox"], textarea',
            'send': 'button:has-text("Send"), [aria-label="Send"]',
            'resp': '.message:last-child, [data-message-role="assistant"]:last-child',
        },
        'claude': {
            'url': 'https://claude.ai/chat',
            'input': 'textarea[placeholder*="Ask Claude"], [role="textbox"]',
            'send': 'button[aria-label="Send Message"], button:has-text("Send")',
            'resp': '.font-claude-message:last-child, [data-testid="message-content"]:last-child',
        },
        'perplexity': {
            'url': 'https://www.perplexity.ai',
            'input': 'textarea[placeholder*="Ask"], [role="textbox"]',
            'send': 'button[aria-label="Submit"], button:has-text("Send")',
            'resp': '.prose:last-child, .answer-text:last-child',
        }
    }

    for name, cfg in configs.items():
        agent = TradingStrategyBrowserAgent(identity=name, headless=False)
        response = await agent.prompt_agent(
            cfg['url'], cfg['input'], cfg['send'], cfg['resp'], prompts[name]
        )
        
        out_path = OUTPUT_DIR / f'{name}_response.txt'
        out_path.write_text(response)
        print(f"💾 Saved {name} response to {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
