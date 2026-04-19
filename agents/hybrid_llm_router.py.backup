#!/usr/bin/env python3
"""
Hybrid LLM Router: Intelligently routes tasks between Gemini and DeepSeek 
based on rate limits, task complexity, and availability.
"""
import asyncio
import os
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from agents.researcher.researcher_agent import HumanAIResearcher
from agents.gemini.gemini_agent import GeminiBrowserAgent

class HybridLLMRouter:
    """
    Routes LLM tasks between Gemini and DeepSeek browsers.
    
    Routing Logic:
    - Gemini: Preferred for complex reasoning, vision tasks, and when under rate limits
    - DeepSeek: Used for high-volume tasks, when Gemini is rate-limited, or as fallback
    
    Rate Limit Tracking:
    - Tracks Gemini usage via browser interactions (not API headers)
    - Implements cooldown periods when rate limits are detected
    """
    
    def __init__(self, 
                 gemini_use_chrome_profile: bool = False,
                 deepseek_use_browser_profile: bool = True,
                 rate_limit_cooldown: int = 300):  # 5 minutes default cooldown
        """
        Initialize the hybrid router.
        
        Args:
            gemini_use_chrome_profile: Whether to use the main Chrome profile for Gemini
            deepseek_use_browser_profile: Whether to use the swarm's browser profile for DeepSeek
            rate_limit_cooldown: Seconds to wait after detecting a rate limit before retrying Gemini
        """
        self.gemini_agent = GeminiBrowserAgent(use_chrome_profile=gemini_use_chrome_profile)
        self.deepseek_agent = HumanAIResearcher()  # Uses DeepSeekBrowserAgent internally
        
        self.rate_limit_cooldown = rate_limit_cooldown
        self.last_gemini_rate_limit = 0  # Timestamp of last rate limit detection
        self.gemini_request_count = 0
        self.deepseek_request_count = 0
        
        # Task complexity indicators that favor Gemini
        self.gemini_favored_keywords = [
            'analyze', 'explain', 'describe', 'compare', 'contrast', 
            'summarize', 'vision', 'image', 'screenshot', 'visual',
            'complex', 'detailed', 'comprehensive', 'reasoning',
            'creative', 'write', 'essay', 'story', 'poem'
        ]
        
        # Task types that favor DeepSeek (volume/tasks)
        self.deepseek_favored_keywords = [
            'code', 'program', 'function', 'class', 'method', 
            'debug', 'fix', 'implement', 'build', 'create',
            'list', 'enumerate', 'simple', 'quick', 'fast'
        ]
        
        print("🔀 Hybrid LLM Router initialized")
        print(f"   Gemini cooldown: {rate_limit_cooldown}s")
        print(f"   Gemini profile: {'Main Chrome' if gemini_use_chrome_profile else 'Swarm Profile'}")
    
    async def _is_gemini_rate_limited(self) -> bool:
        """
        Check if we should avoid Gemini due to rate limits.
        Returns True if we're in cooldown period.
        """
        if self.last_gemini_rate_limit == 0:
            return False
        
        elapsed = time.time() - self.last_gemini_rate_limit
        return elapsed < self.rate_limit_cooldown
    
    def _detect_rate_limit_from_response(self, response: str) -> bool:
        """
        Detect if a response indicates a rate limit from Gemini.
        Looks for common rate limit messages in the response.
        """
        rate_limit_indicators = [
            'rate limit', 'quota exceeded', 'too many requests',
            'try again later', 'resource exhausted', 'limit exceeded'
        ]
        
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in rate_limit_indicators)
    
    def _assess_task_complexity(self, task: str) -> Tuple[float, float]:
        """
        Assess whether a task favors Gemini or DeepSeek.
        Returns (gemini_score, deepseek_score) where higher is better fit.
        """
        task_lower = task.lower()
        
        gemini_score = 0
        deepseek_score = 0
        
        # Check for Gemini-favored keywords
        for keyword in self.gemini_favored_keywords:
            if keyword in task_lower:
                gemini_score += 1
        
        # Check for DeepSeek-favored keywords
        for keyword in self.deepseek_favored_keywords:
            if keyword in task_lower:
                deepseek_score += 1
        
        # Length heuristic: longer tasks often favor Gemini (more complex)
        if len(task) > 100:
            gemini_score += 1
        elif len(task) < 30:
            deepseek_score += 1
            
        # Question marks often indicate complex reasoning
        if task.count('?') > 1:
            gemini_score += 1
            
        # Code-like patterns favor DeepSeek
        if any(char in task for char in ['{', '}', '()', ';', '==', '!=']):
            deepseek_score += 1
            
        return gemini_score, deepseek_score
    
    
    async def _should_use_gemini(self, task: str) -> bool:
        """
        Determine whether to use Gemini or DeepSeek for a given task.
        """
        # If Gemini is in rate limit cooldown, use DeepSeek
        if await self._is_gemini_rate_limited():
            return False
            
        # Assess task complexity
        gemini_score, deepseek_score = self._assess_task_complexity(task)
        
        # If DeepSeek score is equal or higher, use DeepSeek (better for volume/efficiency)
        if deepseek_score >= gemini_score:
            return False
        
        # Only use Gemini if it is clearly better suited for the task
        return True
    async def route_task(self, task: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Route a task to the appropriate LLM and return the result.
        
        Args:
            task: The task/prompt to execute
            context: Optional context to prepend to the task
            
        Returns:
            Dict with status, response, and metadata
        """
        if context:
            full_task = context + "\n\n" + task
        else:
            full_task = task
        
        # Determine which agent to use
        use_gemini = await self._should_use_gemini(full_task)
        
        try:
            if use_gemini:
                print(f"🔀 Routing to GEMINI: {full_task[:50]}...")
                await self.gemini_agent.start_browser()
                logged_in = await self.gemini_agent.login()
                
                if not logged_in:
                    raise Exception("Failed to authenticate with Gemini")
                
                self.gemini_request_count += 1
                response = await self.gemini_agent.prompt(full_task)
                
                # Check if response indicates rate limit
                if self._detect_rate_limit_from_response(response):
                    print("⚠️  Detected rate limit in Gemini response")
                    self.last_gemini_rate_limit = time.time()
                    # Fall back to DeepSeek for this request
                    print("🔄 Falling back to DeepSeek due to rate limit")
                    return await self._route_to_deepseek(full_task, is_fallback=True)
                
                return {
                    "status": "success",
                    "agent": "gemini",
                    "response": response,
                    "request_count": self.gemini_request_count,
                    "is_fallback": False
                }
            else:
                print(f"🔀 Routing to DEEPSEEK: {full_task[:50]}...")
                await self.deepseek_agent.start_browser()
                # DeepSeek agent handles its own login/session internally via researcher_agent
                response = await self.deepseek_agent.call_llm_via_browser(full_task)
                self.deepseek_request_count += 1
                
                return {
                    "status": "success",
                    "agent": "deepseek",
                    "response": response,
                    "request_count": self.deepseek_request_count,
                    "is_fallback": False
                }
                
        except Exception as e:
            print(f"❌ Error in { 'Gemini' if use_gemini else 'DeepSeek' } agent: {e}")
            
            # Try fallback to the other agent
            try:
                if use_gemini:
                    print("🔄 Attempting fallback to DeepSeek...")
                    return await self._route_to_deepseek(full_task, is_fallback=True)
                else:
                    print("🔄 Attempting fallback to Gemini...")
                    return await self._route_to_gemini(full_task, is_fallback=True)
            except Exception as fallback_error:
                return {
                    "status": "error",
                    "error": f"Both agents failed. Primary: {str(e)}, Fallback: {str(fallback_error)}",
                    "agent": "none",
                    "response": None
                }
    
    async def _route_to_gemini(self, task: str, is_fallback: bool = False) -> Dict[str, Any]:
        """Helper to route specifically to Gemini."""
        await self.gemini_agent.start_browser()
        logged_in = await self.gemini_agent.login()
        
        if not logged_in:
            raise Exception("Failed to authenticate with Gemini")
            
        self.gemini_request_count += 1
        response = await self.gemini_agent.prompt(task)
        
        return {
            "status": "success",
            "agent": "gemini",
            "response": response,
            "request_count": self.gemini_request_count,
            "is_fallback": is_fallback
        }
    
    async def _route_to_deepseek(self, task: str, is_fallback: bool = False) -> Dict[str, Any]:
        """Helper to route specifically to DeepSeek."""
        await self.deepseek_agent.start_browser()
        response = await self.deepseek_agent.call_llm_via_browser(task)
        self.deepseek_request_count += 1
        
        return {
            "status": "success",
            "agent": "deepseek",
            "response": response,
            "request_count": self.deepseek_request_count,
            "is_fallback": is_fallback
        }
    
    async def close(self):
        """Close all agent resources."""
        await self.gemini_agent.close()
        if hasattr(self.deepseek_agent, 'close'):
            await self.deepseek_agent.close()
        print("🔀 Hybrid LLM Router closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        # Note: We can't use await here, so we'll return the current state
        # For accurate rate limit status, caller should check _is_gemini_rate_limited() directly
        return {
            "gemini_requests": self.gemini_request_count,
            "deepseek_requests": self.deepseek_request_count,
            "total_requests": self.gemini_request_count + self.deepseek_request_count,
            "last_gemini_rate_limit": self.last_gemini_rate_limit,
            "rate_limit_cooldown": self.rate_limit_cooldown
        }
