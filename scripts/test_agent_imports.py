#!/usr/bin/env python3
"""
Simple test to verify that our agent imports and basic structure works
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '/home/yahwehatwork/human-ai')

def test_imports():
    """Test that we can import our modules"""
    try:
        # Test config loader
        from core.utils.config_loader import get_agent_config, get_global_config
        print("✅ Config loader imported successfully")
        
        # Test that we can get configurations
        deepseek_config = get_agent_config('deepseek')
        print(f"✅ DeepSeek config loaded: {deepseek_config.get('identity', 'Not found')}")
        
        claude_config = get_agent_config('claude')
        print(f"✅ Claude config loaded: {claude_config.get('identity', 'Not found')}")
        
        perplexity_config = get_agent_config('perplexity')
        print(f"✅ Perplexity config loaded: {perplexity_config.get('identity', 'Not found')}")
        
        global_config = get_global_config()
        print(f"✅ Global config loaded: {len(global_config)} sections")
        
        # Test importing the agents (without initializing)
        from agents.ai_agents import DeepSeekAgent, ClaudeAgent, PerplexityAgent
        print("✅ Agent classes imported successfully")
        
        # Test importing the base agent
        from core.agents.browser_base.patchright_base_agent import PatchrightBaseAgent
        print("✅ Base agent imported successfully")
        
        print("\n🎉 All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)