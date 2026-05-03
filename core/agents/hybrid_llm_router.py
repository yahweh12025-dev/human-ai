#!/usr/bin/env python3
"""
Omni-Model LLM Router: Intelligently routes tasks between Gemini, DeepSeek, Perplexity, Claude, and OpenCode
based on task type, rate limits, and availability.
"""
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from core.agents.researcher.researcher_agent import HumanAIResearcher
from core.agents.gemini.gemini_agent import GeminiBrowserAgent
from core.agents.perplexity.perplexity_agent import PerplexityBrowserAgent
from core.agents.claude.claude_agent_improved import ClaudeAgentImproved as ClaudeBrowserAgent

CloudflareBypassManager = None

class HybridLLMRouter:
    """
    Routes LLM tasks between Gemini, DeepSeek, Perplexity, and Claude browsers.
    
    Routing Logic:
    - Gemini: Preferred for complex reasoning, vision tasks, and when under rate limits
    - OpenCode: Used for coding tasks, implementation, refactoring, and code review
    - DeepSeek: Used for high-volume tasks, when OpenCode is rate-limited, or as fallback for coding
    - Perplexity: Used for search, research, current events, and factual queries needing citations
    - Claude: Used for high-nuance reasoning, complex writing, sophisticated analysis, and premium outputs
    Rate Limit Tracking:
    - Tracks Gemini and OpenCode usage via browser interactions (not API headers)
    - Implements cooldown periods when rate limits are detected
    """

    def __init__(self, 
                 gemini_use_chrome_profile: bool = False,
                 deepseek_use_browser_profile: bool = True,
                 perplexity_use_browser_profile: bool = True,
                 claude_use_browser_profile: bool = True,
                 rate_limit_cooldown: int = 300):  # 5 minutes default cooldown
        """Initialize the omni-model router."""
        self.gemini_agent = GeminiBrowserAgent(use_chrome_profile=gemini_use_chrome_profile)
        # self.opencode_agent = OpenCodeBrowserAgent(use_swarm_profile=True)  # Removed per request
        self.opencode_agent = None
        self.deepseek_agent = HumanAIResearcher()  # Uses DeepSeekBrowserAgent internally
        self.perplexity_agent = PerplexityBrowserAgent(use_swarm_profile=perplexity_use_browser_profile)
        self.claude_agent = ClaudeBrowserAgent()
        
        self.rate_limit_cooldown = rate_limit_cooldown
        self.last_gemini_rate_limit = 0  # Timestamp of last rate limit detection
        self.gemini_request_count = 0
        self.opencode_request_count = 0
        self.deepseek_request_count = 0
        self.perplexity_request_count = 0
        self.claude_request_count = 0
        
        # Task types that favor OpenCode (coding tasks)
        self.opencode_favored_keywords = [
            'code', 'program', 'function', 'class', 'method', 
            'debug', 'fix', 'implement', 'build', 'create',
            'refactor', 'test', 'script', 'compile', 'binary',
            'algorithm', 'data structure', 'api', 'endpoint', 'database',
            'auth', 'login', 'crud', 'rest', 'graphql',
            'frontend', 'backend', '*fullstack', '*devops', '*ci/cd'
        ]
        
        # Task complexity indicators that favor Gemini
        # Task complexity indicators that favor Gemini
        self.gemini_favored_keywords = [
            'analyze', 'explain', 'describe', 'compare', 'contrast', 
            'summarize', 'vision', 'image', 'screenshot', 'visual',
            'complex', 'detailed', 'comprehensive', 'reasoning',
            'creative', 'write', 'essay', 'story', 'poem'
        ]
        
        # Task types that favor DeepSeek (volume/tasks/code)
        self.deepseek_favored_keywords = [
            'code', 'program', 'function', 'class', 'method', 
            'debug', 'fix', 'implement', 'build', 'create',
            'list', 'enumerate', 'simple', 'quick', 'fast'
        ]
        
        # Task types that favor Perplexity (search, research, current info)
        self.perplexity_favored_keywords = [
            'search', 'find', 'latest', 'current', 'news', 'research',
            'statistics', 'data', 'fact', 'cite', 'source', 'reference',
            'what is', 'who is', 'when did', 'where is', 'how many',
            'trend', 'price', 'stock', 'weather', 'score'
        ]
        
        # Task types that favor Claude (high-nuance reasoning, complex coding, writing)
        self.claude_favored_keywords = [
            'refactor', 'architecture', 'design', 'algorithm', 'optimize',
            'explain', 'tutorial', 'guide', 'documentation', 'spec',
            'logic', 'proof', 'theorem', 'philosophy', 'ethics',
            'nuanced', 'subtle', 'sophisticated', 'elegant', 'premium'
        ]
        
        print("🌀 Omni-Model LLM Router initialized")
        print(f"   Gemini cooldown: {rate_limit_cooldown}s")
        print(f"   Gemini profile: {'Main Chrome' if gemini_use_chrome_profile else 'Swarm Profile'}")

    async def _is_gemini_rate_limited(self) -> bool:
        """Check if we should avoid Gemini due to rate limits.
        Returns True if we're in cooldown period."""
        if self.last_gemini_rate_limit == 0:
            return False
        
        elapsed = time.time() - self.last_gemini_rate_limit
        return elapsed < self.rate_limit_cooldown

    def _detect_rate_limit_from_response(self, response: str) -> bool:
        """Detect if a response indicates a rate limit from Gemini.
        Looks for common rate limit messages in the response."""
        rate_limit_indicators = [
            'rate limit', 'quota exceeded', 'too many requests',
            'try again later', 'resource exhausted', 'limit exceeded'
        ]
        
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in rate_limit_indicators)

    def _assess_task_complexity(self, task: str) -> Tuple[float, float, float, float]:
        """Assess which model is best suited for a task.
        Returns (gemini_score, deepseek_score, perplexity_score, claude_score) where higher is better fit."""
        task_lower = task.lower()
        
        opencode_score = 0
        gemini_score = 0
        gemini_score = 0
        deepseek_score = 0
        perplexity_score = 0
        claude_score = 0
        
        # Check for OpenCode-favored keywords (weight coding tasks heavily) - DISABLED
        # Check for OpenCode-favored keywords (weight coding tasks heavily) - DISABLED
        for keyword in self.opencode_favored_keywords:
            pass
        # Check for Gemini-favored keywords
        for keyword in self.gemini_favored_keywords:
            if keyword in task_lower:
                gemini_score += 1
        
        # Check for DeepSeek-favored keywords (weight code higher)
        for keyword in self.deepseek_favored_keywords:
            if keyword in task_lower:
                # Give extra weight to core coding keywords
                if keyword in ['code', 'program', 'function', 'class', 'method']:
                    deepseek_score += 2
                else:
                    deepseek_score += 1
        
        # Check for Perplexity-favored keywords
        for keyword in self.perplexity_favored_keywords:
            if keyword in task_lower:
                perplexity_score += 1
        
        # Check for Claude-favored keywords
        for keyword in self.claude_favored_keywords:
            if keyword in task_lower:
                claude_score += 1
        
        # Length heuristic: longer tasks often favor Gemini/Claude (more complex)
        if len(task) > 100:
            gemini_score += 1
            claude_score += 1
        elif len(task) < 30:
            deepseek_score += 1
            perplexity_score += 1  # Short factual queries good for search
        
        # Question marks often indicate complex reasoning
        if task.count('?') > 1:
            gemini_score += 1
            claude_score += 1
        
        # Code-like patterns favor DeepSeek (strong signal)
        code_chars = ['{', '}', '()', ';', '==', '!=', '+=', '-=', '++', '--']
        code_score = sum(1 for char in code_chars if char in task)
        deepseek_score += min(code_score, 3)  # Cap at 3 to avoid overwhelming
        
        # Explicit citation/request for sources favors Perplexity
        if any(phrase in task_lower for phrase in ['source', 'cite', 'reference', 'according to']):
            perplexity_score += 2
            
        # Explicit request for nuanced/sophisticated output favors Claude
        if any(phrase in task_lower for phrase in ['nuanced', 'sophisticated', 'elegant', 'premium']):
            claude_score += 2
            
        # Explicit request for latest/current info favors Perplexity
        if any(phrase in task_lower for phrase in ['latest', 'current', 'news', 'today', 'recent']):
            perplexity_score += 2
        
        return gemini_score, deepseek_score, perplexity_score, claude_score, opencode_score

    async def _should_use_model(self, task: str) -> str:
        """Determine which model to use for a given task.
        Returns 'gemini', 'deepseek', 'perplexity', or 'claude'."""
        # If Gemini is in rate limit cooldown, avoid it
        if await self._is_gemini_rate_limited():
            # Route to best alternative
            _, deepseek, perplexity, claude = self._assess_task_complexity(task)
            scores = [('deepseek', deepseek), ('perplexity', perplexity), ('claude', claude)]
            return max(scores, key=lambda x: x[1])[0]
        
        # Assess task complexity for all models
        gemini, deepseek, perplexity, claude, opencode = self._assess_task_complexity(task)
        
        # Return the model with the highest score
        scores = [('gemini', gemini), ('deepseek', deepseek), ('perplexity', perplexity), ('claude', claude), ('opencode', opencode)]
        return max(scores, key=lambda x: x[1])[0]

    async def route_task(self, task: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Route a task to the appropriate LLM and return the result.
        
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
        selected_model = await self._should_use_model(full_task)
        
        try:
            if selected_model == "gemini":
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
                    # Fall back to best alternative
                    print("🔄 Falling back to alternative model due to rate limit")
                    return await self._route_to_best_alternative(full_task, excluded_model="gemini")
                
                return {
                    "status": "success",
                    "agent": "gemini",
                    "response": response,
                    "request_count": self.gemini_request_count,
                    "is_fallback": False
                }
            
            elif selected_model == "deepseek":
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
            
            elif selected_model == "perplexity":
                print(f"🔀 Routing to PERPLEXITY: {full_task[:50]}...")
                await self.perplexity_agent.start_browser()
                logged_in = await self.perplexity_agent.login()
                
                if not logged_in:
                    raise Exception("Failed to authenticate with Perplexity")
                
                self.perplexity_request_count += 1
                response = await self.perplexity_agent.prompt(full_task)
                
                return {
                    "status": "success",
                    "agent": "perplexity",
                    "response": response,
                    "request_count": self.perplexity_request_count,
                    "is_fallback": False
                }
            
            elif selected_model == "opencode":
                print(f"🔀 Routing to OPENSENSE: {full_task[:50]}...")
                # OpenCode is handled via browser automation
                await self.opencode_agent.start_browser()
                logged_in = await self.opencode_agent.login()
                
                if not logged_in:
                    raise Exception("Failed to authenticate with OpenCode")
                
                self.opencode_request_count += 1
                response = await self.opencode_agent.prompt(full_task)
                
                return {
                    "status": "success",
                    "agent": "opencode",
                    "response": response,
                    "request_count": self.opencode_request_count,
                    "is_fallback": False
                }
            elif selected_model == "claude":
                print(f"🔀 Routing to CLAUDE: {full_task[:50]}...")
                await self.claude_agent.start_browser()
                logged_in = await self.claude_agent.login()
                
                if not logged_in:
                    raise Exception("Failed to authenticate with Claude")
                
                self.claude_request_count += 1
                response = await self.claude_agent.prompt(full_task)
                
                return {
                    "status": "success",
                    "agent": "claude",
                    "response": response,
                    "request_count": self.claude_request_count,
                    "is_fallback": False
                }
            
        except Exception as e:
            print(f"❌ Error in {selected_model.upper()} agent: {e}")
            
            # Try fallback to another model
            try:
                print(f"🔄 Attempting fallback to alternative model...")
                return await self._route_to_best_alternative(full_task, excluded_model=selected_model)
            except Exception as fallback_error:
                return {
                    "status": "error",
                    "error": f"Both primary ({selected_model}) and fallback fallback agents failed. Primary: {str(e)}, Fallback: {str(fallback_error)}",
                    "agent": "none",
                    "response": None
                }

    async def _route_to_best_alternative(self, task: str, excluded_model: str) -> Dict[str, Any]:
        """Route to the best available model, excluding the specified one."""
        # Assess task complexity for remaining models
        gemini, deepseek, perplexity, claude = self._assess_task_complexity(task)
        
        # Set excluded model's score to -inf so it's never chosen
        scores = {
            'gemini': gemini if excluded_model != 'gemini' else float('-inf'),
            'deepseek': deepseek if excluded_model != 'deepseek' else float('-inf'),
            'perplexity': perplexity if excluded_model != 'perplexity' else float('-inf'),
            'claude': claude if excluded_model != 'claude' else float('-inf')
        }
        
        # Also exclude Gemini if it's rate limited
        if await self._is_gemini_rate_limited():
            scores['gemini'] = float('-inf')
        
        # Select the model with highest score
        selected_model = max(scores, key=scores.get)
        
        # Route to the selected model
        if selected_model == "gemini":
            print(f"🔀 Fallback routing to GEMINI: {task[:50]}...")
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
                "is_fallback": True
            }
        
        elif selected_model == "deepseek":
            print(f"🔀 Fallback routing to DEEPSEEK: {task[:50]}...")
            await self.deepseek_agent.start_browser()
            response = await self.deepseek_agent.call_llm_via_browser(task)
            self.deepseek_request_count += 1
            
            return {
                "status": "success",
                "agent": "deepseek",
                "response": response,
                "request_count": self.deepseek_request_count,
                "is_fallback": True
            }
        
        elif selected_model == "perplexity":
            print(f"🔀 Fallback routing to PERPLEXITY: {task[:50]}...")
            await self.perplexity_agent.start_browser()
            logged_in = await self.perplexity_agent.login()
            
            if not logged_in:
                raise Exception("Failed to authenticate with Perplexity")
            
            self.perplexity_request_count += 1
            response = await self.perplexity_agent.prompt(task)
            
            return {
                "status": "success",
                "agent": "perplexity",
                "response": response,
                "request_count": self.perplexity_request_count,
                "is_fallback": True
            }
        
        elif selected_model == "claude":
            print(f"🔀 Fallback routing to CLAUDE: {task[:50]}...")
            await self.claude_agent.start_browser()
            logged_in = await self.claude_agent.login()
            
            if not logged_in:
                raise Exception("Failed to authenticate with Claude")
            
            self.claude_request_count += 1
            response = await self.claude_agent.prompt(task)
            
            return {
                "status": "success",
                "agent": "claude",
                "response": response,
                "request_count": self.claude_request_count,
                "is_fallback": True
            }

        
    
    async def close(self):
        """Close all agent resources."""
        await self.gemini_agent.close()
        if hasattr(self.deepseek_agent, 'close'):
            await self.deepseek_agent.close()
        await self.perplexity_agent.close()
        await self.claude_agent.close()
        await self.opencode_agent.close()
        print("🌀 Omni-Model LLM Router closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        # Note: We can't use await here, so we'll return the current state
        # For accurate rate limit status, caller should check _is_gemini_rate_limited() directly
        return {
            "gemini_requests": self.gemini_request_count,
            "opencode_requests": self.opencode_request_count,
            "deepseek_requests": self.deepseek_request_count,
            "perplexity_requests": self.perplexity_request_count,
            "claude_requests": self.claude_request_count,
            "total_requests": self.gemini_request_count + self.deepseek_request_count + self.perplexity_request_count + self.claude_request_count,
            "last_gemini_rate_limit": self.last_gemini_rate_limit,
            "rate_limit_cooldown": self.rate_limit_cooldown
        }