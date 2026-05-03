#!/usr/bin/env python3
"""
Puter.js Agent: Provides access to Puter's free AI models for the swarm.
Can be used as a subagent by Hermes, OpenClaw, and other agents.
Uses a Node.js subprocess wrapper to avoid Python/JS import issues.
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import sys


class PuterAgent:
    """
    Agent for accessing Puter's free AI models and services.
    Integrates with the swarm's existing architecture via Node.js subprocess.
    """
    
    def __init__(self, 
                 agent_name: str = "puter_agent",
                 work_dir: Optional[str] = None,
                 use_free_models_only: bool = True):
        """
        Initialize the Puter agent.
        
        Args:
            agent_name: Identifier for this agent instance
            work_dir: Working directory (defaults to human-ai root)
            use_free_models_only: If True, only use models with free tiers
        """
        self.agent_name = agent_name
        self.work_dir = Path(work_dir) if work_dir else Path(__file__).parent.parent.parent.parent
        self.use_free_models_only = use_free_models_only
        self.is_initialized = False
        self.available_models = []
        self.available_providers = []
        self.process = None
        self.request_id = 0
        
    async def _start_process(self):
        """Start the Node.js wrapper subprocess."""
        if self.process is not None:
            return
            
        wrapper_path = self.work_dir / "core" / "agents" / "puter" / "puter_wrapper.js"
        if not wrapper_path.exists():
            raise FileNotFoundError(f"Puter wrapper not found at {wrapper_path}")
        
        # Start the Node.js process
        self.process = subprocess.Popen(
            ['node', str(wrapper_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            cwd=str(self.work_dir)
        )
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Check if process started successfully
        if self.process.poll() is not None:
            stderr_output = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"Puter wrapper failed to start: {stderr_output}")
    
    async def _send_request(self, action: str, params: Optional[Dict] = None) -> Dict:
        """Send a request to the Node.js wrapper and get response."""
        if not self.process or self.process.poll() is not None:
            await self._start_process()
        
        self.request_id += 1
        request = {
            "id": self.request_id,
            "action": action,
            "params": params or {}
        }
        
        # Send request
        request_line = json.dumps(request) + "\n"
        self.process.stdin.write(request_line)
        self.process.stdin.flush()
        
        # Read response
        response_line = self.process.stdout.readline()
        if not response_line:
            # Check for errors
            stderr_output = self.process.stderr.read()
            raise RuntimeError(f"No response from Puter wrapper: {stderr_output}")
        
        try:
            response = json.loads(response_line.strip())
            return response
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from Puter wrapper: {response_line}")
    
    async def initialize(self):
        """Initialize the Puter agent and discover available models."""
        if self.is_initialized:
            return
            
        print("🚀 Initializing Puter.js Agent...")
        
        try:
            # Start the subprocess
            await self._start_process()
            
            # Initialize Puter.js
            init_response = await self._send_request("initialize")
            if not init_response.get("success"):
                raise RuntimeError(f"Failed to initialize Puter.js: {init_response.get('error')}")
            
            # Get available models and providers
            await self._refresh_model_info()
            
            self.is_initialized = True
            print(f"✅ Puter.js Agent initialized")
            print(f"   Available models: {len(self.available_models)}")
            print(f"   Available providers: {len(self.available_providers)}")
            
        except Exception as e:
            print(f"❝ Failed to initialize Puter.js Agent: {e}")
            await self.close()  # Clean up on failure
            raise
    
    async def _refresh_model_info(self):
        """Refresh the list of available models and providers."""
        try:
            # Get available models
            models_response = await self._send_request("listModels")
            if models_response.get("success"):
                self.available_models = models_response.get("models", [])
            else:
                print(f"⚠️  Could not get models: {models_response.get('error')}")
                self.available_models = []
            
            # Get available providers
            providers_response = await self._send_request("listModelProviders")
            if providers_response.get("success"):
                self.available_providers = providers_response.get("providers", [])
            else:
                print(f"⚠️  Could not get providers: {providers_response.get('error')}")
                self.available_providers = []
            
            # Filter for free models if requested
            if self.use_free_models_only:
                self.available_models = [
                    model for model in self.available_models
                    if self._is_free_model(model)
                ]
                self.available_providers = [
                    provider for provider in self.available_providers
                    if self._is_free_provider(provider)
                ]
                
        except Exception as e:
            print(f"⚠️  Could not refresh model info: {e}")
    
    def _is_free_model(self, model: Dict) -> bool:
        """Check if a model has a free tier."""
        if isinstance(model, dict):
            # Check explicit free flag
            if model.get('free') is True:
                return True
                
            # Check pricing info
            pricing = model.get('pricing', {})
            if isinstance(pricing, dict):
                if pricing.get('free') is True:
                    return True
                if pricing.get('tier') == 'free':
                    return True
                    
            # Check for free indicators in model name/tags
            name = model.get('name', '').lower()
            tags = [tag.lower() for tag in model.get('tags', [])]
            free_indicators = ['free', 'trial', 'community', 'open']
            if any(indicator in name for indicator in free_indicators):
                return True
            if any(any(indicator in tag for indicator in free_indicators) for tag in tags):
                return True
                
        return False
    
    def _is_free_provider(self, provider: Dict) -> bool:
        """Check if a provider offers free access."""
        if isinstance(provider, dict):
            # Check explicit free flag
            if provider.get('free') is True:
                return True
                
            # Check pricing/tier info
            pricing = provider.get('pricing', {})
            if isinstance(pricing, dict):
                if pricing.get('free') is True:
                    return True
                if pricing.get('tier') == 'free':
                    return True
                    
            # Check name/tags
            name = provider.get('name', '').lower()
            tags = [tag.lower() for tag in provider.get('tags', [])]
            free_indicators = ['free', 'trial', 'community', 'open']
            if any(indicator in name for indicator in free_indicators):
                return True
            if any(any(indicator in tag for indicator in free_indicators) for tag in tags):
                return True
                
        return False
    
    async def chat(self, 
                   messages: List[Dict[str, str]], 
                   model: Optional[str] = None,
                   provider: Optional[str] = None,
                   temperature: float = 0.7,
                   max_tokens: Optional[int] = None,
                   **kwargs) -> Dict[str, Any]:
        """
        Send a chat request to Puter's AI models.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Specific model to use (if None, auto-selects best free model)
            provider: Specific provider to use (if None, auto-selects)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters passed to Puter
            
        Returns:
            Dict containing the response and metadata
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            # Auto-select model if not specified
            if model is None and self.available_models:
                model = self._select_best_model()
                
            # Prepare request
            request_params = {
                'messages': messages,
                'temperature': temperature,
                **kwargs
            }
            
            if model:
                request_params['model'] = model
            if provider:
                request_params['provider'] = provider
            if max_tokens is not None:
                request_params['max_tokens'] = max_tokens
                
            # Make the request
            response = await self._send_request("chat", request_params)
            
            if response.get("success"):
                chat_response = response.get("response", {})
                # Add metadata
                result = {
                    'response': chat_response,
                    'model_used': model or 'auto-selected',
                    'provider_used': provider or 'auto-selected',
                    'agent': self.agent_name,
                    'timestamp': asyncio.get_event_loop().time()
                }
                return result
            else:
                error_msg = response.get('error', 'Unknown error')
                raise Exception(f"Puter chat failed: {error_msg}")
            
        except Exception as e:
            print(f"❌ Error in Puter chat: {e}")
            # Try fallback to a different model/provider if available
            return await self._fallback_chat(messages, model, provider, temperature, max_tokens, **kwargs)
    
    async def _fallback_chat(self, 
                           messages: List[Dict[str, str]], 
                           failed_model: Optional[str],
                           failed_provider: Optional[str],
                           temperature: float,
                           max_tokens: Optional[int],
                           **kwargs) -> Dict[str, Any]:
        """Attempt fallback when primary model/provider fails."""
        print("🔄 Attempting fallback to alternative model/provider...")
        
        # Try different models from available list
        for model_info in self.available_models[:3]:  # Try first 3 free models
            model_name = model_info.get('name') if isinstance(model_info, dict) else str(model_info)
            if model_name != failed_model:
                try:
                    response = await self._send_request("chat", {
                        'messages': messages,
                        'model': model_name,
                        'temperature': temperature,
                        **({} if max_tokens is None else {'max_tokens': max_tokens}),
                        **kwargs
                    })
                    if response.get("success"):
                        chat_response = response.get("response", {})
                        return {
                            'response': chat_response,
                            'model_used': model_name,
                            'provider_used': 'fallback',
                            'agent': self.agent_name,
                            'timestamp': asyncio.get_event_loop().time(),
                            'fallback_used': True
                        }
                except Exception as e:
                    print(f"⚠️  Fallback model {model_name} also failed: {e}")
                    continue
        
        # If all fallbacks fail, raise the original error
        raise Exception(f"All Puter model attempts failed")
    
    def _select_best_model(self) -> str:
        """Select the best available free model based on heuristics."""
        if not self.available_models:
            return None
            
        # Prefer chat/text models
        text_models = []
        for model in self.available_models:
            if isinstance(model, dict):
                name = model.get('name', '').lower()
                tags = [tag.lower() for tag in model.get('tags', [])]
                # Look for text/chat indicators
                if any(indicator in name for indicator in ['chat', 'text', 'llm', 'instruct']):
                    text_models.append(model)
                elif any(indicator in tag for indicator in ['chat', 'text', 'llm', 'instruct'] for tag in tags):
                    text_models.append(model)
        
        # Use text models if available, otherwise fallback to first available
        selected_models = text_models if text_models else self.available_models
        best_model = selected_models[0] if selected_models else None
        
        return best_model.get('name') if isinstance(best_model, dict) else str(best_model)
    
    async def list_free_models(self) -> List[Dict]:
        """Get list of available free models."""
        await self._refresh_model_info()
        return self.available_models.copy()
    
    async def list_free_providers(self) -> List[Dict]:
        """Get list of available free providers."""
        await self._refresh_model_info()
        return self.available_providers.copy()
    
    async def text_to_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate image from text using Puter's txt2img."""
        if not self.is_initialized:
            await self.initialize()
            
        try:
            response = await self._send_request("txt2img", {'prompt': prompt, **kwargs})
            if response.get("success"):
                img_response = response.get("response", {})
                return {
                    'response': img_response,
                    'agent': self.agent_name,
                    'timestamp': asyncio.get_event_loop().time()
                }
            else:
                error_msg = response.get('error', 'Unknown error')
                raise Exception(f"Puter txt2img failed: {error_msg}")
        except Exception as e:
            print(f"❌ Error in Puter txt2img: {e}")
            raise
    
    async def image_to_text(self, image_data: Union[str, bytes], **kwargs) -> Dict[str, Any]:
        """Extract text from image using Puter's img2txt."""
        if not self.is_initialized:
            await self.initialize()
            
        try:
            response = await self._send_request("img2txt", {'image': image_data, **kwargs})
            if response.get("success"):
                txt_response = response.get("response", {})
                return {
                    'response': txt_response,
                    'agent': self.agent_name,
                    'timestamp': asyncio.get_event_loop().time()
                }
            else:
                error_msg = response.get('error', 'Unknown error')
                raise Exception(f"Puter img2txt failed: {error_msg}")
        except Exception as e:
            print(f"❌ Error in Puter img2txt: {e}")
            raise
    
    async def close(self):
        """Clean up resources."""
        if self.process:
            try:
                self.process.terminate()
                # Wait a bit for graceful shutdown
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            except Exception:
                pass  # Ignore cleanup errors
            finally:
                self.process = None
        self.is_initialized = False
        print(f"🧹 Puter.js Agent {self.agent_name} closed")


# Convenience functions for easy integration
async def get_puter_agent(agent_name: str = "puter_agent", 
                         work_dir: Optional[str] = None,
                         use_free_models_only: bool = True) -> PuterAgent:
    """Factory function to create and initialize a Puter agent."""
    agent = PuterAgent(agent_name=agent_name, work_dir=work_dir, use_free_models_only=use_free_models_only)
    await agent.initialize()
    return agent


# Example usage and testing
if __name__ == "__main__":
    async def test_puter_agent():
        """Test the Puter agent functionality."""
        print("🧪 Testing Puter.js Agent...")
        
        agent = await get_puter_agent("test-puter-agent")
        
        try:
            # Test model listing
            models = await agent.list_free_models()
            print(f"📋 Found {len(models)} free models")
            if models:
                print(f"   First model: {models[0].get('name', 'Unknown') if isinstance(models[0], dict) else models[0]}")
            
            # Test chat
            response = await agent.chat([
                {"role": "user", "content": "Hello! Respond with just 'Puter test successful'"}
            ])
            print(f"💬 Chat response: {response.get('response', 'No response')}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
        finally:
            await agent.close()
    
    # Run the test
    asyncio.run(test_puter_agent())