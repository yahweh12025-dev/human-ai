#!/usr/bin/env python3
"""
Robust Claude access that combines hybrid router (primary) with Botasaurus fallback.
This is the main orchestration script for the claude-robust-review skill.
"""

import asyncio
import json
import sys
import traceback
from typing import Dict, Any

# Add the human-ai directory to path for imports
sys.path.insert(0, '/home/yahwehatwork/human-ai')

def log_message(msg: str):
    """Simple logging function"""
    print(f"[Claude-Robust] {msg}")

async def try_hybrid_router_method(prompt: str, context: str = "") -> Dict[str, Any]:
    """
    Try the primary method: using the hybrid LLM router to access Claude.
    """
    log_message("🔄 Attempting primary method: Hybrid LLM Router -> ClaudeBrowserAgent")
    
    try:
        # Import the hybrid router
        from core.agents.hybrid_llm_router import HybridLLMRouter
        
        # Initialize the router
        router = HybridLLMRouter()
        
        # Enhance the prompt with context if provided
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n---\n\nTask: {prompt}"
        
        # Route the task - this should choose Claude for code review/tasks
        log_message("   Routing task to appropriate LLM...")
        result = await router.route_task(full_prompt)
        
        # Close the router
        await router.close()
        
        # Check if we got a successful response from Claude
        if result.get('status') == 'success':
            agent_used = result.get('agent', 'unknown')
            log_message(f"   ✅ Success via {agent_used}")
            return {
                "status": "success",
                "response": result.get('response', ''),
                "agent_used": agent_used,
                "method": "hybrid_router_claude",
                "raw_result": result
            }
        else:
            error_msg = result.get('error', 'Unknown error')
            log_message(f"   ❌ Hybrid router failed: {error_msg}")
            
            # Check if this looks like a Cloudflare issue
            error_lower = error_msg.lower()
            cloudflare_indicators = [
                'cloudflare', 'timeout', 'challenge', 'just a moment',
                'waiting for selector', 'timeout exceeded', 'not logged in',
                'session invalid', 'captcha'
            ]
            
            is_cloudflare_related = any(indicator in error_lower for indicator in cloudflare_indicators)
            
            return {
                "status": "error",
                "error": error_msg,
                "agent_used": result.get('agent', 'unknown'),
                "method": "hybrid_router_claude",
                "is_cloudflare_related": is_cloudflare_related,
                "raw_result": result
            }
            
    except Exception as e:
        error_msg = f"Hybrid router exception: {str(e)}"
        log_message(f"   ❌ {error_msg}")
        log_message(f"   Traceback: {traceback.format_exc()}")
        
        return {
            "status": "error",
            "error": error_msg,
            "method": "hybrid_router_claude",
            "is_cloudflare_related": True,  # Assume Cloudflare-related on exception
            "traceback": traceback.format_exc()
        }

def try_botasaurus_fallback_method(prompt: str, context: str = "") -> Dict[str, Any]:
    """
    Try the fallback method: using Botasaurus to access Claude directly.
    """
    log_message("🔄 Attempting fallback method: Botasaurus Claude Agent")
    
    try:
        # Import and run the Botasaurus Claude reviewer
        # We'll execute it as a subprocess to avoid asyncio conflicts
        import subprocess
        import os
        
        # Prepare the data for the Botasaurus script
        script_path = '/home/yahwehatwork/human-ai/skills/claude-robust-review/scripts/claude_review_botasaurus.py'
        
        # Build command line arguments
        cmd = ['python3', script_path]
        
        if prompt:
            cmd.extend(['--prompt', prompt])
        
        # Add trading agent path for default prompt generation
        cmd.extend(['--trading-agent-path', 
                   '/home/yahwehatwork/human-ai/agents/trading-agent/trading_agent.py'])
        
        log_message(f"   Running: {' '.join(cmd)}")
        
        # Run the script and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180  # 3 minute timeout for the whole process
        )
        
        if result.returncode == 0:
            # Try to parse JSON output
            try:
                output_data = json.loads(result.stdout.strip())
                log_message("   ✅ Botasaurus fallback successful")
                return {
                    "status": "success",
                    "response": output_data.get('review', ''),
                    "method": output_data.get('method', 'botasaurus_claude_fallback'),
                    "raw_output": output_data
                }
            except json.JSONDecodeError:
                # If not JSON, treat as plain text response
                log_message("   ✅ Botasaurus fallback successful (plain text)")
                return {
                    "status": "success",
                    "response": result.stdout.strip(),
                    "method": "botasaurus_claude_fallback_plaintext",
                    "raw_output": {"stdout": result.stdout, "stderr": result.stderr}
                }
        else:
            # Script failed
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            log_message(f"   ❌ Botasaurus fallback failed: {error_msg}")
            if result.stdout:
                log_message(f"   STDOUT: {result.stdout[:200]}...")
            
            return {
                "status": "error",
                "error": error_msg,
                "method": "botasaurus_claude_fallback",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
    except subprocess.TimeoutExpired:
        error_msg = "Botasaurus fallback timed out after 3 minutes"
        log_message(f"   ❌ {error_msg}")
        return {
            "status": "error",
            "error": error_msg,
            "method": "botasaurus_claude_fallback",
            "timeout": True
        }
    except Exception as e:
        error_msg = f"Botasaurus fallback exception: {str(e)}"
        log_message(f"   ❌ {error_msg}")
        log_message(f"   Traceback: {traceback.format_exc()}")
        
        return {
            "status": "error",
            "error": error_msg,
            "method": "botasaurus_claude_fallback",
            "traceback": traceback.format_exc()
        }

async def robust_claude_access(prompt: str, context: str = "") -> Dict[str, Any]:
    """
    Main function: Try hybrid router first, fall back to Botasaurus if Cloudflare issues detected.
    """
    log_message("🚀 Starting robust Claude access attempt")
    log_message(f"   Prompt length: {len(prompt)} characters")
    if context:
        log_message(f"   Context length: {len(context)} characters")
    
    # Step 1: Try primary method (hybrid router)
    primary_result = await try_hybrid_router_method(prompt, context)
    
    # If primary succeeded, return it
    if primary_result.get("status") == "success":
        log_message("✅ Primary method succeeded - returning result")
        return primary_result
    
    # Primary failed - check if it's Cloudflare-related to justify fallback
    is_cloudflare = primary_result.get("is_cloudflare_related", False)
    primary_error = primary_result.get("error", "Unknown error")
    
    log_message(f"⚠️  Primary method failed: {primary_error}")
    log_message(f"   Cloudflare-related: {is_cloudflare}")
    
    # If it's Cloudflare-related OR we just want to be safe, try fallback
    # In practice, we'll try fallback on most failures since the hybrid router
    # might fail for other reasons too, and Botasaurus might still work
    log_message("🔄 Attempting Botasaurus fallback method...")
    fallback_result = try_botasaurus_fallback_method(prompt, context)
    
    # If fallback succeeded, return it with note about fallback
    if fallback_result.get("status") == "success":
        log_message("✅ Fallback method succeeded - returning result")
        fallback_result["fallback_used"] = True
        fallback_result["primary_error"] = primary_error
        return fallback_result
    
    # Both methods failed
    log_message("❌ Both primary and fallback methods failed")
    return {
        "status": "error",
        "error": "Both hybrid router and Botasaurus fallback failed",
        "primary_error": primary_error,
        "primary_method": "hybrid_router_claude",
        "fallback_error": fallback_result.get("error", "Unknown error"),
        "fallback_method": "botasaurus_claude_fallback",
        "primary_details": primary_result,
        "fallback_details": fallback_result
    }

# For testing / direct usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Robust Claude access with hybrid router primary and Botasaurus fallback')
    parser.add_argument('--prompt', type=str, required=True, help='The prompt to send to Claude')
    parser.add_argument('--context', type=str, default='', help='Additional context for the prompt')
    parser.add_argument('--output', type=str, help='Output file for the result (JSON)')
    
    args = parser.parse_args()
    
    # Run the async function
    result = asyncio.run(robust_claude_access(args.prompt, args.context))
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Result saved to {args.output}")
    else:
        print(json.dumps(result, indent=2))