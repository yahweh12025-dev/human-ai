#!/usr/bin/env python3
"""
Simple test script for the Trading Agent
"""

import sys
import os

# Add the trading agent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_initialization():
    """Test that the trading agent can be initialized"""
    try:
        from agentmain import TradingAgent
        agent = TradingAgent()
        print("✓ Trading Agent initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize Trading Agent: {e}")
        return False

def test_llm_list():
    """Test that we can list available LLMs"""
    try:
        from agentmain import TradingAgent
        agent = TradingAgent()
        llms = agent.list_llms()
        print(f"✓ Available LLMs: {llms}")
        return True
    except Exception as e:
        print(f"✗ Failed to list LLMs: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Trading Agent...")
    print("=" * 40)
    
    tests = [
        test_initialization,
        test_llm_list,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())