#!/usr/bin/env python3
"""
LLM Router - Routes agent requests to NVIDIA API directly.
All agents use NVIDIA NIM. No OpenRouter.
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / '.env')

_routing_config = None

# Canonical config path — core/config/llm_routing.json
_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "llm_routing.json"


def _load_routing_config() -> Dict:
    global _routing_config
    if _routing_config is None:
        # Try canonical path first, then legacy path
        for p in [_CONFIG_PATH,
                  Path(__file__).resolve().parents[1] / "configs" / "llm_routing.json"]:
            if p.exists():
                with open(p) as f:
                    _routing_config = json.load(f)["llm_routing"]
                break
        if _routing_config is None:
            # Hard default — direct NVIDIA
            _routing_config = {"agents": {}, "fallback_chain": []}
    return _routing_config


def get_agent_config(agent_name: str) -> Dict:
    """Get LLM config for a specific agent"""
    config = _load_routing_config()
    return config["agents"].get(agent_name.lower(), config["agents"]["opencode"])


def query_llm(agent_name: str, prompt: str, system_prompt: str = "",
              max_tokens: int = 2048, temperature: float = 0.7) -> str:
    """
    Query the LLM assigned to a specific agent.

    Args:
        agent_name: Which agent is making the request (determines model)
        prompt: User/task prompt
        system_prompt: System instructions
        max_tokens: Max response tokens
        temperature: Sampling temperature

    Returns:
        LLM response text
    """
    agent_cfg = get_agent_config(agent_name)
    api_key = os.getenv(agent_cfg["api_key_env"])

    if not api_key:
        return f"Error: {agent_cfg['api_key_env']} not set in environment"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": agent_cfg["model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        resp = requests.post(
            f"{agent_cfg['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        # Fallback: use core.llm (NVIDIA → Groq, no OpenRouter)
        return _try_fallback_llm(prompt, system_prompt, max_tokens, temperature, str(e))


def _try_fallback_llm(prompt, system_prompt, max_tokens, temperature, original_error) -> str:
    """Fallback via core.llm — uses NVIDIA NIM then Groq. Never OpenRouter."""
    try:
        from core.llm import complete
        result = complete(prompt, system=system_prompt or "You are a helpful assistant.",
                          max_tokens=max_tokens, temperature=temperature)
        if result:
            return result
    except Exception as e2:
        pass
    return f"[LLM unavailable: {original_error}]"


def _try_fallback(messages, max_tokens, temperature, original_error) -> str:
    """Legacy fallback — redirects to core.llm (NVIDIA/Groq, no OpenRouter)."""
    prompt = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    return _try_fallback_llm(prompt, system, max_tokens, temperature, original_error)


def _try_nvidia_fallback(messages, max_tokens, temperature, original_error) -> str:
    """Fallback using NVIDIA NIM fallback chain from config."""
    config = _load_routing_config()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        return f"[LLM unavailable — NVIDIA_API_KEY not set. Original: {original_error}]"
    for fallback in config.get("fallback_chain", []):
        try:
            resp = requests.post(
                f"{fallback.get('base_url', 'https://integrate.api.nvidia.com/v1')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": fallback["model"], "messages": messages,
                      "max_tokens": max_tokens, "temperature": temperature},
                timeout=60
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            continue
    return f"[All NVIDIA fallbacks failed. Original: {original_error}]"


def test_routing():
    """Test that routing works for each agent"""
    print("Testing LLM routing for each agent...")
    config = _load_routing_config()
    for agent, cfg in config["agents"].items():
        key = os.getenv(cfg["api_key_env"])
        status = "KEY_PRESENT" if key else "MISSING"
        print(f"  {agent:15s} → {cfg['provider']:12s} ({cfg['model'][:40]}) [{status}]")


if __name__ == "__main__":
    test_routing()
    print("\nTesting OpenCode (NVIDIA)...")
    result = query_llm("opencode", "Say 'hello' in one word", max_tokens=10)
    print(f"  Response: {result[:100]}")
